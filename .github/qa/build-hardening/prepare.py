"""Prepare two independent, narrowly scoped PR candidates from upstream master.

All preparation is local to runner worktrees. Publishing is a separate step after QA.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import urllib.request

BASE = 'b2492d5d610e7d6fb1cecaf7dc13c2d9e75961ca'
PLATFORM = '76f1695ed861a4073fab2df42a2996d88e233468'
REPO = Path.cwd()
QA = REPO / '.github/qa/build-hardening'
ROOT = Path(os.environ['RUNNER_TEMP']) / 'jdt-build-hardening'
MODEL = 'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/'
TRACING = [
    'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/RunAllJdtModelTestsTracing.java',
    'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/dom/RunAllTestsTracing.java',
    MODEL + 'AllJavaModelTestsTracing.java',
]
BRANCHES = {'snapshot': 'fix/snapshot-job-wakeup-race', 'tracing': 'fix/headless-core-timeout-diagnostics'}


def git(*args, cwd=REPO):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def replace_once(path, before, after):
    text = path.read_text()
    if text.count(before) != 1:
        raise RuntimeError(f'Expected one exact match in {path}: {before!r}')
    path.write_text(text.replace(before, after))


def harness(name):
    root = ROOT / name
    root.mkdir(parents=True)
    (root / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>
<groupId>org.eclipse.jdt.qa</groupId><artifactId>build-hardening</artifactId><version>1</version>
<properties><maven.compiler.release>21</maven.compiler.release><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
<dependencies>
<dependency><groupId>org.eclipse.platform</groupId><artifactId>org.eclipse.core.jobs</artifactId><version>3.15.900</version></dependency>
<dependency><groupId>junit</groupId><artifactId>junit</artifactId><version>4.13.2</version><scope>test</scope></dependency>
</dependencies>
<build><plugins>
<plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.14.0</version></plugin>
<plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.5.3</version><configuration><failIfNoTests>true</failIfNoTests></configuration></plugin>
</plugins></build></project>''')
    src = root / 'src/test/java'
    src.mkdir(parents=True)
    return src


def write(src, relative, content):
    path = src / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def prepare():
    ROOT.mkdir()
    git('fetch', '--no-tags', 'https://github.com/eclipse-jdt/eclipse.jdt.core.git', BASE)
    assert git('rev-parse', BASE) == BASE
    config_test = (QA / 'TracingSuiteConfigurationTests.java').read_text()
    for kind in BRANCHES:
        git('worktree', 'add', '--detach', str(ROOT / kind), BASE)
    snapshot = ROOT / 'snapshot'
    for name in ['JobFamilyWait.java', 'JobFamilyWaitTests.java']:
        shutil.copy2(QA / 'src/test/java/org/eclipse/jdt/core/tests/model' / name,
                     snapshot / MODEL / name)
    extra = (QA / 'extra-snapshot-test.txt').read_text()
    replace_once(snapshot / MODEL / 'JobFamilyWaitTests.java',
                 '\tprivate Future<?> waitFor(', extra + '\tprivate Future<?> waitFor(')
    replace_once(snapshot / MODEL / 'JobFamilyWaitTests.java',
                 'import java.util.concurrent.atomic.AtomicBoolean;',
                 'import java.util.concurrent.atomic.AtomicBoolean;\nimport java.util.concurrent.atomic.AtomicInteger;')
    replace_once(snapshot / MODEL / 'JobFamilyWaitTests.java',
                 'java.util.concurrent.atomic.AtomicInteger joins = new java.util.concurrent.atomic.AtomicInteger();',
                 'AtomicInteger joins = new AtomicInteger();')
    replace_once(snapshot / MODEL / 'AbstractJavaModelTests.java',
                 'Job.getJobManager().wakeUp(ResourcesPlugin.FAMILY_SNAPSHOT);\n\t\t\t\tJob.getJobManager().join(ResourcesPlugin.FAMILY_SNAPSHOT, null);',
                 'JobFamilyWait.join(Job.getJobManager(), ResourcesPlugin.FAMILY_SNAPSHOT);')
    replace_once(snapshot / MODEL / 'AllJavaModelTests.java',
                 '\t\t// Binding key tests', '\t\t// Test infrastructure\n\t\tJobFamilyWaitTests.class,\n\n\t\t// Binding key tests')

    tracing = ROOT / 'tracing'
    for path in TRACING:
        replace_once(tracing / path, '@TracingOptions(stackDumpTimeoutSeconds = 60)',
                     '// These headless tests have no UI to capture. Keep timeout thread dumps without requiring X11.\n'
                     '@TracingOptions(stackDumpTimeoutSeconds = 60, maxScreenshotCount = 0)')
    (tracing / MODEL / 'TracingSuiteConfigurationTests.java').write_text(config_test)
    replace_once(tracing / MODEL / 'AllJavaModelTests.java',
                 '\t\t// test IJavaModel', '\t\t// Headless tracing configuration\n\t\tTracingSuiteConfigurationTests.class,\n\n\t\t// test IJavaModel')

    allowed = {
        'snapshot': [MODEL + x for x in ['JobFamilyWait.java', 'JobFamilyWaitTests.java', 'AbstractJavaModelTests.java', 'AllJavaModelTests.java']],
        'tracing': TRACING + [MODEL + 'TracingSuiteConfigurationTests.java', MODEL + 'AllJavaModelTests.java'],
    }
    for kind in BRANCHES:
        tree = ROOT / kind
        git('add', '--', *allowed[kind], cwd=tree)
        assert set(git('diff', '--cached', '--name-only', cwd=tree).splitlines()) == set(allowed[kind])
        git('diff', '--cached', '--check', cwd=tree)
        (ROOT / f'{kind}.patch').write_text(git('diff', '--cached', '--binary', cwd=tree) + '\n')
    (ROOT / 'allowed.json').write_text(json.dumps(allowed, indent=2))

    # The job tests use actual Eclipse jobs. Only the surrounding Tycho build is omitted.
    src = harness('snapshot-tests')
    for name in ['JobFamilyWait.java', 'JobFamilyWaitTests.java']:
        write(src, 'org/eclipse/jdt/core/tests/model/' + name, (snapshot / MODEL / name).read_text())

    # Compile exact entrypoint sources and the real TracingSuite. Placeholder child
    # suites avoid compiling all of JDT in this focused configuration/diagnostic test.
    url = ('https://raw.githubusercontent.com/eclipse-platform/eclipse.platform.releng.aggregator/'
           + PLATFORM + '/eclipse.platform.releng/bundles/org.eclipse.test/src/org/eclipse/test/TracingSuite.java')
    source = urllib.request.urlopen(url, timeout=60).read().decode()
    assert 'if (fScreenshotCount < fTracingOptions.maxScreenshotCount())' in source
    (ROOT / 'TracingSuite.java').write_text(source)
    for arm in ['before', 'after']:
        src = harness('tracing-' + arm)
        for path in TRACING:
            text = git('show', BASE + ':' + path) + '\n' if arm == 'before' else (tracing / path).read_text()
            relative = path.split('/src/', 1)[1]
            write(src, relative, text)
        write(src, 'org/eclipse/jdt/core/tests/model/TracingSuiteConfigurationTests.java', config_test)
        write(src, 'org/eclipse/test/TracingSuite.java', source)
        write(src, 'org/eclipse/test/Screenshots.java',
              'package org.eclipse.test; public final class Screenshots {'
              'public static String takeScreenshot(Class<?> c,String n) {'
              'throw new RuntimeException("Injected unavailable display"); }}')
        for name in ['org.eclipse.jdt.core.tests.RunFormatterTests', 'org.eclipse.jdt.core.tests.dom.RunAllTests', 'org.eclipse.jdt.core.tests.model.AllJavaModelTests']:
            package, cls = name.rsplit('.', 1)
            write(src, name.replace('.', '/') + '.java',
                  'package ' + package + '; public class ' + cls + ' extends junit.framework.TestCase {'
                  'public static junit.framework.Test suite() { return new junit.framework.TestSuite(); }}')
        write(src, 'org/eclipse/test/TracingTimeoutIsolationTests.java',
              (QA / 'TracingTimeoutIsolationTests.java').read_text())
    print('Prepared pinned candidates and isolated before/after harnesses at', ROOT)


def reports():
    import xml.etree.ElementTree as E
    all_reports = []
    for path in sorted(ROOT.glob('**/TEST-*.xml')):
        root = E.parse(path).getroot()
        entries = [{**t.attrib, 'problems': [e.attrib for e in t if e.tag in ('failure', 'error')]}
                   for t in root.iter('testcase')]
        all_reports.append({'file': str(path.relative_to(ROOT)), 'suite': root.attrib, 'tests': entries})
    (ROOT / 'results.json').write_text(json.dumps(all_reports, indent=2))
    for report in all_reports:
        print(report['file'], report['suite'])
        for test in report['tests']:
            print(' ', test['name'], test.get('time'), test['problems'])


def publish():
    assert os.environ.get('GITHUB_REPOSITORY') == 'carstenartur/eclipse.jdt.core'
    assert os.environ.get('GITHUB_REF_NAME') == 'qa/jdt-build-hardening'
    allowed = json.loads((ROOT / 'allowed.json').read_text())
    messages = {
        'snapshot': 'Avoid delayed snapshot waits when jobs are scheduled after wakeUp\n\nRetry only the family join wait periodically so late sleeping snapshot\njobs can be woken without cancelling jobs or skipping running work.\nAdd deterministic regression coverage using the real Eclipse job manager.',
        'tracing': 'Keep headless Core timeout diagnostics independent of screenshots\n\nDisable optional screenshots in the three headless tracing entrypoints.\nKeep the existing timeout, thread dumps and test-start logging.\nA display failure must not terminate tracing for subsequent tests.',
    }
    commits = {}
    for kind, branch in BRANCHES.items():
        tree = ROOT / kind
        assert git('rev-parse', 'HEAD', cwd=tree) == BASE
        assert set(git('diff', '--cached', '--name-only', cwd=tree).splitlines()) == set(allowed[kind])
        git('diff', '--cached', '--check', cwd=tree)
        git('-c', 'user.name=Carsten Hammer', '-c', 'user.email=carsten.hammer@t-online.de',
            'commit', '-m', messages[kind] + '\n\nSigned-off-by: Carsten Hammer <carsten.hammer@t-online.de>', cwd=tree)
        sha = git('rev-parse', 'HEAD', cwd=tree)
        assert git('rev-parse', 'HEAD^', cwd=tree) == BASE
        # New refs only; never rewrite an existing branch or push upstream.
        existing = subprocess.run(['gh', 'api', f'repos/carstenartur/eclipse.jdt.core/git/ref/heads/{branch}'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if existing.returncode == 0:
            raise RuntimeError('Ref already exists: ' + branch)
        git('push', 'origin', sha + ':refs/heads/' + branch, cwd=tree)
        commits[kind] = {'branch': branch, 'sha': sha, 'base': BASE, 'files': allowed[kind]}
    (ROOT / 'commits.json').write_text(json.dumps(commits, indent=2))
    print(json.dumps(commits, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'reports': reports, 'publish': publish}[sys.argv[1]]()
