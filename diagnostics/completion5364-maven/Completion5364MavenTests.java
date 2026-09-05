/*******************************************************************************
 * Copyright (c) 2026 Contributors to the Eclipse Foundation.
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
package org.eclipse.jdt.core.tests.model;

import java.util.ArrayList;
import java.util.List;
import junit.framework.AssertionFailedError;
import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestListener;
import junit.framework.TestResult;
import junit.framework.TestSuite;
import org.eclipse.jdt.internal.codeassist.Completion5364Trace;

/** Selects original suites; no completion inputs, assertions or setup are edited. */
@SuppressWarnings({"rawtypes", "unchecked", "nls"})
public class Completion5364MavenTests extends TestCase {
    public static Test suite() throws Exception {
        String scenario = System.getProperty("completion5364.scenario", "pair");
        TestSuite selected = new TestSuite("Completion5364 " + scenario);
        org.eclipse.jdt.core.tests.junit.extension.TestCase.TESTS_NAMES = null;
        if ("chain".equals(scenario)) {
            List<Class> classes = new ArrayList<>();
            for (Object next : RunCompletionModelTests.COMPLETION_SUITES) {
                classes.add((Class) next);
                if (next == CompletionTests16_2.class) break;
            }
            if (classes.get(classes.size() - 1) != CompletionTests16_2.class) throw new IllegalStateException("Target absent");
            AbstractJavaModelCompletionTests.COMPLETION_SUITES = new ArrayList(classes);
            for (Class type : classes) selected.addTest((Test) type.getMethod("suite").invoke(null));
        } else if ("model".equals(scenario)) {
            selected.addTest(AllJavaModelTests.suite());
        } else {
            try {
                if ("pair".equals(scenario)) {
                    org.eclipse.jdt.core.tests.junit.extension.TestCase.TESTS_NAMES = new String[] { "test001", "test002" };
                } else if (!"class".equals(scenario)) throw new IllegalArgumentException(scenario);
                selected.addTest(CompletionTests16_2.suite());
            } finally {
                org.eclipse.jdt.core.tests.junit.extension.TestCase.TESTS_NAMES = null;
            }
        }
        TestSuite wrapper = new TestSuite("Completion5364 evidence") {
            @Override public void run(TestResult result) {
                int beforeCount = result.runCount(), beforeFailures = result.failureCount(), beforeErrors = result.errorCount();
                int[] targetCount = {0};
                TestListener listener = new TestListener() {
                    private boolean target;
                    @Override public void startTest(Test test) {
                        target = test instanceof TestCase tc && (
                            tc.getClass() == CompletionTests16_2.class && "test002".equals(tc.getName())
                            || tc.getClass() == CompletionTests16.class && "testBug564828_2".equals(tc.getName()));
                        if (target) {
                            if (test instanceof CompletionTests16_2) targetCount[0]++;
                            String id = test.getClass().getName() + "." + ((TestCase) test).getName();
                            System.out.println("COMPLETION5364_TARGET_START " + id);
                            Completion5364Trace.begin(id);
                        }
                    }
                    @Override public void endTest(Test test) {
                        if (target) {
                            Completion5364Trace.end();
                            System.out.println("COMPLETION5364_TARGET_END " + test);
                            target = false;
                        }
                    }
                    @Override public void addError(Test test, Throwable error) {
                        System.out.println("COMPLETION5364_ERROR " + test + " " + error);
                    }
                    @Override public void addFailure(Test test, AssertionFailedError error) {
                        System.out.println("COMPLETION5364_FAILURE " + test + " " + error);
                    }
                };
                System.out.println("COMPLETION5364_RUNTIME java=" + System.getProperty("java.version")
                        + " home=" + System.getProperty("java.home") + " scenario=" + scenario
                        + " trace=" + System.getProperty("completion5364.trace")
                        + " expected=" + countTestCases());
                result.addListener(listener);
                try { super.run(result); }
                finally {
                    result.removeListener(listener);
                    System.out.println("COMPLETION5364_RESULT scenario=" + scenario
                            + " tests=" + (result.runCount() - beforeCount)
                            + " failures=" + (result.failureCount() - beforeFailures)
                            + " errors=" + (result.errorCount() - beforeErrors) + " target=" + targetCount[0]);
                }
            }
        };
        wrapper.addTest(selected);
        return wrapper;
    }
}
