#!/usr/bin/env python3
"""Apply identical, checked diagnostic hooks to each freshly checked-out revision."""
from pathlib import Path
import difflib, hashlib, json, re, shutil, subprocess, sys

root, tools, out = map(lambda s: Path(s).resolve(), sys.argv[1:4])
java = sys.argv[4]
out.mkdir(parents=True, exist_ok=True)
trace = 'org.eclipse.jdt.internal.codeassist.Completion5364Trace'
changes = []

def edit(path, transform):
    file = root / path
    old = file.read_text()
    new = transform(old)
    if new == old: raise RuntimeError('No instrumentation: '+path)
    file.write_text(new)
    changes.append({'path': path, 'before': hashlib.sha256(old.encode()).hexdigest(), 'after': hashlib.sha256(new.encode()).hexdigest()})
    with (out/'instrumentation.patch').open('a') as f:
        f.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))

def once(text, old, new):
    if text.count(old) != 1: raise RuntimeError(f'Expected unique anchor ({text.count(old)}): {old[:120]}')
    return text.replace(old,new,1)

def section(text, start, end, fn):
    a = text.index(start); b = text.index(end,a+len(start))
    return text[:a]+fn(text[a:b])+text[b:]

def catches(s):
    return re.sub(r'(catch\s*\([^)]*\b(\w+)\)\s*\{)',
        lambda m: m[1]+f'\n            if ({trace}.active()) {trace}.event("CAUGHT_L{s[:m.start()].count(chr(10))+1}", {m[2]});',s)

def engine(s):
    s=once(s,'\t\tsuper(settings);','\t\tsuper(settings);\n\t\t'+trace+'.options(settings);')
    s=once(s,'\t\tthis.complianceLevel = javaProject.getOption(JavaCore.COMPILER_COMPLIANCE, true);',
        '\t\tthis.complianceLevel = javaProject.getOption(JavaCore.COMPILER_COMPLIANCE, true);\n'
        f'\t\tif ({trace}.active()) {trace}.event("LEVELS", "source=" + this.sourceLevel + " compliance=" + this.complianceLevel);')
    s=once(s,'\t\t\tthis.source = sourceUnit.getContents();',
        '\t\t\tthis.source = sourceUnit.getContents();\n'
        f'\t\t\tif ({trace}.active()) {trace}.event("SOURCE", new String(this.source));')
    s,n=re.subn(r'(CompletionEngine\.this|this)\.requestor\.accept\((\w+)\)',
        lambda m:f'{trace}.deliver({m[1]}.requestor, {m[2]})',s)
    if n<20: raise RuntimeError('Unexpected proposal delivery sites: '+str(n))
    def accept(block):
        block=once(block,'\n\t\t// does not check cancellation',
            f'\n\t\t{trace}.type("ENGINE_CANDIDATE", packageName, simpleTypeName, modifiers);\n\t\t// does not check cancellation')
        block=re.sub(r'\breturn;',lambda m:'{ '+trace+'.name("ENGINE_REJECT_L'+str(block[:m.start()].count('\n')+1)+'", simpleTypeName); return; }',block)
        return block.replace('this.acceptedTypes.add(new AcceptedType',trace+'.name("ENGINE_QUEUED", simpleTypeName);\n\t\tthis.acceptedTypes.add(new AcceptedType')
    s=section(s,'\tpublic void acceptType(','\tprivate void acceptTypes(',accept)
    s=once(s,'\t\t\t\tif (this.knownTypes.containsKey(fullyQualifiedName)) continue next;',
        f'\t\t\t\tif (this.knownTypes.containsKey(fullyQualifiedName)) {{ {trace}.name("KNOWN_TYPE_SKIP", fullyQualifiedName); continue next; }}')
    def propose(block):
        return once(block,'\t\tchar[] completionName = fullyQualifiedName;',f'\t\t{trace}.name("PROPOSE_TYPE", fullyQualifiedName);\n\t\tchar[] completionName = fullyQualifiedName;')
    s=section(s,'\tprivate void proposeType(','\tprotected void reset()',propose)
    return catches(s)

def environment(s):
    def types(block):
        anchor='\n\t\tlong start = -1;'
        block=once(block,anchor,f'\n\t\tif ({trace}.active()) {trace}.event("SEARCH", "prefix=" + new String(prefix) + " rule=" + matchRule + " filter=" + searchFor + " monitor=" + (monitor != null));'+anchor)
        block=once(block,'\t\t\t\t\tif (excludePath != null && excludePath.equals(path))',
            f'\t\t\t\t\t{trace}.type("INDEX_CANDIDATE", packageName, simpleTypeName, modifiers);\n\t\t\t\t\tif (excludePath != null && excludePath.equals(path))')
        block=block.replace('indexManager.awaitingJobsCount() == 0','loggedPendingJobs(indexManager.awaitingJobsCount()) == 0')
        block=block.replace('new BasicSearchEngine(this.workingCopies).searchAllTypeNames(',
            trace+'.event("SEARCH_PATH", "INDEX");\n\t\t\t\t\tnew BasicSearchEngine(this.workingCopies).searchAllTypeNames(')
        return block
    s=section(s,'\tpublic void findTypes(char[] prefix, final boolean findMembers, int matchRule, int searchFor, final boolean resolveDocumentName,',
        '\tpublic void findConstructorDeclarations(',types)
    s=once(s,'\tprivate void findTypes(String prefix, ISearchRequestor storage, int type) {',
        '\tprivate static int loggedPendingJobs(int count) {\n\t\t'+trace+'.event("PENDING_INDEX_JOBS", count);\n\t\treturn count;\n\t}\n\n'
        '\tprivate void findTypes(String prefix, ISearchRequestor storage, int type) {\n'
        f'\t\tif ({trace}.active()) {trace}.event("SEARCH_PATH", "MODEL prefix=" + prefix + " filter=" + type);')
    return catches(s)

def lookup(s):
    s=once(s,'\t\tthis.packageFragmentRoots = packageFragmentRoots;',
        '\t\tthis.packageFragmentRoots = packageFragmentRoots;\n'
        f'\t\tif ({trace}.active()) {{\n\t\t\tfor (IPackageFragmentRoot r : packageFragmentRoots) {trace}.event("LOOKUP_ROOT", r.getPath());\n\t\t}}')
    def binary(block):
        block=once(block,'\t\tname= DeduplicationUtil.intern(name);',
            f'\t\tif ({trace}.active() && "java.lang".equals(pkg.getElementName())) {trace}.event("MODEL_BINARY", name + " flags=" + acceptFlags);\n\t\tname= DeduplicationUtil.intern(name);')
        block=once(block,'\t\t\t\t\tclassFiles= pkg.getChildren();',
            '\t\t\t\t\tclassFiles= pkg.getChildren();\n'
            f'\t\t\t\t\tif ({trace}.active() && "java.lang".equals(pkg.getElementName())) {trace}.event("MODEL_CHILDREN", classFiles.length);')
        block=block.replace('requestor.acceptType(type);',f'{{ {trace}.event("MODEL_ACCEPT", type.getElementName()); requestor.acceptType(type); }}')
        return block
    s=section(s,'\tprotected void seekTypesInBinaryPackage(', '\tprotected void seekTypesInSourcePackage(',binary)
    return catches(s)

edit('org.eclipse.jdt.core/codeassist/org/eclipse/jdt/internal/codeassist/CompletionEngine.java',engine)
edit('org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/SearchableEnvironment.java',environment)
edit('org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/NameLookup.java',lookup)
for name,target in [('Completion5364Trace.java','org.eclipse.jdt.core/codeassist/org/eclipse/jdt/internal/codeassist'),('Completion5364MavenTests.java','org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model')]:
    shutil.copyfile(tools/name,root/target/name)

def pom(s):
    s=once(s,'<id>JavaSE-21</id>',f'<id>JavaSE-{java}</id><!-- diagnostic test JVM -->')
    return once(s,'<include>org/eclipse/jdt/core/tests/RunAllJdtModelTestsTracing.class</include>',
        '<include>org/eclipse/jdt/core/tests/model/Completion5364MavenTests.class</include>')
edit('org.eclipse.jdt.core.tests.model/pom.xml',pom)
(out/'source-hashes.json').write_text(json.dumps(changes,indent=2)+'\n')
(out/'original-test-sha256.txt').write_text(hashlib.sha256((root/'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/CompletionTests16_2.java').read_bytes()).hexdigest()+'\n')
print('INSTRUMENTED',root,'test JVM',java)
