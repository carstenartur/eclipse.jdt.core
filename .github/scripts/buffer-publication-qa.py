"""Isolated A/B validation; not part of the proposed production commit."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'bb43114e42b4b4d8222d86fbcac45ca6b19a0972'
BASE_TREE = '17dbb2fdd5fe0aad799c15cdcba72e04501ce9b9'
MODEL = Path('org.eclipse.jdt.core.tests.model')
SOURCES = MODEL / 'src/org/eclipse/jdt/core/tests/model'
CORE = Path('org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core')
FILES = [CORE/'ClassFile.java', CORE/'ModularClassFile.java', SOURCES/'AllJavaModelTests.java', SOURCES/'ClassFileBufferPublicationTests.java']
EVIDENCE = Path('publication-evidence')
EXPECTED = {
    'testClassSourceIsInitializedBeforePublication': 'Published source must already be initialized',
    'testModuleSourceIsInitializedBeforePublication': 'Published source must already be initialized',
    'testClassBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
    'testModuleBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
    'testClassNullBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
    'testModuleNullBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
}

def prepare():
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    ET.register_namespace('', ns['m'])
    p = MODEL/'pom.xml'
    tree = ET.parse(p)
    plugins = tree.find('m:build/m:plugins', ns)
    for plugin in list(plugins):
        if plugin.findtext('m:artifactId', namespaces=ns) == 'maven-surefire-plugin':
            plugins.remove(plugin)
    changed = 0
    for profile in tree.findall('m:profiles/m:profile', ns):
        if profile.findtext('m:id', namespaces=ns) == 'test-on-javase-21':
            profile.find('m:id', ns).text = 'test-on-javase-25'
            for plugin in profile.findall('m:build/m:plugins/m:plugin', ns):
                if plugin.findtext('m:artifactId', namespaces=ns) == 'maven-toolchains-plugin':
                    jdk = plugin.find('m:configuration/m:toolchains/m:jdk/m:id', ns)
                    assert jdk.text == 'JavaSE-21'
                    jdk.text = 'JavaSE-25'
                    changed += 1
    assert changed == 1
    tree.write(p, encoding='UTF-8', xml_declaration=True)
    EVIDENCE.mkdir(exist_ok=True)
    shutil.copy(p, EVIDENCE/'test-runtime-pom.xml')

def clean():
    for name in ('surefire-reports', 'work'):
        p = MODEL/'target'/name
        if p.exists():
            shutil.rmtree(p)

def verify(phase):
    reports = MODEL/'target/surefire-reports'
    dest = EVIDENCE/phase
    dest.mkdir(parents=True, exist_ok=True)
    if reports.exists():
        shutil.copytree(reports, dest/'reports', dirs_exist_ok=True)
    work = MODEL/'target/work'
    if work.exists():
        for p in work.rglob('*.log'):
            target = dest/'runtime'/p.relative_to(work)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, target)
        p = work/'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
        if p.exists():
            shutil.copy(p, dest/'bundles.info')
    cases = [c for p in reports.glob('*.xml') for c in ET.parse(p).iter('testcase')]
    counts = {}
    for c in cases:
        name = c.get('classname', '').rsplit('.', 1)[-1]
        counts[name] = counts.get(name, 0) + 1
    if phase == 'adjacent':
        required = {'ClassFileTests', 'BufferTests', 'AttachSourceTests'}
        assert required <= counts.keys(), counts
        for name in required:
            assert any(c.get('classname', '').endswith('.'+name) and c.find('skipped') is None for c in cases), name
    else:
        cases = [c for c in cases if c.get('classname', '').endswith('.ClassFileBufferPublicationTests')]
        assert len(cases) == 6 and {c.get('name') for c in cases} == set(EXPECTED), counts
    for c in cases:
        assert c.find('error') is None, ET.tostring(c, encoding='unicode')
        failures = c.findall('failure')
        if phase == 'baseline':
            assert c.find('skipped') is None, ET.tostring(c, encoding='unicode')
            assert len(failures) == 1 and EXPECTED[c.get('name')] in failures[0].get('message', ''), ET.tostring(c, encoding='unicode')
        else:
            assert not failures, ET.tostring(c, encoding='unicode')
            if phase != 'adjacent':
                assert c.find('skipped') is None, ET.tostring(c, encoding='unicode')
    result = {'phase': phase, 'tests': len(cases), 'failures': sum(c.find('failure') is not None for c in cases), 'errors': 0, 'skipped': sum(c.find('skipped') is not None for c in cases), 'classes': counts}
    (dest/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

def apply_fix():
    for p in FILES[:3]:
        original = subprocess.check_output(['git', 'show', f'{BASE}:{p}'])
        assert p.read_bytes() == original, f'Production baseline changed: {p}'
    for p in FILES[:2]:
        text = p.read_text()
        pattern = r'(?m)^(\t+)bufManager\.addBuffer\(buffer\);\n'
        assert len(re.findall(pattern, text)) == 2
        text = re.sub(pattern, '', text)
        pattern = r'(?m)^(\t+)buffer\.addBufferChangedListener\(this\);$'
        assert len(re.findall(pattern, text)) == 2
        text = re.sub(pattern, lambda m: m[0]+'\n\n'+m[1]+'// Publish only after the contents and close listener are initialized.\n'+m[1]+'bufManager.addBuffer(buffer);', text)
        pos = text.index('BufferManager.createNullBuffer')
        text = text[:pos]+text[pos:].replace('the contents and close listener are initialized', 'the close listener is installed', 1)
        p.write_text(text)
    p = FILES[2]
    text = p.read_text()
    assert text.count('\t\tClassFileTests.class,') == 1
    p.write_text(text.replace('\t\tClassFileTests.class,', '\t\tClassFileTests.class,\n\t\tClassFileBufferPublicationTests.class,'))
    subprocess.run(['git', 'diff', '--check', BASE, '--', *map(str, FILES)], check=True)
    for p in FILES:
        target = EVIDENCE/'sources'/p
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, target)
    (EVIDENCE/'fix.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary', BASE, '--', *map(str, FILES)]))

def export_tree():
    summaries = [json.loads((EVIDENCE/phase/'summary.json').read_text()) for phase in ('baseline', 'patched', 'repeat', 'adjacent')]
    assert summaries[0]['failures'] == 6
    assert all(s['failures'] == 0 and s['errors'] == 0 for s in summaries[1:])
    repo = os.environ['GITHUB_REPOSITORY']
    assert repo == 'carstenartur/eclipse.jdt.core'
    entries = [{'path': str(p), 'mode': '100644', 'type': 'blob', 'content': p.read_text()} for p in FILES]
    request = urllib.request.Request(f'https://api.github.com/repos/{repo}/git/trees', data=json.dumps({'base_tree': BASE_TREE, 'tree': entries}).encode(), headers={'Authorization': 'Bearer '+os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        tree = json.load(response)
    result = {'base': BASE, 'tree_sha': tree['sha'], 'qa_commit': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'], 'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}, 'validation': summaries}
    (EVIDENCE/'verified-tree.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'prepare': prepare()
    elif command == 'clean': clean()
    elif command == 'verify': verify(sys.argv[2])
    elif command == 'apply': apply_fix()
    elif command == 'export': export_tree()
    else: raise SystemExit(f'Unknown command: {command}')
