from pathlib import Path
import collections
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import xml.etree.ElementTree as E

ROOT=Path.cwd()
OUT=ROOT/'compiler-evidence'
OUT.mkdir()
MODULE=ROOT/'org.eclipse.jdt.core.tests.compiler'
BASE='6b777ed704d1a0e00eb87f63ec9042b01b0acd6f'
METHODS={'test056','test056a','test056b','test056d'}
B=Path(os.environ['JAVA_HOME']).resolve()
A_VERSION='26+34-2887'
B_VERSION='26.0.2.1+1'


def execute(cmd, log):
    with log.open('w') as f:
        p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    print(log.name,'exit',p.returncode,flush=True)
    if p.returncode: print(log.read_text(errors='replace')[-9000:],flush=True)
    return p.returncode


def identity(home):
    text=subprocess.check_output([str(home/'bin/java'),'-XshowSettings:properties','-version'],stderr=subprocess.STDOUT,text=True)
    found=re.search(r'^\s*java.runtime.version = (.+)$',text,re.M)
    if not found: raise RuntimeError('Missing runtime identity')
    return found.group(1).strip(),text


def fetch(url,path):
    if urllib.parse.urlparse(url).scheme!='https': raise ValueError('HTTPS required')
    return execute(['curl','--proto','=https','--proto-redir','=https','--fail','--location','--silent','--show-error','--connect-timeout','20','--max-time','240','--output',str(path),url],path.with_suffix(path.suffix+'.curl.log'))==0


# Look up links from the official archive instead of silently substituting another JDK.
A=None
availability={'requested_runtime':A_VERSION,'indexes':[],'candidates':[],'matched':False}
try:
    links=set()
    for i,url in enumerate(['https://jdk.java.net/archive/','https://jdk.java.net/26/']):
        page=OUT/f'jdk-index-{i}.html'
        ok=fetch(url,page)
        availability['indexes'].append({'url':url,'success':ok})
        if ok:
            for link in re.findall(r'href=[\"\']([^\"\']+)[\"\']',page.read_text(errors='replace')):
                link=urllib.parse.urljoin(url,html.unescape(link))
                if urllib.parse.urlparse(link).hostname=='download.java.net' and re.search(r'/jdk26/',link) and re.search(r'/34/',link) and re.search(r'openjdk-26(?:-ea\+34)?_linux-x64_bin\.tar\.gz$',link):
                    links.add(link)
    for i,url in enumerate(sorted(links)[:3]):
        entry={'url':url}; availability['candidates'].append(entry)
        checksum=OUT/f'jdk-A-{i}.sha256'
        archive=Path(os.environ['RUNNER_TEMP'])/f'jdk-A-{i}.tar.gz'
        if not fetch(url+'.sha256',checksum): continue
        digest=checksum.read_text().strip().split()[0]
        if not re.fullmatch('[0-9a-fA-F]{64}',digest): continue
        if not fetch(url,archive): continue
        with archive.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=digest.lower(): raise RuntimeError('Official archive checksum mismatch')
        folder=Path(os.environ['RUNNER_TEMP'])/f'jdk-A-{i}'
        folder.mkdir()
        with tarfile.open(archive) as f: f.extractall(folder,filter='data')
        homes=[p.parent.parent for p in folder.glob('*/bin/java')]
        if len(homes)!=1: continue
        version,text=identity(homes[0]); entry.update(runtime=version,sha256=actual)
        (OUT/f'jdk-A-{i}.txt').write_text(text)
        if version==A_VERSION:
            A=homes[0].resolve(); availability['matched']=True; break
except Exception as e:
    availability['error']=repr(e)
finally:
    (OUT/'jdk-A-availability.json').write_text(json.dumps(availability,indent=2))

version,text=identity(B)
(OUT/'jdk-B.txt').write_text(text)
assert version==B_VERSION,('Unexpected B runtime',version)
assert not subprocess.check_output(['git','diff',BASE,'--',str(MODULE)],text=True).strip()
source=MODULE/'src/org/eclipse/jdt/core/tests/compiler/regression/AbstractRegressionTest.java'
text=source.read_text()
compile_call='batchCompiler.compile(getCompilationUnits(testFiles)); // compile all files together'
verify_call='''boolean passed =
					this.verifier.verifyClassFiles(
						sourceFile,
						className,
						expectedOutputString,
						expectedErrorString,
						this.classpaths,
						null,
						vmArguments);'''
metric='org.eclipse.jdt.core.tests.util.Pr5380Metrics'
assert text.count(compile_call)==1
text=text.replace(compile_call,f'var compileTiming = {metric}.start("compile", getName());\ntry {{\n{compile_call}\n}} finally {{ {metric}.finish(compileTiming); }}')
assert text.count(verify_call)==1
text=text.replace(verify_call,f'var executeTiming = {metric}.start("execute", getName());\nboolean passed;\ntry {{\n'+verify_call.replace('boolean passed =','passed =')+f'\n}} finally {{ {metric}.finish(executeTiming); }}')
source.write_text(text)
for name,package in [('Pr5380CompilerProbe','compiler/regression'),('Pr5380Metrics','util')]:
    shutil.copy2(ROOT/f'.github/qa/{name}.java',MODULE/f'src/org/eclipse/jdt/core/tests/{package}/{name}.java')
(OUT/'instrumentation.patch').write_bytes(subprocess.check_output(['git','diff',BASE,'--',str(MODULE)]))
(ROOT/'tmp').mkdir(exist_ok=True)
common=['mvn','-B','-ntp','-Dcbi-ecj-version=99.99','-Dtycho.baseline.replace=none','-DcompilerBaselineMode=disable','-DcompilerBaselineReplace=none','-Dcompare-version-with-baselines.skip=true','-Djava.io.tmpdir='+str(ROOT/'tmp')]
assert execute([*common,'clean','install','-f','org.eclipse.jdt.core.compiler.batch','-DlocalEcjVersion=99.99'],OUT/'bootstrap.log')==0
assert execute([*common,'-pl','org.eclipse.jdt.core.tests.compiler','-am','install','-DskipTests'],OUT/'build.log')==0
maven=subprocess.check_output(['mvn','-version'],text=True,stderr=subprocess.STDOUT)
(OUT/'maven.txt').write_text(maven)
original_toolchains=Path.home()/'.m2/toolchains.xml'
results=[]
fingerprint=None
sequence='ABBA' if A else 'BBB'
for index,arm in enumerate(sequence):
    home=A if arm=='A' else B
    expected=A_VERSION if arm=='A' else B_VERSION
    dest=OUT/f'{index+1:02d}-{arm}';dest.mkdir()
    toolchains=E.parse(original_toolchains)
    for element in toolchains.iter():
        element.tag=element.tag.rsplit('}',1)[-1]
    matched=0
    for tool in toolchains.getroot().findall('toolchain'):
        if tool.findtext('provides/id')=='JavaSE-26':
            tool.find('configuration/jdkHome').text=str(home);matched+=1
    assert matched==1,matched
    chain=dest/'toolchains.xml';toolchains.write(chain,encoding='utf-8',xml_declaration=True)
    for path in ['surefire-reports','work']:
        shutil.rmtree(MODULE/'target'/path,ignore_errors=True)
    events=dest/'events.tsv'
    flags='--add-modules ALL-SYSTEM -Dcompliance=17 -Djdt.performance.asserts=disabled -Dpr5380.events='+str(events)+' -Dpr5380.expectedRuntime='+expected+' -Dpr5380.expectedHome='+str(home)
    cmd=[*common,'-t',str(chain),'-pl','org.eclipse.jdt.core.tests.compiler','-am','verify','-Ptest-on-javase-26','-Dtest=Pr5380CompilerProbe','-DfailIfNoTests=false','-Dsurefire.failIfNoSpecifiedTests=false','-Dmaven.test.failure.ignore=false','-Dtycho.surefire.argLine='+flags]
    (dest/'command.json').write_text(json.dumps(cmd,indent=2))
    rc=execute(['/usr/bin/time','-v','-o',str(dest/'resources.txt'),'timeout','--kill-after=15s','5m',*cmd],dest/'maven.log')
    reports=MODULE/'target/surefire-reports'
    if reports.exists(): shutil.copytree(reports,dest/'reports')
    cases=[]
    for p in (dest/'reports').glob('TEST-*.xml'): cases.extend(E.parse(p).getroot().iter('testcase'))
    def norm(name): return re.sub(r'\s+-\s+17$','',name)
    assert len(cases)==4 and {norm(c.get('name','')) for c in cases}==METHODS,(len(cases),[c.get('name') for c in cases])
    assert rc==0 and not any(any(e.tag in ('failure','error','skipped') for e in c) for c in cases)
    records=[line.split('\t') for line in events.read_text().splitlines()]
    runtimes=[r for r in records if r[0]=='runtime']
    assert len(runtimes)==1 and runtimes[0][1]==expected and runtimes[0][-1]=='17'
    phases=[r for r in records if r[0]=='phase']
    inventory=collections.Counter((norm(r[2]),r[1]) for r in phases)
    wanted=collections.Counter({(name,phase):1 for name in METHODS for phase in ('total','compile')})
    wanted.update({(name,'execute'):1 for name in METHODS if name!='test056d'})
    assert inventory==wanted,(inventory,wanted)
    classes={str(p.relative_to(MODULE/'target/classes')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((MODULE/'target/classes').rglob('*.class'))}
    assert classes
    (dest/'class-fingerprints.json').write_text(json.dumps(classes,indent=2))
    if fingerprint is None: fingerprint=classes
    assert classes==fingerprint,'Compiled test bytes changed across observations'
    results.append({'sample':dest.name,'arm':arm,'runtime':expected,'tests':4,'phases':[{'method':norm(r[2]),'phase':r[1],'wall_ms':int(r[3])/1e6,'process_cpu_ms':int(r[4])/1e6} for r in phases]})
    (OUT/'results.json').write_text(json.dumps({'comparison_complete':A is not None,'scope':'Four original methods at compliance 17. Fresh test JVM/workspace, same build JVM and runner. Phase CPU excludes children; GNU time covers the whole invocation.','samples':results},indent=2))
print(json.dumps({'A_available':A is not None,'completed_samples':len(results)},indent=2))
if A is None:
    raise SystemExit('B baseline completed; exact Jenkins JDK A unavailable. This is NOT a completed A/B comparison.')
