#!/usr/bin/env python3
from pathlib import Path
import difflib
import hashlib
import json
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
upstream = (evidence/'JavaModelManager.baseline.java').read_text()
provenance = []
for signature in ['public Hashtable<String, String> getOptions()', 'public void setOptions(Hashtable<String, String> newOptions)']:
    def method(source):
        start=source.index(signature)
        end=source.index('\n\t}',start)+3
        return re.sub(r'\s+',' ',source[start:end]).strip()
    actual, expected = method(sdk_source), method(upstream)
    record = {'method': signature, 'equal': actual == expected,
              'sdk_sha256': hashlib.sha256(actual.encode()).hexdigest(),
              'upstream_sha256': hashlib.sha256(expected.encode()).hexdigest()}
    provenance.append(record)
    print('BASELINE_SOURCE_COMPARISON',json.dumps(record),flush=True)
    if actual != expected:
        (evidence/'sdk-upstream-method-mismatch.txt').write_text('\n'.join(difflib.unified_diff(expected.split(),actual.split())))
        raise SystemExit('SDK differs from the pinned upstream method; refusing a misleading baseline comparison')
(evidence/'method-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
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
