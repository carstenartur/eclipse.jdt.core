package org.eclipse.jdt.core.tests.compiler.regression;

import java.util.IdentityHashMap;
import java.util.Map;
import junit.framework.AssertionFailedError;
import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestListener;
import junit.framework.TestResult;
import org.eclipse.jdt.core.tests.util.Pr5380Metrics;
import org.eclipse.jdt.core.tests.util.Util;
import org.eclipse.jdt.internal.compiler.classfmt.ClassFileConstants;

/** Disposable timing probe; preserves the original methods, instances and assertions. */
public class Pr5380CompilerProbe extends TestCase {
	public static Test suite() {
		Pr5380Metrics.runtime(Util.getJREDirectory());
		RegressionTestSetup setup = new RegressionTestSetup(ClassFileConstants.JDK17) {
			@Override
			public void run(TestResult result) {
				Map<Test, Pr5380Metrics.Stamp> starts = new IdentityHashMap<>();
				TestListener listener = new TestListener() {
					@Override
					public void startTest(Test test) {
						starts.put(test, Pr5380Metrics.start("total", ((TestCase) test).getName()));
					}

					@Override
					public void endTest(Test test) {
						Pr5380Metrics.Stamp start = starts.remove(test);
						if (start == null) {
							throw new IllegalStateException("Missing test-start event: " + test);
						}
						Pr5380Metrics.finish(start);
					}

					@Override
					public void addError(Test test, Throwable error) {
						// The existing TestResult retains and reports the original error.
					}

					@Override
					public void addFailure(Test test, AssertionFailedError failure) {
						// The existing TestResult retains and reports the original assertion.
					}
				};
				result.addListener(listener);
				try {
					super.run(result);
				} finally {
					result.removeListener(listener);
				}
			}
		};
		for (String name : new String[] { "test056", "test056a", "test056b", "test056d" }) {
			setup.addTest(new PatternMatching16Test(name));
		}
		if (setup.countTestCases() != 4) {
			throw new IllegalStateException("Expected exactly four tests");
		}
		return setup;
	}
}
