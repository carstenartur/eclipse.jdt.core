"""Apply the reviewed cache-recheck fix; candidate sources are exported only after QA."""
from pathlib import Path
core=Path('org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core')
p=core/'ClassFile.java'
s=p.read_text()
a=s.index('private IBuffer mapSource(SourceMapper mapper, IBinaryType info, IClassFile bufferOwner) {')
b=s.index('\n/* package */ static String simpleName',a)
s=s[:a]+'''private IBuffer mapSource(SourceMapper mapper, IBinaryType info, IClassFile bufferOwner) {
	char[] contents = mapper.findSource(getType(), info);
	IBuffer buffer = contents != null
			? BufferManager.createBuffer(bufferOwner)
			: BufferManager.createNullBuffer(bufferOwner);
	if (buffer == null) return null;
	BufferManager bufManager = getBufferManager();
	IBuffer existingBuffer;
	// Recheck the shared owner's key before publishing a competing buffer.
	synchronized (bufManager) {
		existingBuffer = bufManager.getBuffer(bufferOwner);
		if (existingBuffer == null) {
			if (contents != null && buffer.getCharacters() == null) {
				buffer.setContents(contents);
			}
			// Cached buffers must already have their contents and close listener.
			buffer.addBufferChangedListener(this);
			bufManager.addBuffer(buffer);
		}
	}
	if (existingBuffer != null) {
		// No listener was installed on this unpublished candidate.
		buffer.close();
		return existingBuffer;
	}
	if (contents != null) {
		// Keep source mapping and Java-model access outside the manager lock.
		mapper.mapSource((NamedMember) getOuterMostEnclosingType(), contents, info);
	}
	return buffer;
}
'''+s[b:]
p.write_text(s)
p=core/'ModularClassFile.java'
s=p.read_text()
a=s.index('\tprivate IBuffer mapSource(SourceMapper mapper) throws JavaModelException {')
b=s.index('\n\t@Override\n\tpublic IModuleDescription getModule()',a)
s=s[:a]+'''	private IBuffer mapSource(SourceMapper mapper) throws JavaModelException {
		char[] contents = mapper.findSource(getModule());
		IBuffer buffer = contents != null
				? BufferManager.createBuffer(this)
				: BufferManager.createNullBuffer(this);
		if (buffer == null) return null;
		BufferManager bufManager = getBufferManager();
		IBuffer existingBuffer;
		// Recheck before publishing a competing source buffer or NullBuffer.
		synchronized (bufManager) {
			existingBuffer = bufManager.getBuffer(this);
			if (existingBuffer == null) {
				if (contents != null && buffer.getCharacters() == null) {
					buffer.setContents(contents);
				}
				// Cached buffers must already have their contents and close listener.
				buffer.addBufferChangedListener(this);
				bufManager.addBuffer(buffer);
			}
		}
		if (existingBuffer != null) {
			// No listener was installed on this unpublished candidate.
			buffer.close();
			return existingBuffer;
		}
		if (contents != null) {
			// Keep source mapping and Java-model access outside the manager lock.
			mapper.mapSource((NamedMember) getModule(), contents, null);
		}
		return buffer;
	}
'''+s[b:]
p.write_text(s)
