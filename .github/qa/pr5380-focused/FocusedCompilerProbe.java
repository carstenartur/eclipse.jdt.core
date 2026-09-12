package org.eclipse.jdt.core.tests.compiler.regression;

import junit.framework.Test;
import org.eclipse.jdt.core.tests.util.ProbeTiming;
import org.eclipse.jdt.internal.compiler.classfmt.ClassFileConstants;

/** Runs inherited, unmodified test bodies at exactly compliance 17. QA only. */
public class FocusedCompilerProbe extends PatternMatching16Test {
	private final String probeName;
	public FocusedCompilerProbe(String name) {
		super(name);
		this.probeName = name;
	}
	public static Test suite() {
		ProbeTiming.environment();
		RegressionTestSetup suite = new RegressionTestSetup(ClassFileConstants.JDK17);
		for (String name : new String[] { "test056", "test056a", "test056b", "test056d" }) {
			suite.addTest(new FocusedCompilerProbe(name));
		}
		return suite;
	}
	@Override
	public void runBare() throws Throwable {
		ProbeTiming.test(this.probeName);
		long[] before = ProbeTiming.start();
		try {
			if (this.complianceLevel != ClassFileConstants.JDK17) {
				throw new AssertionError("Probe must execute at compliance 17");
			}
			super.runBare();
		} finally {
			ProbeTiming.end("test", before);
			ProbeTiming.clearTest();
		}
	}
}
