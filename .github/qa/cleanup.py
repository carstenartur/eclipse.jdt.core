from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

ROOT = Path('qa-cleanup')
MODEL = Path('org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model')

TESTS = '''
	public void testCleanupContinuesAfterExecutorFailure() throws Exception {
		assertCleanupContinues(true, false);
	}

	public void testCleanupContinuesAfterJobFailure() throws Exception {
		assertCleanupContinues(false, true);
	}

	public void testCleanupRetainsMultipleFailures() throws Exception {
		assertCleanupContinues(true, true);
	}

	private void assertCleanupContinues(boolean executorFails, boolean jobFails) throws Exception {
		junit.framework.AssertionFailedError executorFailure = new junit.framework.AssertionFailedError("executor cleanup failure");
		junit.framework.AssertionFailedError jobFailure = new junit.framework.AssertionFailedError("job cleanup failure");
		List<Job> joined = new ArrayList<>();
		JobFamilyWaitTests fixture = new JobFamilyWaitTests("cleanup fixture") {
			@Override
			void awaitExecutorTermination() throws InterruptedException {
				super.awaitExecutorTermination();
				if (executorFails) {
					throw executorFailure;
				}
			}

			@Override
			void awaitJobTermination(Job job) throws InterruptedException {
				joined.add(job);
				super.awaitJobTermination(job);
				if (jobFails && joined.size() == 1) {
					throw jobFailure;
				}
			}
		};
		fixture.setUp();
		fixture.job(new Object(), monitor -> { });
		fixture.job(new Object(), monitor -> { });
		Throwable observed = null;
		try {
			fixture.tearDown();
		} catch (Throwable failure) {
			observed = failure;
		}
		assertEquals("Every owned job must be joined even after a cleanup failure", fixture.jobs, joined);
		if (executorFails && jobFails) {
			assertTrue("Both cleanup failures must be retained", observed instanceof org.junit.runners.model.MultipleFailureException);
			org.junit.runners.model.MultipleFailureException multiple = (org.junit.runners.model.MultipleFailureException) observed;
			assertEquals(List.of(executorFailure, jobFailure), multiple.getFailures());
		} else {
			assertSame("Preserve the original cleanup failure", executorFails ? executorFailure : jobFailure, observed);
		}
	}

	void awaitExecutorTermination() throws InterruptedException {
		assertTrue("Waiter thread did not terminate",
				this.executor.awaitTermination(TIMEOUT_SECONDS, TimeUnit.SECONDS));
	}

	void awaitJobTermination(Job job) throws InterruptedException {
		assertTrue("Test job did not terminate: " + job,
				job.join(TimeUnit.SECONDS.toMillis(TIMEOUT_SECONDS), null));
	}
'''

CLEANUP = '''	@Override
	protected void tearDown() throws Exception {
		List<Throwable> failures = new ArrayList<>();
		for (Job job : this.jobs) {
			collectCleanupFailure(failures, () -> job.cancel());
		}
		collectCleanupFailure(failures, () -> this.executor.shutdownNow());
		collectCleanupFailure(failures, this::awaitExecutorTermination);
		for (Job job : this.jobs) {
			collectCleanupFailure(failures, () -> awaitJobTermination(job));
		}
		collectCleanupFailure(failures, () -> super.tearDown());
		for (Throwable failure : failures) {
			if (failure instanceof InterruptedException) {
				Thread.currentThread().interrupt();
				break;
			}
		}
		org.junit.runners.model.MultipleFailureException.assertEmpty(failures);
	}

	private static void collectCleanupFailure(List<Throwable> failures, CleanupStep step) {
		try {
			step.run();
		} catch (Throwable failure) {
			// Report after attempting the remaining cleanup, including assertion errors.
			failures.add(failure);
		}
	}

	@FunctionalInterface
	private interface CleanupStep {
		void run() throws Exception;
	}
'''


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def prepare():
    ROOT.mkdir()
    original = (MODEL / 'JobFamilyWaitTests.java').read_text()
    before = replace_once(original,
        '\t\t\tassertTrue("Waiter thread did not terminate",\n\t\t\t\t\tthis.executor.awaitTermination(TIMEOUT_SECONDS, TimeUnit.SECONDS));',
        '\t\t\tawaitExecutorTermination();')
    before = replace_once(before,
        '\t\t\t\tassertTrue("Test job did not terminate: " + job,\n\t\t\t\t\t\tjob.join(TimeUnit.SECONDS.toMillis(TIMEOUT_SECONDS), null));',
        '\t\t\t\tawaitJobTermination(job);')
    before = replace_once(before, '\tprivate Future<?> waitFor(', TESTS + '\n\tprivate Future<?> waitFor(')
    start = before.index('\t@Override\n\tprotected void tearDown()')
    end = before.index('\n\tpublic void testEmptyFamily()', start)
    after = before[:start] + CLEANUP + before[end:]
    after = after.replace('beforeJoin(() -> { throw expected; })', 'beforeJoin(() -> {\n\t\t\t\tthrow expected;\n\t\t\t})')
    imports = re.findall(r'^import .+;$', after, re.M)
    import_start = after.index('import ')
    import_end = after.index('\n\npublic class JobFamilyWaitTests')
    after = after[:import_start] + '\n'.join(sorted(imports)) + after[import_end:]
    (ROOT / 'JobFamilyWaitTests.java').write_text(after)
    pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>
<groupId>org.eclipse.jdt.qa</groupId><artifactId>cleanup</artifactId><version>1</version>
<properties><maven.compiler.release>21</maven.compiler.release><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
<dependencies><dependency><groupId>org.eclipse.platform</groupId><artifactId>org.eclipse.core.jobs</artifactId><version>3.15.900</version></dependency>
<dependency><groupId>junit</groupId><artifactId>junit</artifactId><version>4.13.2</version><scope>test</scope></dependency></dependencies>
<build><plugins><plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.14.0</version></plugin>
<plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.5.3</version></plugin></plugins></build></project>'''
    for arm, text in [('before', before), ('after', after)]:
        work = ROOT / arm
        src = work / 'src/test/java/org/eclipse/jdt/core/tests/model'
        src.mkdir(parents=True)
        (src / 'JobFamilyWaitTests.java').write_text(text)
        shutil.copy2(MODEL / 'JobFamilyWait.java', src / 'JobFamilyWait.java')
        (work / 'pom.xml').write_text(pom)


def run(arm, label):
    work = ROOT / arm
    out = ROOT / label
    out.mkdir()
    with (out / 'maven.log').open('w') as log:
        result = subprocess.run(['mvn', '-B', '-ntp', '-f', str(work / 'pom.xml'), 'clean', 'test'], stdout=log, stderr=subprocess.STDOUT)
    print((out / 'maven.log').read_text(), flush=True)
    reports = work / 'target/surefire-reports'
    if reports.exists(): shutil.copytree(reports, out / 'reports')
    cases = []
    for path in (out / 'reports').glob('TEST-*.xml'):
        cases.extend(E.parse(path).getroot().iter('testcase'))
    bad = {c.get('name') for c in cases if c.find('failure') is not None}
    summary = {'arm': arm, 'label': label, 'tests': len(cases), 'failures': sorted(bad), 'exit': result.returncode}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    assert len(cases) == 11, summary
    assert not any(c.find('error') is not None or c.find('skipped') is not None for c in cases)
    expected = {'testCleanupContinuesAfterExecutorFailure', 'testCleanupContinuesAfterJobFailure', 'testCleanupRetainsMultipleFailures'} if arm == 'before' else set()
    assert bad == expected, summary
    assert (result.returncode != 0) == bool(expected), summary


if __name__ == '__main__':
    if sys.argv[1] == 'prepare': prepare()
    else: run(sys.argv[1], sys.argv[2])
