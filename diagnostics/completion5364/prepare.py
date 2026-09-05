from pathlib import Path
import sys, zipfile, io, tarfile, subprocess, os, re, shutil, hashlib, json

root=Path.cwd(); work=Path(os.environ['RUNNER_TEMP'])/'completion5364'; work.mkdir(exist_ok=True)
evidence=root/'evidence'; evidence.mkdir(exist_ok=True)
sdk=work/'eclipse'
with tarfile.open(work/'sdk.tar.gz') as z: z.extractall(work,filter='data')
with zipfile.ZipFile(work/'tests.zip') as z:
    nested=z.read('eclipse-testing/eclipse-junit-tests-I20260826-2300.zip')
with zipfile.ZipFile(io.BytesIO(nested)) as z: z.extractall(work/'tests')
info=sdk/'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
lines=info.read_text().splitlines()
for p in sorted((work/'tests/plugins').glob('*.jar')):
    with zipfile.ZipFile(p) as z:
        manifest=z.read('META-INF/MANIFEST.MF').decode().replace('\r\n ', '').split('\r\n\r\n')[0]
        fields=dict(line.split(': ',1) for line in manifest.splitlines() if ': ' in line)
        bsn=fields['Bundle-SymbolicName'].split(';')[0]; version=fields['Bundle-Version']
        if any(line.startswith(bsn+',') for line in lines): continue
        directory=fields.get('Eclipse-BundleShape')=='dir'
        target=sdk/'plugins'/(p.stem if directory else p.name)
        if directory: z.extractall(target)
        else: shutil.copyfile(p,target)
        lines.append(f'{bsn},{version},plugins/{target.name},4,false')
info.write_text('\n'.join(lines)+'\n')
plugins=sorted(p for p in (sdk/'plugins').iterdir() if p.is_dir() or p.suffix=='.jar')
cp=os.pathsep.join(map(str,plugins))
empty=work/'empty';empty.mkdir(exist_ok=True)
def compile_java(sources, output):
    output.mkdir(exist_ok=True)
    subprocess.run(['javac','--release','21','-proc:none','-implicit:none','-sourcepath',str(empty),'-cp',cp,'-d',str(output),*[str(s) for s in sources]],check=True)

def replace_classes(bundle, classes, prefixes):
    def selected(name): return any(name == p+'.class' or (name.startswith(p+'$') and name.endswith('.class')) for p in prefixes)
    if bundle.is_dir():
        for p in bundle.rglob('*.class'):
            if selected(p.relative_to(bundle).as_posix()): p.unlink()
        shutil.copytree(classes,bundle,dirs_exist_ok=True)
        return
    tmp=bundle.with_suffix('.replacement')
    with zipfile.ZipFile(bundle) as old,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as new:
        for e in old.infolist():
            n=e.filename
            if selected(n) or (n.upper().startswith('META-INF/') and n.upper().endswith(('.SF','.RSA','.DSA','.EC'))): continue
            new.writestr(e,old.read(n))
        for p in classes.rglob('*.class'): new.writestr(p.relative_to(classes).as_posix(),p.read_bytes())
    tmp.replace(bundle)

# Execute the current original test and its setup classes, not a hand-written equivalent.
testbase=root/'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model'
names=['CompletionTests16_2','CompletionTests16_1','AbstractJavaModelCompletionTests','AbstractJavaModelTests','CompletionTestsRequestor2']
classes=work/'test-classes';compile_java([testbase/(n+'.java') for n in names],classes)
testbundle=next(p for p in plugins if p.name.startswith('org.eclipse.jdt.core.tests.model_'))
replace_classes(testbundle,classes,['org/eclipse/jdt/core/tests/model/'+n for n in names])
(evidence/'test-source-hashes.json').write_text(json.dumps({n:hashlib.sha256((testbase/(n+'.java')).read_bytes()).hexdigest() for n in names},indent=2))

corepath='org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java'
arm=sys.argv[1]; revision={'base':'8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51','pr':'d55a8c72e96ba601562fda02e5698da6323d37e7'}[arm]
source=work/'JavaModelManager.java';source.write_bytes(subprocess.check_output(['git','show',revision+':'+corepath]))
classes=work/'core-classes';compile_java([source],classes)
core=next(p for p in plugins if p.name.startswith('org.eclipse.jdt.core_'))
replace_classes(core,classes,['org/eclipse/jdt/internal/core/JavaModelManager'])
print('CORE_ARM',arm,revision,hashlib.sha256(source.read_bytes()).hexdigest(),flush=True)

classes=work/'app-classes';compile_java([root/'diagnostics/completion5364/ProbeApplication.java'],classes)
manifest=work/'MANIFEST.MF';manifest.write_text('''Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-SymbolicName: completion5364.probe;singleton:=true
Bundle-Version: 1.0.0
Bundle-RequiredExecutionEnvironment: JavaSE-21
Require-Bundle: org.eclipse.equinox.app,org.eclipse.core.runtime,
 org.eclipse.jdt.core,org.eclipse.jdt.core.tests.model,
 org.eclipse.jdt.core.tests.compiler,org.junit

''')
(classes/'plugin.xml').write_text('''<plugin><extension point="org.eclipse.core.runtime.applications" id="run"><application cardinality="singleton-global" thread="main" visible="true"><run class="diagnostics.ProbeApplication"/></application></extension></plugin>''')
subprocess.run(['jar','cfm',str(sdk/'plugins/completion5364.probe_1.0.0.jar'),str(manifest),'-C',str(classes),'.'],check=True)
with info.open('a') as f:f.write('completion5364.probe,1.0.0,plugins/completion5364.probe_1.0.0.jar,4,false\n')
print('SDK_READY',sdk,flush=True)
