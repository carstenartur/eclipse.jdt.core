#!/usr/bin/env python3
"""Full Maven source build, then fresh Tycho JVMs with exact outcome accounting."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET

root, out = map(lambda s: Path(s).resolve(),sys.argv[1:3])
arm, java = sys.argv[3:5]
out.mkdir(parents=True,exist_ok=True)
base=['mvn','--batch-mode','--no-transfer-progress','-Ptest-on-javase-21','-Pbree-libs',
      '-Dcbi-ecj-version=99.99','-Dproject.build.sourceEncoding=UTF-8',
      '-Djava.io.tmpdir='+str(out/'tmp')]
(out/'tmp').mkdir(exist_ok=True)
summary={'arm':arm,'test_java':java,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'scenarios':[]}
def invoke(command,label,timeout=1800):
    with (out/(label+'.log')).open('w') as log:
        log.write('COMMAND '+json.dumps(command)+'\n');log.flush()
        try:
            proc=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            status=proc.returncode
        except subprocess.TimeoutExpired: status=124
    (out/(label+'.exit')).write_text(str(status)+'\n')
    print(label,'exit',status,flush=True)
    if status:
        print('\n'.join((out/(label+'.log')).read_text(errors='replace').splitlines()[-60:]),flush=True)
    return status

def record():
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')

status=invoke(['mvn','--batch-mode','--no-transfer-progress','clean','install','-f','org.eclipse.jdt.core.compiler.batch','-DlocalEcjVersion=99.99'],'bootstrap')
if status:
    summary['build_failure']='bootstrap';record();sys.exit(status)
status=invoke(base+['clean','install','-DskipTests','-pl','org.eclipse.jdt.core.tests.model','-am'],'reactor-build')
if status:
    summary['build_failure']='reactor-build';record();sys.exit(status)
# Each verify invocation runs only model tests in a fresh Tycho JVM/workspace.
# Do not use -Dtest: it overrides the separate standalone-test execution too.
for label,scenario,tracing in [('pair-off','pair','false'),('pair-on','pair','true'),('class-on','class','true'),('chain-on','chain','true')]:
    target=root/'org.eclipse.jdt.core.tests.model/target'
    for path in [target/'surefire-reports',target/'work']:
        if path.exists(): shutil.rmtree(path)
    args='--add-modules ALL-SYSTEM -Dcompliance=1.8,11,17,20 -Djdt.performance.asserts=disabled '+ \
        '-Dcompletion5364.scenario='+scenario+' -Dcompletion5364.trace='+tracing
    status=invoke(base+['verify','-pl','org.eclipse.jdt.core.tests.model','-Dtycho.surefire.argLine='+args],label)
    text=(out/(label+'.log')).read_text(errors='replace')
    dest=out/label;dest.mkdir(exist_ok=True)
    if (target/'surefire-reports').exists(): shutil.copytree(target/'surefire-reports',dest/'reports',dirs_exist_ok=True)
    for p in target.glob('work/**/.log'):
        d=dest/p.relative_to(target);d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
    for pattern in ['work/**/config.ini','work/**/bundles.info','work/**/*.properties']:
        for p in target.glob(pattern):
            d=dest/p.relative_to(target);d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
    results=re.findall(r'COMPLETION5364_RESULT scenario=(\w+) tests=(\d+) failures=(\d+) errors=(\d+) target=(\d+)',text)
    runtime=re.findall(r'COMPLETION5364_RUNTIME java=([^ ]+)',text)
    traces=re.findall(r'^COMPLETION5364 (.+)$',text,re.M)
    (dest/'trace.txt').write_text('\n'.join(traces)+'\n')
    cases=[];xml_errors=0
    for p in (dest/'reports').glob('TEST-*.xml'):
        try:
            doc=ET.parse(p)
            for case in doc.findall('.//testcase'):
                failure=case.find('failure');error=case.find('error');skip=case.find('skipped')
                cases.append({'class':case.get('classname'),'name':case.get('name'),
                    'failed':failure is not None or error is not None,'skipped':skip is not None})
        except ET.ParseError: xml_errors+=1
    expected={'pair':2,'class':22,'chain':1999}[scenario]
    complete=len(results)==1 and results[0][0]==scenario and int(results[0][1])==expected and results[0][4]=='1'
    right_jvm=len(runtime)==1 and runtime[0].startswith(java+'.')
    trace_valid=tracing=='false' or any(t.startswith('ENGINE_SETTINGS ') for t in traces) and any(t.startswith('DELIVER ') for t in traces)
    entry={'label':label,'exit':status,'result_markers':results,'runtime':runtime,'completed_expected_tests':complete,
           'correct_test_jvm':right_jvm,'trace_valid':trace_valid,'xml_case_elements':len(cases),
           'xml_failed':sum(c['failed'] for c in cases),'xml_skipped':sum(c['skipped'] for c in cases),'xml_parse_errors':xml_errors,
           'settings_sha256': [hashlib.sha256(t.encode()).hexdigest() for t in traces if t.startswith('ENGINE_SETTINGS ')],
           'eclipse_error_entries':len(re.findall(r'^!ENTRY \S+ 4 ',text,re.M))}
    entry['success']=bool(status==0 and complete and right_jvm and trace_valid and cases and not xml_errors
                          and not entry['xml_failed'] and not entry['xml_skipped'] and results[0][2:4]==('0','0'))
    summary['scenarios'].append(entry);record();print(json.dumps(entry),flush=True)
summary['success']=all(e['success'] for e in summary['scenarios']) and len(summary['scenarios'])==4
record()
report=['# Maven comparison: '+arm+' / Java '+java,'',f"Source: `{summary['revision']}`",'',
        '| Scenario | Tests | Failures | Errors | Correct JVM | Verified |','| --- | ---: | ---: | ---: | --- | --- |']
for e in summary['scenarios']:
    r=e['result_markers'][0] if len(e['result_markers'])==1 else ('?','?','?','?','?')
    report.append(f"| {e['label']} | {r[1]} | {r[2]} | {r[3]} | {e['correct_test_jvm']} | {e['success']} |")
report+=['','This is a targeted source-built Maven/Tycho comparison, not a Jenkins replay or proof of absence of a sporadic defect.',
         'Trace-off still contains the dormant diagnostic hooks; it is not an original-binary control.']
(out/'SUMMARY.md').write_text('\n'.join(report)+'\n')
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('\n'.join(report)+'\n')
sys.exit(0 if summary['success'] else 1)
