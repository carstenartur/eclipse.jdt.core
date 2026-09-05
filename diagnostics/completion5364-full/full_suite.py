#!/usr/bin/env python3
"""Source-built full JDT model-suite A/B experiment; never changes expected results."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

MODEL = 'org.eclipse.jdt.core.tests.model'
PACKAGE = MODEL + '/src/org/eclipse/jdt/core/tests/model'
TARGETS = {'CompletionTests16_2': 'test002', 'CompletionTests16': 'testBug564828_2'}
REVISIONS = {'base': '8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51',
             'pr': 'd55a8c72e96ba601562fda02e5698da6323d37e7'}
ORIGINAL_SELECTOR = 'org/eclipse/jdt/core/tests/RunAllJdtModelTestsTracing.class'
TRACE = 'org.eclipse.jdt.internal.codeassist.Completion5364Trace'


def once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f'Expected one source anchor, found {text.count(old)}: {old!r}')
    return text.replace(old, new, 1)


def surround_method(text: str, name: str, owner: str) -> str:
    # Find the closing brace at the existing method indentation, not in a source string.
    pattern = re.compile(r'(?m)^(\tpublic void ' + re.escape(name) + r'\(\) throws JavaModelException \{\n)(.*?)(^\t\})', re.S)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one method body for {owner}.{name}')
    match = matches[0]
    body = match.group(2)
    wrapped = (match.group(1) + '\t\t' + TRACE + '.begin("' + owner + '.' + name + '");\n'
               + '\t\ttry {\n' + body + '\t\t} finally {\n\t\t\t' + TRACE + '.end();\n\t\t}\n' + match.group(3))
    return text[:match.start()] + wrapped + text[match.end():]


def java_manifest(root: Path) -> dict[str, str]:
    files = subprocess.check_output(['git', 'ls-files', '*.java'], cwd=root, text=True).splitlines()
    return {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files}


def prepare(root: Path, tools: Path, out: Path, arm: str, mode: str) -> None:
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if revision != REVISIONS[arm]:
        raise RuntimeError(f'Wrong source revision: {revision}')
    before = java_manifest(root)
    original_pom = (root / MODEL / 'pom.xml').read_text()
    if mode == 'traced':
        subprocess.run([sys.executable, str(tools / 'instrument.py'), str(root), str(tools), str(out), '25'], check=True)
        # Keep the original full JUnit4 TracingSuite entry and all its predecessors.
        # The diagnostic subset wrapper is NOT executed or compiled in this experiment.
        (root / PACKAGE / 'Completion5364MavenTests.java').unlink()
        for owner, name in TARGETS.items():
            path = root / PACKAGE / (owner + '.java')
            original = path.read_text()
            wrapped = surround_method(original, name, owner)
            path.write_text(wrapped)
            old_body = re.search(r'(?ms)^\tpublic void ' + name + r'\(\) throws JavaModelException \{\n(.*?)^\t\}', original)[1]
            if old_body not in wrapped:
                raise RuntimeError('Original test body was modified')
    elif mode != 'pristine':
        raise ValueError(mode)
    # The only POM adjustment selects the actual Java-25 test JVM; includes stay original.
    pom = once(original_pom, '<id>JavaSE-21</id>', '<id>JavaSE-25</id><!-- diagnostic test JVM -->')
    if ORIGINAL_SELECTOR not in pom:
        raise RuntimeError('Original comprehensive selector missing')
    (root / MODEL / 'pom.xml').write_text(pom)
    after = java_manifest(root)
    changed = [f for f in before if before[f] != after[f]]
    expected = [] if mode == 'pristine' else [
        'org.eclipse.jdt.core/codeassist/org/eclipse/jdt/internal/codeassist/CompletionEngine.java',
        'org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/SearchableEnvironment.java',
        'org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/NameLookup.java',
        *(PACKAGE + '/' + owner + '.java' for owner in TARGETS)]
    if sorted(changed) != sorted(expected):
        raise RuntimeError(f'Unexpected changed Java sources: {changed}')
    out.mkdir(parents=True, exist_ok=True)
    provenance = {'revision': revision, 'arm': arm, 'mode': mode, 'test_jvm': '25',
                  'original_suite': ORIGINAL_SELECTOR, 'changed_java_files': changed,
                  'all_tracked_java_before': before, 'all_tracked_java_after': after,
                  'generated_java': [] if mode == 'pristine' else [TRACE.replace('.', '/') + '.java'],
                  'target_hooks_scope': 'inside original test methods, not a replacement test runner'}
    (out / 'source-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    subprocess.run(['git', 'diff', '--check'], cwd=root, check=True)
    (out / 'instrumentation.patch').write_bytes(subprocess.check_output(['git', 'diff'], cwd=root))
    print('PREPARED', arm, mode, 'changed Java sources:', len(changed), flush=True)


def command(root: Path, out: Path, label: str, args: list[str], timeout: int) -> int:
    print('START', label, flush=True)
    started = time.monotonic()
    with (out / (label + '.log')).open('w') as log:
        log.write('COMMAND ' + json.dumps(args) + '\n'); log.flush()
        process = subprocess.Popen(args, cwd=root, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            status = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            status = 124
    (out / (label + '.exit')).write_text(str(status) + '\n')
    print('FINISH', label, 'status', status, 'seconds', round(time.monotonic() - started, 1), flush=True)
    if status:
        print('\n'.join((out / (label + '.log')).read_text(errors='replace').splitlines()[-50:]), flush=True)
    return status


def analyze(root: Path, out: Path, arm: str, mode: str, status: int) -> dict:
    target = root / MODEL / 'target'
    reports = out / 'reports'
    if (target / 'surefire-reports').is_dir():
        shutil.copytree(target / 'surefire-reports', reports, dirs_exist_ok=True)
    for pattern in ['work/**/.log', 'work/**/config.ini', 'work/**/bundles.info', 'work/**/*.properties']:
        for path in target.glob(pattern):
            dest = out / path.relative_to(target); dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    cases, failures, targets, runtimes, xml_errors, model_cases = [], [], [], [], [], 0
    for path in sorted(reports.glob('TEST-*.xml')):
        try:
            doc = ET.parse(path)
        except ET.ParseError as ex:
            xml_errors.append({'file': path.name, 'error': str(ex)}); continue
        is_model = 'RunAllJdtModelTestsTracing' in path.name
        if is_model:
            props = {p.get('name'): p.get('value') for p in doc.findall('.//properties/property')}
            runtimes.append({k: props.get(k) for k in ['java.version', 'java.home', 'os.name']})
        for case in doc.findall('.//testcase'):
            model_cases += int(is_model)
            text = ''.join(case.itertext())
            identity = case.get('classname', '') + '.' + case.get('name', '')
            full = re.search(r'org\.eclipse\.jdt\.core\.tests\.model\.[\w$]+\.\w+\(\)', text)
            detail = {'identity': full[0] if full else identity,
                      'failure': case.find('failure') is not None or case.find('error') is not None,
                      'skipped': case.find('skipped') is not None}
            cases.append(detail)
            if detail['failure']:
                failures.append(detail | {'detail': text[:24000]})
            for owner, name in TARGETS.items():
                needle = 'org.eclipse.jdt.core.tests.model.' + owner + '.' + name
                if (case.get('name') == name and needle + '()' in text) or identity == needle:
                    targets.append(detail | {'target': needle})
                    (out / (owner + '-' + name + '.txt')).write_text(text)
    console = (out / 'full-model.log').read_text(errors='replace')
    traces = re.findall(r'^COMPLETION5364 (.+)$', console, re.M)
    (out / 'trace.txt').write_text('\n'.join(traces) + '\n')
    errors = []
    for path in sorted(out.glob('work/**/.log')):
        for entry in re.split(r'(?m)(?=^!ENTRY |^!SESSION )', path.read_text(errors='replace')):
            if re.match(r'^!ENTRY \S+ 4 ', entry):
                message = re.search(r'^!MESSAGE (.*)$', entry, re.M)
                errors.append({'file': str(path.relative_to(out)), 'message': message[1] if message else '',
                               'entry': entry[:14000]})
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    present = all(sum(t['target'].endswith(owner + '.' + name) for t in targets) == 1 for owner, name in TARGETS.items())
    # A failed assertion may be a valuable reproduction: retain it and fail this job.
    verified = bool(status == 0 and model_cases > 20000 and present and not failures and not xml_errors
                    and len(runtimes) == 1 and (runtimes[0]['java.version'] or '').startswith('25.')
                    and (mode != 'traced' or any(t.startswith('ENGINE_SETTINGS ') for t in traces)))
    result = {'arm': arm, 'mode': mode, 'revision': revision, 'exit': status,
              'model_testcase_elements': model_cases, 'all_testcase_elements': len(cases),
              'skipped': sum(c['skipped'] for c in cases), 'failures': failures, 'targets': targets,
              'runtime': runtimes, 'xml_parse_errors': xml_errors, 'workspace_errors': errors,
              'trace_events': len(traces), 'verified': verified,
              'scope': 'original RunAllJdtModelTestsTracing including formatter, DOM and model suites; not all repository modules'}
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    text = (f'# Original full model-suite comparison: {arm} / {mode}\n\n'
            f'Source: `{revision}`. Maven exit: {status}. Verified execution: **{verified}**.\n\n'
            f'Model testcase elements: {model_cases}; all XML testcase elements: {len(cases)}; '
            f'failed elements: {len(failures)}; skipped: {result["skipped"]}.\n\n'
            f'Actual model JVM: {runtimes}. Workspace ERROR entries: {len(errors)}.\n\n'
            '## Target results\n\n' + '\n'.join('- ' + str(t) for t in targets) + '\n\n'
            '## Failures\n\n' + '\n'.join('- ' + f['identity'] for f in failures) + '\n\n'
            'Passing assertions do not imply an error-free workspace or an exact replay of Jenkins. '
            'No expected proposals have been changed. Aggregate XML header counts are not used.\n')
    (out / 'SUMMARY.md').write_text(text)
    print(text, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream: stream.write(text)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('tools', type=Path)
    parser.add_argument('out', type=Path); parser.add_argument('arm', choices=REVISIONS)
    parser.add_argument('mode', choices=['pristine', 'traced'])
    a = parser.parse_args()
    root, tools, out = (p.resolve() for p in (a.source, a.tools, a.out))
    out.mkdir(parents=True, exist_ok=True)
    prepare(root, tools, out, a.arm, a.mode)
    (out / 'tmp').mkdir(exist_ok=True)
    base = ['mvn', '--batch-mode', '--no-transfer-progress', '-Ptest-on-javase-21', '-Pbree-libs',
            '-Dcbi-ecj-version=99.99', '-Dproject.build.sourceEncoding=UTF-8', '-Djava.io.tmpdir=' + str(out / 'tmp')]
    stages = [('bootstrap', ['mvn', '--batch-mode', '--no-transfer-progress', 'clean', 'install', '-f',
                              'org.eclipse.jdt.core.compiler.batch', '-DlocalEcjVersion=99.99']),
              ('reactor-build', base + ['clean', 'install', '-DskipTests', '-pl', MODEL, '-am'])]
    for label, args in stages:
        status = command(root, out, label, args, 1800)
        if status:
            (out / 'build-failure.json').write_text(json.dumps({'stage': label, 'status': status}) + '\n')
            return status
    args = '--add-modules ALL-SYSTEM -Dcompliance=1.8,11,17,20 -Djdt.performance.asserts=disabled -Dcompletion5364.trace=true'
    status = command(root, out, 'full-model', base + ['verify', '-pl', MODEL,
                     '-Dtycho.surefire.argLine=' + args], 2400)
    result = analyze(root, out, a.arm, a.mode, status)
    return 0 if result['verified'] else 1


if __name__ == '__main__':
    sys.exit(main())
