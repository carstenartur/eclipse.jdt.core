"""Fork-only validation for PR 5450. Never move the PR branch from this workflow."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'bb43114e42b4b4d8222d86fbcac45ca6b19a0972'
PREVIOUS = '9a315924f10bbf91d8561ca88110993091c13b67'
PREVIOUS_TREE = 'b7a75d2929253e177ac2631e00d236cd31e6fb16'
CORE = Path('org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core')
MODEL = Path('org.eclipse.jdt.core.tests.model')
TEST = MODEL/'src/org/eclipse/jdt/core/tests/model/ClassFileBufferPublicationTests.java'
FILES = [CORE/'ClassFile.java', CORE/'ModularClassFile.java', TEST]
EVIDENCE = Path('review-buffer-evidence')
P2 = 'https://download.eclipse.org/eclipse/updates/4.41/R-4.41-202608281142/'
OLD = {
 'testClassSourceIsInitializedBeforePublication': 'Published source must already be initialized',
 'testModuleSourceIsInitializedBeforePublication': 'Published source must already be initialized',
 'testClassBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
 'testModuleBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
 'testClassNullBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
 'testModuleNullBufferListenerIsInstalledBeforePublication': 'Closing a published buffer must remove it from the cache',
}
NEW = {name: 'Concurrent cache misses must publish one buffer' for name in (
 'testConcurrentClassOpensReuseBuffer', 'testConcurrentModuleOpensReuseBuffer',
 'testConcurrentClassOpensReuseNullBuffer', 'testConcurrentModuleOpensReuseNullBuffer',
 'testConcurrentOuterAndInnerOpensReuseBuffer', 'testConcurrentOuterAndInnerOpensReuseNullBuffer')}

def checked(*args):
    return subprocess.check_output(args)

def restore(ref):
    for p in FILES[:2]:
        p.write_bytes(checked('git','show',f'{ref}:{p}'))

def run(phase, selection, expected):
    for path in (Path('org.eclipse.jdt.core/target'), MODEL/'target'):
        shutil.rmtree(path, ignore_errors=True)
    dest=EVIDENCE/phase
    dest.mkdir(parents=True, exist_ok=True)
    for p in FILES:
        target=dest/'sources'/p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    args=['mvn','-B','verify','-pl',str(MODEL),'-am','-Ptest-on-javase-21','-Pbree-libs',
          '-Dcbi-ecj-version=99.99',f'-Declipse-p2-repo.url={P2}',f'-Dtest={selection}',
          '-Dmaven.test.skip.exec=true','-DfailIfNoTests=false','-Dtycho.showEclipseLog=true',
          '-Dtycho.surefire.argLine=--add-modules ALL-SYSTEM -Dcompliance=1.8,11,17,21 -Djdt.performance.asserts=disabled']
    (dest/'command.json').write_text(json.dumps(args,indent=2)+'\n')
    with (dest/'maven.log').open('w') as log:
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:
            log.write(line)
            print(line,end='',flush=True)
        status=process.wait()
    reports=MODEL/'target/surefire-reports'
    if reports.exists():
        shutil.copytree(reports,dest/'reports',dirs_exist_ok=True)
    work=MODEL/'target/work'
    if work.exists():
        for p in work.rglob('*.log'):
            target=dest/'runtime'/p.relative_to(work)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy(p,target)
    cases=[c for p in reports.glob('TEST-*.xml') for c in ET.parse(p).iter('testcase')]
    if phase=='adjacent':
        required={'ClassFileTests':91,'BufferTests':19,'AttachSourceTests':83}
        counts={name:sum(c.get('classname','').endswith('.'+name) for c in cases) for name in required}
        assert counts==required, counts
    else:
        cases=[c for c in cases if c.get('classname','').endswith('.ClassFileBufferPublicationTests')]
        assert len(cases)==12 and {c.get('name') for c in cases}==OLD.keys()|NEW.keys(), [c.attrib for c in cases]
    for c in cases:
        assert c.find('error') is None and c.find('skipped') is None, ET.tostring(c,encoding='unicode')
        failures=c.findall('failure')
        if c.get('name') in expected:
            assert len(failures)==1 and expected[c.get('name')] in failures[0].get('message',''), ET.tostring(c,encoding='unicode')
        else:
            assert not failures, ET.tostring(c,encoding='unicode')
    assert (status!=0)==bool(expected), ('unexpected Maven status',phase,status)
    result={'phase':phase,'exit':status,'tests':len(cases),'failures':len(expected),'errors':0,'skipped':0,
            'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}}
    (dest/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return result

def main():
    EVIDENCE.mkdir(exist_ok=True)
    checked('git','fetch','--no-tags','--depth=1','origin',BASE,PREVIOUS)
    subprocess.run([sys.executable,'.github/scripts/review-buffer-tests.py'],check=True)
    test_hash=hashlib.sha256(TEST.read_bytes()).hexdigest()
    restore(BASE)
    summaries=[run('upstream','ClassFileBufferPublicationTests',OLD|NEW)]
    restore(PREVIOUS)
    summaries.append(run('previous','ClassFileBufferPublicationTests',NEW))
    fix=Path('.github/scripts/review-buffer-fix.py')
    if not fix.exists():
        print('RED verified on upstream and original PR. No production fix applied.')
        return
    subprocess.run([sys.executable,str(fix)],check=True)
    assert hashlib.sha256(TEST.read_bytes()).hexdigest()==test_hash
    checked('git','diff','--check')
    summaries.append(run('fixed','ClassFileBufferPublicationTests',{}))
    summaries.append(run('repeat','ClassFileBufferPublicationTests',{}))
    summaries.append(run('adjacent','ClassFileTests,BufferTests,AttachSourceTests',{}))
    repo=os.environ['GITHUB_REPOSITORY']
    assert repo=='carstenartur/eclipse.jdt.core'
    entries=[{'path':str(p),'mode':'100644','type':'blob','content':p.read_text()} for p in FILES]
    req=urllib.request.Request(f'https://api.github.com/repos/{repo}/git/trees',
         data=json.dumps({'base_tree':PREVIOUS_TREE,'tree':entries}).encode(),
         headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'},method='POST')
    with urllib.request.urlopen(req,timeout=30) as response:
        tree=json.load(response)
    result={'parent':PREVIOUS,'tree_sha':tree['sha'],'qa_commit':os.environ['GITHUB_SHA'],
            'run_id':os.environ['GITHUB_RUN_ID'],'p2':P2,'validation':summaries}
    (EVIDENCE/'verified-tree.json').write_text(json.dumps(result,indent=2)+'\n')
    (EVIDENCE/'review-fix.patch').write_bytes(checked('git','diff',PREVIOUS,'--',*map(str,FILES)))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
