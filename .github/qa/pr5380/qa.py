#!/usr/bin/env python3
"""Disposable PR 5380 paired CI probe. Never changes the PR branch.

Both variants use the same QA-only test adapter. It observes the two known
boundary outcomes without reporting an expected exception to TracingSuite.
The report gate (not Maven's failure-ignore flag) checks the outcome required
for each variant, all unexpected errors, and equality of test inventories.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASE = '6b777ed704d1a0e00eb87f63ec9042b01b0acd6f'
PRODUCTION = 'org.eclipse.jdt.core/formatter/org/eclipse/jdt/internal/formatter/linewrap/WrapPreparator.java'
TEST = 'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/formatter/FormatterRegionTests.java'
FIX = 'previousRegionEnd = Math.max(0, region.getOffset() + region.getLength() - 1);'
ORIGINAL = 'previousRegionEnd = region.getOffset() + region.getLength() - 1;'
PROBES = ('testEmptyFirstRegionAtDocumentStart', 'testEmptyFirstRegionAtDocumentStartWithCrLf')
NOOPS = ('testSingleEmptyRegionAtDocumentStartDoesNotChangeSource', 'testSingleEmptyRegionAfterDocumentStartDoesNotChangeSource')
MARKER = 'PR5380_QA_OUTCOME='
ADAPTER_OLD = '''\t\tString actual = formatAndApply(source, new IRegion[] { new Region(0, 0), followingRegion }, lineSeparator);

\t\tassertEquals(expected, actual);
\t\tassertTrue(actual.startsWith(lineSeparator));'''
ADAPTER_NEW = '''\t\t// QA only: record the expected negative control without aborting TracingSuite.
\t\t// The external report gate requires the correct outcome for each variant.
\t\tString actual;
\t\ttry {
\t\t\tactual = formatAndApply(source, new IRegion[] { new Region(0, 0), followingRegion }, lineSeparator);
\t\t} catch (StringIndexOutOfBoundsException ex) {
\t\t\tboolean expectedFrame = false;
\t\t\tfor (StackTraceElement frame : ex.getStackTrace()) {
\t\t\t\tif (frame.getClassName().equals("org.eclipse.jdt.internal.formatter.TokenManager")
\t\t\t\t\t\t&& frame.getMethodName().equals("countLineBreaksBetween"))
\t\t\t\t\texpectedFrame = true;
\t\t\t}
\t\t\tif (!expectedFrame || ex.getMessage() == null || !ex.getMessage().contains("-1"))
\t\t\t\tthrow ex;
\t\t\tSystem.err.println("PR5380_QA_OUTCOME=without-fix");
\t\t\treturn;
\t\t}
\t\tassertEquals(expected, actual);
\t\tassertTrue(actual.startsWith(lineSeparator));
\t\tSystem.err.println("PR5380_QA_OUTCOME=with-fix");'''


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one replacement, got {text.count(old)}')
    return text.replace(old, new)


def read_reports(directory, variant):
    identities, outcomes, problems = Counter(), defaultdict(list), []
    times, formatter_seconds, report_count = defaultdict(float), 0.0, 0
    for path in sorted(directory.rglob('TEST-*.xml')):
        report_count += 1
        root = ET.parse(path).getroot()
        for suite in root.iter('testsuite'):
            for attribute in ('errors', 'failures', 'flakes'):
                if int(suite.get(attribute, '0')):
                    problems.append(f'{path.name}: {attribute}={suite.get(attribute)}')
        for case in root.iter('testcase'):
            name = case.get('name', '')
            output = '\n'.join((c.text or '') for c in case if c.tag in ('system-out', 'system-err'))
            # Some tracing reports use the enclosing suite as classname. Preserve
            # its actual traced Java method where available, including repeats.
            match = re.search(r'^\[[^\n]+\]\s+(org\.eclipse\.\S+)\(', output, re.M)
            origin = match.group(1) if match else case.get('classname', '')
            identity = f'{path.relative_to(directory)}::{origin}::{name}'
            identities[identity] += 1
            seconds = float(case.get('time', '0'))
            times[identity] += seconds
            if '.tests.formatter.' in output or '.tests.formatter.' in origin:
                formatter_seconds += seconds
            if any(c.tag in ('error', 'failure', 'skipped', 'rerunError', 'rerunFailure', 'flakyError', 'flakyFailure') for c in case):
                problems.append(f'{identity}: error/failure/skip/retry present')
            if name in PROBES:
                outcomes[name].extend(re.findall(r'PR5380_QA_OUTCOME=(with-fix|without-fix)', output))
            elif name in NOOPS:
                outcomes[name].append('executed')
    if not report_count:
        problems.append('No JUnit reports: no result may be inferred')
    for name in PROBES:
        if outcomes[name] != [variant]:
            problems.append(f'{name}: expected one {variant} observation; got {outcomes[name]}')
    for name in NOOPS:
        if outcomes[name] != ['executed']:
            problems.append(f'{name}: expected one executed test; got {outcomes[name]}')
    return dict(identities=identities, times=times, formatter_seconds=formatter_seconds,
                reports=report_count, outcomes=dict(outcomes), problems=problems)


def phase(command, name, work, out):
    started = time.monotonic()
    wrapped = ['/usr/bin/time', '-v', '-o', str(out / (name + '-time.txt')),
               'timeout', '--kill-after=30s', '105m', *command]
    print(f'::group::{out.name}: {name}', flush=True)
    print('COMMAND: ' + repr(command), flush=True)
    with (out / (name + '.log')).open('w') as log:
        proc = subprocess.Popen(wrapped, cwd=work, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors='replace')
        for line in proc.stdout:
            log.write(line)
            # The artifact keeps all output; the console keeps Maven progress.
            if line.startswith(('[INFO]', '[ERROR]', '[WARNING]', 'Running ')):
                print(line, end='', flush=True)
        code = proc.wait()
    elapsed = time.monotonic() - started
    print(f'EXIT={code} ELAPSED_SECONDS={elapsed:.3f}\n::endgroup::', flush=True)
    return dict(exit_code=code, wall_seconds=elapsed, command=command)


def run(variant):
    root = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    work = Path(os.environ['RUNNER_TEMP']).resolve() / 'pr5380-ab-work'
    out = root / 'qa-evidence' / variant
    out.mkdir(parents=True, exist_ok=False)
    if work.exists():
        subprocess.run(['git', 'worktree', 'remove', '--force', str(work)], cwd=root, check=True)
    subprocess.run(['git', 'worktree', 'add', '--detach', str(work), BASE], cwd=root, check=True)
    # A fresh worktree includes a fresh local Maven/p2 cache and temporary directory.
    # No cache from the first arm is copied to the second arm.
    local_repo = work / '.m2/repository'
    local_repo.mkdir(parents=True)
    (work / 'tmp').mkdir()
    os.environ['WORKSPACE'] = str(work)
    for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS'):
        os.environ.pop(key, None)
    test = work / TEST
    test.write_text(replace_once(test.read_text(), ADAPTER_OLD, ADAPTER_NEW))
    production = work / PRODUCTION
    if variant == 'without-fix':
        production.write_text(replace_once(production.read_text(), FIX, ORIGINAL))
    elif production.read_text().count(FIX) != 1:
        raise ValueError('Pinned positive source does not contain the expected fix')
    (out / 'source.patch').write_bytes(subprocess.check_output(['git', 'diff', '--', PRODUCTION, TEST], cwd=work))
    (out / 'test-adapter.java').write_bytes(test.read_bytes())
    metadata = dict(base_sha=BASE, variant=variant, initial_cache='empty per arm',
                    test_adapter_sha256=hashlib.sha256(test.read_bytes()).hexdigest())
    (out / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    repo = '-Dmaven.repo.local=' + str(local_repo)
    common = ['-Djava.io.tmpdir=' + str(work / 'tmp'), '-Dproject.build.sourceEncoding=UTF-8']
    bootstrap = ['mvn', 'clean', 'install', '-f', 'org.eclipse.jdt.core.compiler.batch',
                 '-DlocalEcjVersion=99.99', repo, '-DcompilerBaselineMode=disable', '-DcompilerBaselineReplace=none']
    verify = ['mvn', '-U', 'clean', 'verify', '--batch-mode', '--fail-at-end', repo,
              '-Ptest-on-javase-26', '-Pbree-libs', '-Papi-check', '-Pjavadoc', '-Pp2-repo',
              '-Dmaven.test.failure.ignore=true', '-Dcompare-version-with-baselines.skip=false', *common,
              '-Dtycho.surefire.argLine=--add-modules ALL-SYSTEM -Dcompliance=1.8,11,17,21,25,26 -Djdt.performance.asserts=disabled',
              '-DDetectVMInstallationsJob.disabled=true', '-Dtycho.apitools.debug',
              '-Dtycho.debug.artifactcomparator', '-e', '-Dcbi-ecj-version=99.99']
    result = {}
    try:
        result['bootstrap'] = phase(bootstrap, 'bootstrap', work, out)
        if result['bootstrap']['exit_code'] == 0:
            result['verify'] = phase(verify, 'verify', work, out)
    finally:
        (out / 'phases.json').write_text(json.dumps(result, indent=2))
        for path in work.rglob('TEST-*.xml'):
            if '/target/surefire-reports/' in path.as_posix():
                target = out / 'reports' / path.relative_to(work)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
        # Check that resolved p2 bundle bytes did not change between the arms.
        bundles = {}
        for path in sorted((local_repo / 'p2').rglob('*.jar')):
            with path.open('rb') as stream:
                bundles[str(path.relative_to(local_repo))] = hashlib.file_digest(stream, 'sha256').hexdigest()
        (out / 'p2-bundles.json').write_text(json.dumps(bundles, indent=2))
    return 0 if result.get('verify', {}).get('exit_code') == 0 else 1


def compare(root):
    problems, reports, phases, metadata, bundles = [], {}, {}, {}, {}
    for variant in ('without-fix', 'with-fix'):
        directory = root / variant
        try:
            reports[variant] = read_reports(directory / 'reports', variant)
            phases[variant] = json.loads((directory / 'phases.json').read_text())
            metadata[variant] = json.loads((directory / 'metadata.json').read_text())
            bundles[variant] = json.loads((directory / 'p2-bundles.json').read_text())
            problems.extend(f'{variant}: {p}' for p in reports[variant]['problems'])
            for name in ('bootstrap', 'verify'):
                if phases[variant].get(name, {}).get('exit_code') != 0:
                    problems.append(f'{variant}: {name} did not finish successfully')
            if reports[variant]['reports'] < 20:
                problems.append(f'{variant}: fewer than 20 reports; full reactor coverage not established')
            if not bundles[variant]:
                problems.append(f'{variant}: no p2 bundle fingerprints recorded')
        except (OSError, ValueError, ET.ParseError) as exc:
            problems.append(f'{variant}: incomplete evidence: {exc}')
    if len(reports) == 2 and len(metadata) == 2 and len(bundles) == 2:
        a, b = 'without-fix', 'with-fix'
        if reports[a]['identities'] != reports[b]['identities']:
            problems.append('Test inventories differ; total timings are not a valid paired comparison')
        if metadata[a]['test_adapter_sha256'] != metadata[b]['test_adapter_sha256']:
            problems.append('The common QA probe differs between arms')
        if bundles[a] != bundles[b]:
            problems.append('Resolved p2 bundle sets/bytes differ; dependency drift is a confounder')
        with (root / 'test-times.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['test_identity', 'without_fix_count', 'with_fix_count', 'without_fix_seconds', 'with_fix_seconds', 'delta_seconds'])
            keys = reports[a]['identities'].keys() | reports[b]['identities'].keys()
            for key in sorted(keys, key=lambda k: reports[b]['times'].get(k, 0) - reports[a]['times'].get(k, 0), reverse=True):
                at, bt = reports[a]['times'].get(key, 0), reports[b]['times'].get(key, 0)
                writer.writerow([key, reports[a]['identities'][key], reports[b]['identities'][key], at, bt, bt-at])
    lines = ['# PR 5380 paired fork comparison', '', 'Baseline: `' + BASE + '`.', '',
             '**Comparable observations**' if not problems else '**NOT a valid completed comparison**', '',
             '| Arm | Bootstrap wall s | Verify wall s | Formatter testcase sum s | XML testcase records |',
             '|---|---:|---:|---:|---:|']
    for v in ('without-fix', 'with-fix'):
        if v in reports and v in phases:
            lines.append(f"| {v} | {phases[v].get('bootstrap', {}).get('wall_seconds', 'missing')} | {phases[v].get('verify', {}).get('wall_seconds', 'missing')} | {reports[v]['formatter_seconds']:.3f} | {sum(reports[v]['identities'].values())} |")
    lines += ['', '## Validation problems', *(['- ' + p for p in problems] or ['None.']), '',
              '## Scope and limitations',
              'Both arms ran sequentially on the same runner/JDK/Maven, at the same worktree path, with fresh local Maven/p2 caches. '
              'Only the production clamp is reverted in the negative arm; both have the identical temporary outcome-recording test adapter. '
              'The adapter is QA-only, not part of the proposed fix. The gate requires two fixed outcomes for the positive arm and exactly two original Index -1 outcomes for the negative arm.', '',
              'This is one pair, not a statistically established benchmark. External network load, OS caches, remote Maven snapshots and host load can still vary. '
              'p2 fingerprints are compared, but this does not pin all Maven inputs. Wall times include dependency downloads. '
              'GNU time files also report CPU user/system time and memory; test-times.csv separates test durations. '
              'This does not reproduce Jenkins post-processing or establish the cause of its earlier timeout.']
    text = '\n'.join(lines) + '\n'
    (root / 'SUMMARY.md').write_text(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(text)
    print(text)
    return int(bool(problems))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('run').add_argument('variant', choices=('with-fix', 'without-fix'))
    sub.add_parser('compare').add_argument('directory', type=Path)
    args = parser.parse_args()
    sys.exit(run(args.variant) if args.command == 'run' else compare(args.directory))
