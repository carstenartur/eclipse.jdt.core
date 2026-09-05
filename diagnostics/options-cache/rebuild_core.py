#!/usr/bin/env python3
from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys
import zipfile

sdk, candidate, evidence = map(lambda x: Path(x).resolve(), sys.argv[1:])
source_entry = 'org/eclipse/jdt/internal/core/JavaModelManager.java'
prefix = source_entry[:-5]
def one(pattern):
    found = list((sdk/'plugins').glob(pattern))
    if len(found) != 1:
        raise SystemExit('Bundle selection not unique: '+str(found))
    return found[0]
with zipfile.ZipFile(one('org.eclipse.jdt.core.source_*.jar')) as z:
    sdk_source = z.read(source_entry).decode()
expected = {
 'public Hashtable<String, String> getOptions()': 'ae1d69fc7e8f91996c2ea9553c8a93861072cad1d768be9e606ed5f16cf94b06',
 'public void setOptions(Hashtable<String, String> newOptions)': '49636cb5d2d6ff5a848e422b318e826d715e96d99ee286c33c3a2f5d0cb8abc9',
}
for signature, known in expected.items():
    start=sdk_source.index(signature); end=sdk_source.index('\n\t}',start)+3
    digest=hashlib.sha256(re.sub(r'\s+',' ',sdk_source[start:end]).strip().encode()).hexdigest()
    if digest != known:
        raise SystemExit('Unexpected SDK method: '+signature+' '+digest)
    print('BASELINE_SOURCE_MATCH', signature, digest, flush=True)
jars=sorted((sdk/'plugins').glob('*.jar'))
def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in jars}
before=hashes()
classes=evidence/'compiled-core'; classes.mkdir()
empty=evidence/'empty-sourcepath'; empty.mkdir()
cp=os.pathsep.join(str(p) for p in jars if '.source_' not in p.name)
subprocess.run(['javac','--release','21','-proc:none','-implicit:none','-sourcepath',str(empty),'-cp',cp,'-d',str(classes),str(candidate)],check=True)
compiled={p.relative_to(classes).as_posix():p.read_bytes() for p in classes.rglob('*.class')}
if prefix+'.class' not in compiled or any(not n.startswith(prefix) for n in compiled):
    raise SystemExit('Unexpected compiler output')
core=one('org.eclipse.jdt.core_*.jar')
tmp=core.with_suffix('.replacement')
with zipfile.ZipFile(core) as old, zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as new:
    for entry in old.infolist():
        name=entry.filename
        if name.upper().startswith('META-INF/') and name.upper().endswith(('.SF','.RSA','.DSA','.EC')):
            continue
        if name == prefix+'.class' or (name.startswith(prefix+'$') and name.endswith('.class')):
            continue
        new.writestr(entry,old.read(name))
    for name,data in sorted(compiled.items()):
        new.writestr(name,data)
tmp.replace(core)
after=hashes()
changed=[name for name in before if before[name]!=after[name]]
assert changed == [core.name], changed
(evidence/'bundle-provenance.txt').write_text('\n'.join(f'{name} before={before[name]} after={after[name]}' for name in before)+'\n')
(evidence/'candidate-source-sha256.txt').write_text(hashlib.sha256(candidate.read_bytes()).hexdigest()+'\n')
print('PATCHED_UPSTREAM_CLASS',candidate,'classes',len(compiled),'changed bundles',changed,flush=True)
