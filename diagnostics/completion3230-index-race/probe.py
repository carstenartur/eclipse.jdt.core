#!/usr/bin/env python3
"""Causal experiment: invalidate an acquired index, then test the existing fallback.

Not a production patch and not an assertion that Jenkins used this interleaving.
"""
from pathlib import Path
import hashlib, json, os, re, shutil, signal, subprocess, sys
import xml.etree.ElementTree as ET

root, tools, helpers, out = map(lambda s:Path(s).resolve(),sys.argv[1:5])
arm=sys.argv[5]
out.mkdir(parents=True,exist_ok=True);(out/'tmp').mkdir(exist_ok=True)
model='org.eclipse.jdt.core.tests.model'
source='org.eclipse.jdt.core/search/org/eclipse/jdt/internal/core/search'
file=root/source/'PatternSearchJob.java'
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
expected={'base':'8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51','pr':'d55a8c72e96ba601562fda02e5698da6323d37e7'}
assert revision==expected[arm], revision

def once(text,old,new):
    if text.count(old)!=1: raise RuntimeError('Non-unique source anchor: '+old)
    return text.replace(old,new,1)

subprocess.run([sys.executable,str(tools/'instrument.py'),str(root),str(tools),str(out),'25'],check=True)
original=file.read_text()
anchor='\tIndex[] indexes = getIndexes(subMonitor.split(1));'
file.write_text(once(original,anchor,anchor+'\n\tIndexRemovalProbe.afterAcquire(this.pattern, indexes);'))
shutil.copyfile(helpers/'IndexRemovalProbe.java',root/source/'IndexRemovalProbe.java')
# The actual original test file is never modified in this experiment.
testfile=root/model/'src/org/eclipse/jdt/core/tests/model/CompletionTests16_2.java'
original_test=subprocess.check_output(['git','show','HEAD:'+str(testfile.relative_to(root))],cwd=root)
assert testfile.read_bytes()==original_test
(out/'test-source-sha256.txt').write_text(hashlib.sha256(original_test).hexdigest()+'\n')
subprocess.run(['git','diff','--check'],cwd=root,check=True)
(out/'generated-interleaving.patch').write_bytes(subprocess.check_output(['git','diff'],cwd=root))

base=['mvn','--batch-mode','--no-transfer-progress','-Ptest-on-javase-21','-Pbree-libs',
      '-Dcbi-ecj-version=99.99','-Dproject.build.sourceEncoding=UTF-8','-Djava.io.tmpdir='+str(out/'tmp')]
summary={'arm':arm,'revision':revision,'scenarios':[]}
def save(): (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
def invoke(args,label):
    print('START',label,flush=True)
    with (out/(label+'.log')).open('w') as log:
        log.write('COMMAND '+json.dumps(args)+'\n');log.flush()
        proc=subprocess.Popen(args,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try: status=proc.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            status=124
    (out/(label+'.exit')).write_text(str(status)+'\n')
    print('FINISH',label,status,flush=True)
    if status:print('\n'.join((out/(label+'.log')).read_text(errors='replace').splitlines()[-40:]),flush=True)
    return status

status=invoke(['mvn','--batch-mode','--no-transfer-progress','clean','install','-f','org.eclipse.jdt.core.compiler.batch','-DlocalEcjVersion=99.99'],'bootstrap')
if status:summary['build_failure']='bootstrap';save();sys.exit(status)
status=invoke(base+['clean','install','-DskipTests','-pl',model,'-am'],'reactor')
if status:summary['build_failure']='reactor';save();sys.exit(status)
settings=[]
for label,removal,counterfactual in [('control',False,False),('removed-index',True,False),('cancel-deleted-index',True,True)]:
    if counterfactual:
        # Specific causal control, not a reviewed general search policy change.
        # A canceled search invokes SearchableEnvironment's existing model fallback.
        old=file.read_text()
        file.write_text(once(old,'if (monitor == null) return COMPLETE; // index got deleted since acquired',
                            'if (monitor == null) throw new OperationCanceledException(); // diagnostic causal control'))
        (out/'counterfactual.patch').write_bytes(subprocess.check_output(['git','diff'],cwd=root))
        status=invoke(base+['install','-DskipTests','-pl',model,'-am'],'counterfactual-build')
        if status:summary['build_failure']='counterfactual';save();sys.exit(status)
    target=root/model/'target'
    for p in [target/'work',target/'surefire-reports']:
        if p.exists():shutil.rmtree(p)
    args='--add-modules ALL-SYSTEM -Dcompliance=1.8,11,17,20 -Djdt.performance.asserts=disabled -Dcompletion5364.scenario=pair -Dcompletion5364.trace=true -Dcompletion5364.deleteIndex='+str(removal).lower()
    status=invoke(base+['verify','-pl',model,'-Dtycho.surefire.argLine='+args],label)
    dest=out/label;dest.mkdir(exist_ok=True)
    if (target/'surefire-reports').exists():shutil.copytree(target/'surefire-reports',dest/'reports',dirs_exist_ok=True)
    for p in target.glob('work/**/.log'):
        q=dest/p.relative_to(target);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    text=(out/(label+'.log')).read_text(errors='replace')
    traces=re.findall(r'^COMPLETION5364 (.+)$',text,re.M)
    (dest/'trace.txt').write_text('\n'.join(traces)+'\n')
    result=re.findall(r'COMPLETION5364_RESULT scenario=pair tests=(\d+) failures=(\d+) errors=(\d+) target=(\d+)',text)
    runtime=re.findall(r'COMPLETION5364_RUNTIME java=([^ ]+)',text)
    removed=re.findall(r'^INDEX_RACE_REMOVED (.+)$',text,re.M)
    actual_failures=[];skipped=0;count=0
    for p in (dest/'reports').glob('TEST-*.xml'):
        doc=ET.parse(p)
        for case in doc.findall('.//testcase'):
            count+=1;skipped+=int(case.find('skipped') is not None)
            for kind in ['failure','error']:
                if case.find(kind) is not None:
                    actual_failures.append({'class':case.get('classname'),'name':case.get('name'),'kind':kind,
                                            'message':case.find(kind).get('message','')})
    expected_failures=1 if label=='removed-index' else 0
    correct_failure=not actual_failures if not expected_failures else (
        len(actual_failures)==1 and actual_failures[0]['name']=='test002'
        and 'Enum[TYPE_REF]' in actual_failures[0]['message']
        and 'but was:<[]enum[KEYWORD]' in actual_failures[0]['message'])
    delivered=any(t.startswith('DELIVER kind=9 completion=Enum ') for t in traces)
    keyword=any(t.startswith('DELIVER kind=3 completion=enum ') for t in traces)
    engine_settings=[t for t in traces if t.startswith('ENGINE_SETTINGS ')]
    settings.append(engine_settings)
    passed=bool(result==[('2',str(expected_failures),'0','1')] and len(runtime)==1 and runtime[0].startswith('25.')
                and len(removed)==int(removal) and correct_failure and not skipped and keyword
                and delivered==(not expected_failures) and status==(1 if expected_failures else 0))
    entry={'label':label,'expected_failures':expected_failures,'result':result,'runtime':runtime,'exit':status,
           'xml_tests':count,'failures':actual_failures,'skipped':skipped,'removed':removed,
           'enum_delivered':delivered,'keyword_delivered':keyword,'validated':passed}
    summary['scenarios'].append(entry);save();print(json.dumps(entry),flush=True)
summary['engine_settings_equal']=settings[0]==settings[1]==settings[2] and len(settings[0])==1
summary['validated']=all(x['validated'] for x in summary['scenarios']) and summary['engine_settings_equal']
save()
report=['# Acquired-index removal experiment: '+arm,'',
        'Controlled scheduling with real IndexManager.removeIndex(), not an observed Jenkins schedule.',
        'The canceled-search variant is a causal probe, not a production-ready fix.','',
        '| Scenario | Expected JUnit failures | Actual result | Enum delivered | Verified |',
        '| --- | ---: | --- | --- | --- |']
for e in summary['scenarios']:report.append(f"| {e['label']} | {e['expected_failures']} | {e['result']} | {e['enum_delivered']} | {e['validated']} |")
report+=['','Actual CompletionEngine settings identical across scenarios: '+str(summary['engine_settings_equal'])]
(out/'SUMMARY.md').write_text('\n'.join(report)+'\n')
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('\n'.join(report)+'\n')
sys.exit(0 if summary['validated'] else 1)
