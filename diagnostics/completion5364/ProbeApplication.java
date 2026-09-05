package diagnostics;

import java.util.ArrayList;
import java.util.List;
import org.eclipse.core.runtime.Platform;
import org.eclipse.equinox.app.IApplication;
import org.eclipse.equinox.app.IApplicationContext;
import org.eclipse.jdt.core.tests.model.CompletionTests16_2;
import org.eclipse.jdt.core.tests.model.CompletionTests16_1;
import org.eclipse.jdt.core.tests.model.AbstractJavaModelCompletionTests;
import org.eclipse.jdt.core.tests.junit.extension.TestCase;
import org.eclipse.jdt.internal.codeassist.CompletionEngine;
import org.eclipse.jdt.internal.core.JavaModelManager;
import org.junit.internal.runners.JUnit38ClassRunner;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;

/** Diagnostic runner only. It does not alter test inputs or expectations. */
public class ProbeApplication implements IApplication {
    @Override
    public Object start(IApplicationContext context) throws Exception {
        System.out.println("RUNTIME java=" + System.getProperty("java.version") + " core=" + Platform.getBundle("org.eclipse.jdt.core").getVersion());
        Platform.getBundle("org.eclipse.jdt.core.tests.model").start();
        List<String> failed = new ArrayList<>();
        String mode=System.getProperty("probe.mode", "normal");
        int repeats=Integer.getInteger("probe.repeats", 8);
        CompletionEngine.DEBUG = Boolean.getBoolean("probe.debug");
        for (int i=0; i<repeats; i++) {
            if (mode.equals("predecessor")) {
                AbstractJavaModelCompletionTests.COMPLETION_SUITES = new ArrayList<>(List.of(CompletionTests16_1.class, CompletionTests16_2.class));
                TestCase.TESTS_NAMES=null;
                run("predecessor-"+i, CompletionTests16_1.suite(), failed);
            }
            TestCase.TESTS_NAMES = mode.equals("full") ? null : new String[] {"test001", "test002"};
            TestCase.TESTS_PREFIX=null;
            TestCase.TESTS_NUMBERS=null;
            TestCase.TESTS_RANGE=null;
            run(mode+"-"+i, CompletionTests16_2.suite(), failed);
        }
        System.out.printf("PROBE_RESULT mode=%s repetitions=%d failures=%d%n",mode,repeats,failed.size());
        return Integer.valueOf(failed.isEmpty()?0:1);
    }
    private static void run(String label, junit.framework.Test suite, List<String> failed) {
        System.out.println("PROBE_START " + label + " tests=" + suite.countTestCases());
        Result result=new JUnitCore().run(new JUnit38ClassRunner(suite));
        for (Failure failure:result.getFailures()) {
            failed.add(failure.getTestHeader());
            System.out.println("PROBE_FAILURE " + label + " " + failure.getTestHeader());
            System.out.println(failure.getTrace());
        }
        System.out.printf("PROBE_LAYER label=%s tests=%d failures=%d ignored=%d%n",label,result.getRunCount(),result.getFailureCount(),result.getIgnoreCount());
    }
    @Override public void stop() {}
}
