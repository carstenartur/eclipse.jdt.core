package org.eclipse.jdt.core.tests.compiler.regression;

import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestResult;
import org.eclipse.jdt.core.tests.util.Pr5380Metrics;
import org.eclipse.jdt.core.tests.util.Util;
import org.eclipse.jdt.internal.compiler.classfmt.ClassFileConstants;

/** Disposable timing probe; calls the four original methods with their original assertions. */
public class Pr5380CompilerProbe extends TestCase {
	public static Test suite() {
		Pr5380Metrics.runtime(Util.getJREDirectory());
		RegressionTestSetup setup = new RegressionTestSetup(ClassFileConstants.JDK17) {
			@Override
			public void runTest(Test test, TestResult result) {
				Pr5380Metrics.Stamp start = Pr5380Metrics.start("total", ((TestCase) test).getName());
				try {
					super.runTest(test, result);
				} finally {
					Pr5380Metrics.finish(start);
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
