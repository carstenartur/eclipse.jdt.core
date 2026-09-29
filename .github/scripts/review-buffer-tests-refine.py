"""Keep the concurrent-open tests independent of cache-lookup counts/lock layout."""
from pathlib import Path
p=Path('org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/ClassFileBufferPublicationTests.java')
s=p.read_text().replace('import org.eclipse.jdt.core.IOpenable;\n','')
s=s.replace('import org.eclipse.jdt.internal.core.ClassFile;', 'import org.eclipse.jdt.internal.core.ClassFile;\nimport org.eclipse.jdt.internal.core.JavaElement;')
s=s.replace('import org.eclipse.jdt.internal.core.PackageFragment;', 'import org.eclipse.jdt.internal.core.PackageFragment;\nimport org.eclipse.jdt.internal.core.SourceMapper;')
s=s.replace('IClassFile other = useInner ? fixture.createClassFile("X$Inner") : fixture.classFile;', 'IClassFile other = useInner ? fixture.createClassFile("X$Inner")\n\t\t\t\t\t: kind == FileKind.ORDINARY ? fixture.createClassFile("X") : fixture.createModularClassFile();\n\t\t\tassertNotSame("Exercise distinct handles sharing a cache key", fixture.classFile, other);\n\t\t\tassertNotNull(((JavaElement) fixture.classFile).getSourceMapper());')
s=s.replace('\t\t\tint misses = kind == FileKind.ORDINARY ? 2 : 1;\n', '')
s=s.replace('manager.open(fixture.classFile, misses)', 'manager.open(fixture.classFile)').replace('manager.open(other, misses)', 'manager.open(other)')
a=s.index('\t\t\t\t\tcase MODULAR -> new ModularClassFile')
b=s.index('\n\t\t\t\t};', a)
s=s[:a]+'\t\t\t\t\tcase MODULAR -> createModularClassFile();'+s[b:]
old='''					return PublicationFixture.this.manager;
				}
'''
new=old+'''
				@Override
				public SourceMapper getSourceMapper() {
					SourceMapper mapper = super.getSourceMapper();
					PublicationFixture.this.manager.beforeSourceLookup();
					return mapper;
				}
'''
assert s.count(old)==1
s=s.replace(old,new)
a=s.index('\t\tFuture<String> startWriter()')
s=s[:a]+'''		ModularClassFile createModularClassFile() {
			return new ModularClassFile((PackageFragment) this.root.getPackageFragment("")) {
				@Override
				protected BufferManager getBufferManager() {
					return PublicationFixture.this.manager;
				}

				@Override
				public SourceMapper getSourceMapper() {
					SourceMapper mapper = super.getSourceMapper();
					PublicationFixture.this.manager.beforeSourceLookup();
					return mapper;
				}
			};
		}

'''+s[a:]
a=s.index('\t\tvoid resume()')
s=s[:a]+'''		void beforeSourceLookup() {
			// Only concurrent-creation tests pause here.
		}

'''+s[a:]
a=s.index('\n\t/**\n\t * Return the real empty-cache observations')
s=s[:a]+'''
	/** Pause after the real cache misses, before either caller can create a buffer. */
	private static final class ConcurrentBufferManager extends PausingBufferManager {
		final AtomicInteger additions = new AtomicInteger();
		private final CyclicBarrier lookups = new CyclicBarrier(2);
		private final ThreadLocal<Boolean> awaitingLookup = new ThreadLocal<>();

		IBuffer open(IClassFile classFile) throws Exception {
			this.awaitingLookup.set(Boolean.TRUE);
			try {
				IBuffer buffer = classFile.getBuffer();
				assertEquals("Both callers must enter source lookup", Boolean.FALSE, this.awaitingLookup.get());
				return buffer;
			} finally {
				this.awaitingLookup.remove();
			}
		}

		@Override
		void beforeSourceLookup() {
			if (Boolean.TRUE.equals(this.awaitingLookup.get())) {
				this.awaitingLookup.set(Boolean.FALSE);
				try {
					this.lookups.await(TIMEOUT_SECONDS, TimeUnit.SECONDS);
				} catch (InterruptedException e) {
					Thread.currentThread().interrupt();
					throw new AssertionError("Interrupted while coordinating source lookup", e);
				} catch (BrokenBarrierException | TimeoutException e) {
					throw new AssertionError("Both readers must reach source lookup", e);
				}
			}
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
