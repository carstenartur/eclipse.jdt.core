from pathlib import Path
p=Path('org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/ClassFileBufferPublicationTests.java')
s=p.read_text()
s=s.replace('import java.util.concurrent.CountDownLatch;', 'import java.util.concurrent.BrokenBarrierException;\nimport java.util.concurrent.CountDownLatch;\nimport java.util.concurrent.CyclicBarrier;')
s=s.replace('import java.util.concurrent.TimeUnit;', 'import java.util.concurrent.TimeUnit;\nimport java.util.concurrent.TimeoutException;')
s=s.replace('import java.util.concurrent.atomic.AtomicBoolean;', 'import java.util.concurrent.atomic.AtomicBoolean;\nimport java.util.concurrent.atomic.AtomicInteger;')
s=s.replace('import org.eclipse.jdt.core.IPackageFragmentRoot;', 'import org.eclipse.jdt.core.IPackageFragmentRoot;\nimport org.eclipse.jdt.core.IOpenable;')
s=s.replace('public class X {}\\n', 'public class X { public static class Inner {} }\\n')
start=s.index('\tprivate void assertSourcePublished(')
s=s[:start]+'''	public void testConcurrentClassOpensReuseBuffer() throws Exception {
		assertConcurrentOpens(FileKind.ORDINARY, SourceAttachment.PRESENT, false);
	}

	public void testConcurrentModuleOpensReuseBuffer() throws Exception {
		assertConcurrentOpens(FileKind.MODULAR, SourceAttachment.PRESENT, false);
	}

	public void testConcurrentClassOpensReuseNullBuffer() throws Exception {
		assertConcurrentOpens(FileKind.ORDINARY, SourceAttachment.MISSING_ENTRY, false);
	}

	public void testConcurrentModuleOpensReuseNullBuffer() throws Exception {
		assertConcurrentOpens(FileKind.MODULAR, SourceAttachment.MISSING_ENTRY, false);
	}

	public void testConcurrentOuterAndInnerOpensReuseBuffer() throws Exception {
		assertConcurrentOpens(FileKind.ORDINARY, SourceAttachment.PRESENT, true);
	}

	public void testConcurrentOuterAndInnerOpensReuseNullBuffer() throws Exception {
		assertConcurrentOpens(FileKind.ORDINARY, SourceAttachment.MISSING_ENTRY, true);
	}

	private void assertConcurrentOpens(FileKind kind, SourceAttachment attachment, boolean useInner) throws Exception {
		ConcurrentBufferManager manager = new ConcurrentBufferManager();
		// These tests pause cache misses, not publication.
		manager.resume();
		try (PublicationFixture fixture = new PublicationFixture(kind, attachment, manager)) {
			IClassFile other = useInner ? fixture.createClassFile("X$Inner") : fixture.classFile;
			other.open(null);
			int misses = kind == FileKind.ORDINARY ? 2 : 1;
			Future<IBuffer> first = fixture.workers.submit(() -> manager.open(fixture.classFile, misses));
			Future<IBuffer> second = fixture.workers.submit(() -> manager.open(other, misses));
			IBuffer firstBuffer = first.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
			IBuffer secondBuffer = second.get(TIMEOUT_SECONDS, TimeUnit.SECONDS);
			assertEquals("Concurrent cache misses must publish one buffer", 1, manager.additions.get());
			IBuffer cached = manager.getBuffer(fixture.classFile);
			assertNotNull("Discarding a competing buffer must retain the cached buffer", cached);
			assertFalse("Discarding a competing buffer must not close the cached buffer", cached.isClosed());
			assertEquals("Inner classes must use the outer class as buffer owner", fixture.classFile, cached.getOwner());
			if (attachment == SourceAttachment.PRESENT) {
				assertSame("Both callers must receive the cached buffer", cached, firstBuffer);
				assertSame("Both callers must receive the cached buffer", cached, secondBuffer);
			} else {
				assertTrue("Missing source must remain a cached NullBuffer", cached instanceof NullBuffer);
				assertNull(firstBuffer);
				assertNull(secondBuffer);
			}
			assertEquals(fixture.source, fixture.classFile.getSource());
			assertEquals(fixture.source, other.getSource());
			assertSame("Subsequent access must retain the shared buffer", cached, manager.getBuffer(fixture.classFile));
			cached.close();
			assertNull("The winning buffer must have its close listener installed", manager.getBuffer(fixture.classFile));
			assertEquals("Closing must allow source lookup to reopen the buffer", fixture.source, other.getSource());
			IBuffer reopened = manager.getBuffer(fixture.classFile);
			assertNotNull(reopened);
			assertNotSame(cached, reopened);
			assertFalse(reopened.isClosed());
		}
	}

'''+s[start:]
s=s.replace('final PausingBufferManager manager = new PausingBufferManager();','final PausingBufferManager manager;')
s=s.replace('final IJavaProject project;','final IJavaProject project;\n\t\tfinal IPackageFragmentRoot root;')
s=s.replace('PublicationFixture(FileKind kind, SourceAttachment attachment) throws Exception {\n\t\t\tthis.project', 'PublicationFixture(FileKind kind, SourceAttachment attachment) throws Exception {\n\t\t\tthis(kind, attachment, new PausingBufferManager());\n\t\t}\n\n\t\tPublicationFixture(FileKind kind, SourceAttachment attachment, PausingBufferManager manager) throws Exception {\n\t\t\tthis.manager = manager;\n\t\t\tthis.project')
s=s.replace('IPackageFragmentRoot root = this.project.getPackageFragmentRoot(', 'this.root = this.project.getPackageFragmentRoot(')
a=s.index('\t\t\t\t\tcase ORDINARY -> new ClassFile')
b=s.index('\t\t\t\t\tcase MODULAR', a)
s=s[:a]+'\t\t\t\t\tcase ORDINARY -> createClassFile("X");\n'+s[b:]
s=s.replace('root.getPackageFragment("")','this.root.getPackageFragment("")')
a=s.index('\t\tFuture<String> startWriter()')
s=s[:a]+'''		ClassFile createClassFile(String name) {
			return new ClassFile((PackageFragment) this.root.getPackageFragment("p"), name) {
				@Override
				protected BufferManager getBufferManager() {
					return PublicationFixture.this.manager;
				}
			};
		}

'''+s[a:]
s=s.replace('private static final class PausingBufferManager', 'private static class PausingBufferManager')
s=s[:-2]+'''
	/**
	 * Return the real empty-cache observations only after both callers have made
	 * them. ClassFile checks its own key and then its outermost owner's key;
	 * ModularClassFile checks just its own key. Rechecks under the manager lock
	 * are deliberately not paused: they must observe the winner's publication.
	 */
	private static final class ConcurrentBufferManager extends PausingBufferManager {
		final AtomicInteger additions = new AtomicInteger();
		private final CyclicBarrier misses = new CyclicBarrier(2);
		private final ThreadLocal<Integer> remainingMisses = new ThreadLocal<>();

		IBuffer open(IClassFile classFile, int expectedMisses) throws Exception {
			this.remainingMisses.set(expectedMisses);
			try {
				IBuffer buffer = classFile.getBuffer();
				assertEquals("Both callers must traverse the empty-cache path", 0, this.remainingMisses.get().intValue());
				return buffer;
			} finally {
				this.remainingMisses.remove();
			}
		}

		@Override
		public IBuffer getBuffer(IOpenable owner) {
			IBuffer buffer = super.getBuffer(owner);
			Integer remaining = this.remainingMisses.get();
			if (remaining != null && remaining > 0 && !Thread.holdsLock(this)) {
				assertNull("The controlled lookup must observe an empty cache", buffer);
				this.remainingMisses.set(remaining - 1);
				try {
					this.misses.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
				} catch (InterruptedException e) {
					Thread.currentThread().interrupt();
					throw new AssertionError("Interrupted while coordinating cache misses", e);
				} catch (BrokenBarrierException | TimeoutException e) {
					throw new AssertionError("Both readers must reach the cache miss", e);
				}
			}
			return buffer;
		}

		@Override
		protected void addBuffer(IBuffer buffer) {
			this.additions.incrementAndGet();
			super.addBuffer(buffer);
		}
	}
}
'''
p.write_text(s)
print(len(s.splitlines()), 'lines', s.count('public void test'), 'tests')
