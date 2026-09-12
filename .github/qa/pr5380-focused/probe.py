#!/usr/bin/env python3
"""Isolated PR5380 four-method JDK comparison. No writes to the PR branch.

Build the required compiler modules once. Reuse Tycho's generated OSGi command
and byte-identical classes for A-B-B-A runs, with a restored runtime workspace.
All source instrumentation is disposable and archived as an explicit patch.
"""
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASE = '6b777ed704d1a0e00eb87f63ec9042b01b0acd6f'
METHODS = ('test056', 'test056a', 'test056b', 'test056d')
MODULE = 'org.eclipse.jdt.core.tests.compiler'
SRC = MODULE + '/src/org/eclipse/jdt/core/tests/'
EXPECTED = {'A': '26+34-2887', 'B': '26.0.2.1+1'}


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one occurrence of {old[:100]!r}; got {text.count(old)}')
    return text.replace(old, new)


def wrap_method(source, signature, phase):
    # These TestVerifier methods use unindented declarations/closing braces.
    # Refuse source drift rather than silently patching another overload.
    if source.count(signature) != 1:
        raise ValueError('Method signature absent or ambiguous: ' + signature)
    start = source.index(signature)
    opening = source.index('{', start)
    closing = source.index('\n}', opening)
    body = source[opening + 1:closing]
    return (source[:opening+1] + '\n\tlong[] qaBefore = ProbeTiming.start();\n\ttry {' + body
            + '\n\t} finally {\n\t\tProbeTiming.end("' + phase + '", qaBefore);\n\t}\n'
            + source[closing:])


def read_cases(directory):
    names, times = [], {}
    for path in sorted(directory.glob('TEST-*.xml')):
        root = ET.parse(path).getroot()
        for case in root.iter('testcase'):
            if any(x.tag in ('failure', 'error', 'skipped', 'flakyFailure', 'flakyError', 'rerunFailure', 'rerunError') for x in case):
                raise ValueError('Failed/skipped/retried test: ' + ET.tostring(case, encoding='unicode')[:2000])
            raw = case.get('name', '')
            name = raw.split(' - ')[0]
            names.append(name)
            times[name] = float(case.get('time', '0'))
    if Counter(names) != Counter(METHODS):
        raise ValueError('Expected exactly the four original methods, got ' + repr(Counter(names)))
    return times


def replay_command(base, home, directory, expected):
    if '-Dcompliance=17' not in base or '-jar' not in base or '-testproperties' not in base:
        raise ValueError('Unexpected generated Tycho command')
    return [str(home / 'bin/java'), '-Dqa.probe.dir=' + str(directory),
            '-Dqa.expected.runtime=' + expected, *base[1:]]


def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def paths():
    root = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    work = Path(os.environ['RUNNER_TEMP']) / 'pr5380-focused-work'
    return root, work, root / 'focused-evidence'


def clean_environment(home):
    env = os.environ.copy()
    for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'):
        env.pop(key, None)
    env['JAVA_HOME'] = str(home)
    env['PATH'] = str(home / 'bin') + ':' + env['PATH']
    return env


def execute(command, log, cwd, env, seconds=900):
    print('COMMAND:', shlex.join(command), flush=True)
    before = time.monotonic()
    with log.open('w') as stream:
        code = subprocess.run(['/usr/bin/time', '-v', '-o', str(log.with_suffix('.time.txt')),
                               'timeout', '--kill-after=15s', str(seconds), *command],
                              cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
    print('EXIT:', code, 'WALL:', time.monotonic() - before, 'LOG:', log, flush=True)
    print('\n'.join(log.read_text(errors='replace').splitlines()[-18:]), flush=True)
    if code:
        raise RuntimeError('Command failed: ' + str(log))


def setup():
    root, work, out = paths()
    out.mkdir(exist_ok=True)
    qa = root / '.github/qa/pr5380-focused'
    if work.exists():
        raise ValueError('Refuse to overwrite existing worktree')
    git('worktree', 'add', '--detach', str(work), BASE, cwd=root)
    assert git('rev-parse', 'HEAD', cwd=work) == BASE
    for source, target in [('FocusedCompilerProbe.java', 'compiler/regression/FocusedCompilerProbe.java'),
                           ('ProbeTiming.java', 'util/ProbeTiming.java')]:
        shutil.copy2(qa / source, work / SRC / target)
    path = work / SRC / 'compiler/regression/AbstractRegressionTest.java'
    call = 'batchCompiler.compile(getCompilationUnits(testFiles)); // compile all files together'
    measured = ('long[] qaCompile = org.eclipse.jdt.core.tests.util.ProbeTiming.start();\n'
                '\t\t\ttry {\n\t\t\t\t' + call + '\n\t\t\t} finally {\n'
                '\t\t\t\torg.eclipse.jdt.core.tests.util.ProbeTiming.end("compile", qaCompile);\n\t\t\t}')
    path.write_text(replace_once(path.read_text(), call, measured))
    path = work / SRC / 'util/TestVerifier.java'
    text = path.read_text()
    for sig, label in [('private void launchAndRun(', 'launch-and-run'),
                       ('private void launchVerifyTestsIfNeeded(', 'launch-verifier'),
                       ('private void waitForFullBuffers()', 'buffers'),
                       ('public void shutDown()', 'shutdown'),
                       ('public boolean verifyClassFiles(String sourceFilePath, String className, String expectedOutputString,', 'verify')]:
        text = wrap_method(text, sig, label)
    if text.count('launcher.launch()') != 2:
        raise ValueError('Unexpected VM launch count')
    text = text.replace('launcher.launch()', 'ProbeTiming.launch(launcher)')
    old = 'launcher.setVMPath(Util.getJREDirectory());'
    if text.count(old) != 2:
        raise ValueError('Unexpected child JDK selection')
    text = text.replace(old, 'ProbeTiming.childRuntime(Util.getJREDirectory(), vmArguments);\n\t' + old)
    path.write_text(text)
    path = work / MODULE / 'pom.xml'
    text, count = re.subn(r'<includes>.*?</includes>', '<includes><include>org/eclipse/jdt/core/tests/compiler/regression/FocusedCompilerProbe.class</include></includes>', path.read_text(), flags=re.S)
    if count != 1:
        raise ValueError('Unexpected compiler test includes')
    path.write_text(text)
    git('add', '-N', SRC + 'compiler/regression/FocusedCompilerProbe.java', SRC + 'util/ProbeTiming.java', cwd=work)
    git('diff', '--check', cwd=work)
    (out / 'instrumentation.patch').write_text(git('diff', cwd=work) + '\n')
    (out / 'source-sha.txt').write_text(BASE + '\n')
    (work / 'tmp').mkdir()
    home = Path(os.environ['JAVA_HOME'])
    env = clean_environment(home)
    env['WORKSPACE'] = str(work)
    repo = '-Dmaven.repo.local=' + str(work / '.m2/repository')
    common = ['-B', '--no-transfer-progress', repo, '-DcompilerBaselineMode=disable', '-DcompilerBaselineReplace=none',
              '-Dcompare-version-with-baselines.skip=true', '-Djava.io.tmpdir=' + str(work/'tmp')]
    execute(['mvn', 'clean', 'install', '-f', 'org.eclipse.jdt.core.compiler.batch', '-DlocalEcjVersion=99.99', *common],
            out / 'bootstrap.log', work, env, 900)
    execute(['mvn', 'verify', '-pl', MODULE, '-am', '-Ptest-on-javase-26', '-Dcbi-ecj-version=99.99',
             '-Dmaven.test.failure.ignore=false', '-Dsurefire.timeout=180',
             '-Dtycho.surefire.argLine=--add-modules ALL-SYSTEM -Dcompliance=17 -Djdt.performance.asserts=disabled', *common],
            out / 'prepare.log', work, env, 1200)
    read_cases(work / MODULE / 'target/surefire-reports')
    lines = (out / 'prepare.log').read_text().splitlines()
    commands = [shlex.split(line.split('Command line: ', 1)[1]) for line in lines
                if 'Command line: ' in line and MODULE + '/target' in line]
    if len(commands) != 1:
        raise ValueError('Cannot identify unique generated OSGi test command')
    (out / 'command.json').write_text(json.dumps(commands[0], indent=2))
    shutil.copytree(work / MODULE / 'target/work', out / 'runtime-template')
    shutil.copy2(work / MODULE / 'target/surefire.properties', out / 'surefire.properties')
    (out / 'binary-sha256.json').write_text(json.dumps(fingerprints(work), indent=2))


def fingerprints(work):
    found = {}
    for directory in (work / MODULE / 'target/classes', work / 'org.eclipse.jdt.core/target/classes',
                      work / 'org.eclipse.jdt.core.compiler.batch/target/classes'):
        for p in sorted(directory.rglob('*.class')):
            found[str(p.relative_to(work))] = hashlib.sha256(p.read_bytes()).hexdigest()
    if len(found) < 100:
        raise ValueError('Compiled test classes missing')
    return found


def measurement(home, arm, index):
    root, work, out = paths()
    directory = out / f'{index}-{arm}'
    directory.mkdir()
    expected = EXPECTED[arm]
    env = clean_environment(home)
    env['WORKSPACE'] = str(work)
    version = subprocess.check_output([str(home/'bin/java'), '-XshowSettings:properties', '-version'], env=env, stderr=subprocess.STDOUT, text=True)
    (directory / 'java-version.txt').write_text(version)
    if not re.search(r'java.runtime.version\s*=\s*' + re.escape(expected) + r'\s*$', version, re.M):
        raise ValueError('Wrong JDK for arm ' + arm + ': ' + version)
    if fingerprints(work) != json.loads((out / 'binary-sha256.json').read_text()):
        raise ValueError('Compiled classes changed between measurements')
    target = work / MODULE / 'target'
    for name in ('work', 'surefire-reports', 'qa-probe'):
        shutil.rmtree(target / name, ignore_errors=True)
    shutil.copytree(out / 'runtime-template', target / 'work')
    shutil.copy2(out / 'surefire.properties', target / 'surefire.properties')
    command = replay_command(json.loads((out / 'command.json').read_text()), home, directory, expected)
    (directory / 'command.json').write_text(json.dumps(command, indent=2))
    execute(command, directory / 'test.log', work / MODULE, env, 180)
    cases = read_cases(target / 'surefire-reports')
    shutil.copytree(target / 'surefire-reports', directory / 'reports')
    metadata = dict(line.split('\t',1) for line in (directory/'runtime.tsv').read_text().splitlines())
    if metadata.get('java.runtime.version') != expected or metadata.get('compliance') != '17':
        raise ValueError('Actual test-JVM metadata mismatch')
    rows = list(csv.reader((directory/'timings.tsv').open(), delimiter='\t'))
    for name in METHODS:
        if sum(r[0] == name and r[1] == 'test' for r in rows) != 1:
            raise ValueError('Missing or duplicate test timing: ' + name)
        if sum(r[0] == name and r[1] == 'compile' for r in rows) != 1:
            raise ValueError('Compilation was not measured: ' + name)
        launches = sum(r[0] == name and r[1] == 'vm-launch' for r in rows)
        if launches != (0 if name == 'test056d' else 1):
            raise ValueError('Unexpected program-execution path: ' + name + ' ' + str(launches))
    return {'arm': arm, 'index': index, 'runtime': expected, 'xml_seconds': cases, 'measurements': rows}


def run():
    root, work, out = paths()
    homes = {'A': Path(os.environ['QA_JDK_A']), 'B': Path(os.environ['JAVA_HOME'])}
    results = []
    for index, arm in enumerate(('A', 'B', 'B', 'A'), 1):
        results.append(measurement(homes[arm], arm, index))
        (out/'results.json').write_text(json.dumps(results, indent=2))
    lines = ['# PR5380 focused JDK comparison', '', 'Pinned source: `' + BASE + '`; compliance 17; same runner and compiled classes.', '',
             'Order: A-B-B-A, fresh test JVM each time. Build/download time is excluded.', '',
             '| Method | Phase | A median ms | B median ms |', '|---|---|---:|---:|']
    for name in METHODS:
        for phase in ('test', 'compile', 'verify', 'launch-and-run', 'vm-launch', 'shutdown'):
            values = {arm: [int(row[2])/1e6 for r in results if r['arm']==arm
                            for row in r['measurements'] if row[0]==name and row[1]==phase] for arm in homes}
            if all(values.values()):
                lines.append(f'| {name} | {phase} | {statistics.median(values["A"]):.3f} | {statistics.median(values["B"]):.3f} |')
    lines += ['', '## Interpretation limits',
              'A matches the runtime string of the Jenkins Maven JVM, not yet independently confirmed inside its historical test JVM.',
              'B is the exact runtime observed in the successful earlier fork comparison.',
              'Stage timings are inclusive/nested; do not add them. Parent JVM/thread CPU is not child CPU.',
              'GNU time records process-tree user/system totals separately. Wall minus CPU is not an exact wait measurement.',
              'Two observations per JDK are diagnostic, not a statistically established performance benchmark.',
              'No parser preconditioning or full-suite execution is part of these four-method runs.',
              'The original test assertions were retained. No failed test is accepted as a timing result.']
    text='\n'.join(lines)+'\n'
    (out/'SUMMARY.md').write_text(text)
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f: f.write(text)

if __name__ == '__main__':
    {'setup': setup, 'run': run}[sys.argv[1]]()
