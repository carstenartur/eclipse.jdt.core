package diagnostics;

import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;
import java.util.Arrays;
import org.eclipse.core.runtime.Platform;
import org.eclipse.equinox.app.IApplication;
import org.eclipse.equinox.app.IApplicationContext;
import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.IJavaProject;
import org.eclipse.jdt.core.tests.model.CompletionTests16_2;
import org.eclipse.jdt.core.tests.model.CompletionTests16_1;
import org.eclipse.jdt.core.tests.model.RunCompletionModelTests;
import org.eclipse.jdt.core.tests.model.AbstractJavaModelCompletionTests;
import org.eclipse.jdt.core.tests.junit.extension.TestCase;
import org.eclipse.jdt.internal.codeassist.CompletionEngine;
import org.eclipse.jdt.internal.core.JavaModelManager;
import org.junit.internal.runners.JUnit38ClassRunner;
import org.junit.runner.JUnitCore;
import org.junit.runner.Description;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;
import org.junit.runner.notification.RunListener;
import junit.framework.TestSuite;

/** Diagnostic runner. Every process executes each test scenario at most once. */
public class ProbeApplication implements IApplication {
    @Override
    public Object start(IApplicationContext context) throws Exception {
        System.out.println("RUNTIME java=" + System.getProperty("java.version") + " core=" + Platform.getBundle("org.eclipse.jdt.core").getVersion());
        Platform.getBundle("org.eclipse.jdt.core.tests.model").start();
        List<String> failed = new ArrayList<>();
        String mode=System.getProperty("probe.mode", "normal");
        TestCase.TESTS_NAMES=null;
        TestCase.TESTS_PREFIX=null;
        TestCase.TESTS_NUMBERS=null;
        TestCase.TESTS_RANGE=null;
        if (mode.equals("chain")) {
            List<Class<?>> classes=new ArrayList<>();
            for (Class<?> c:RunCompletionModelTests.getTestClasses()) {
                classes.add(c);
                if (c==CompletionTests16_2.class) break;
            }
            AbstractJavaModelCompletionTests.COMPLETION_SUITES = new ArrayList<>(classes);
            TestSuite suite=new TestSuite("Original completion suites through CompletionTests16_2");
            for (Class<?> c:classes) suite.addTest((junit.framework.Test)c.getDeclaredMethod("suite").invoke(null));
            run(mode,suite,failed);
        } else {
            if (mode.equals("predecessor")) {
                AbstractJavaModelCompletionTests.COMPLETION_SUITES = new ArrayList<>(List.of(CompletionTests16_1.class, CompletionTests16_2.class));
                run("predecessor", CompletionTests16_1.suite(), failed);
            }
            TestCase.TESTS_NAMES = mode.equals("full") ? null : new String[] {"test001", "test002"};
            run(mode, CompletionTests16_2.suite(), failed);
        }
        System.out.printf("PROBE_RESULT mode=%s failures=%d%n",mode,failed.size());
        return Integer.valueOf(failed.isEmpty()?0:1);
    }
    private static void run(String label, junit.framework.Test suite, List<String> failed) {
        System.out.println("PROBE_START " + label + " tests=" + suite.countTestCases());
        JUnitCore runner=new JUnitCore();
        runner.addListener(new RunListener() {
            private boolean disabled;
            @Override public void testStarted(Description d) throws Exception {
                boolean target=CompletionTests16_2.class.getName().equals(d.getClassName()) && "test002".equals(d.getMethodName());
                CompletionEngine.DEBUG=target;
                if (target) {
                    IJavaProject p=JavaModelManager.getJavaModelManager().getJavaModel().getJavaProject("Completion");
                    System.out.println("PROBE_GLOBAL_OPTIONS " + new TreeMap<>(JavaCore.getOptions()));
                    System.out.println("PROBE_PROJECT_OPTIONS " + new TreeMap<>(p.getOptions(true)));
                    System.out.println("PROBE_RESOLVED_CLASSPATH " + Arrays.toString(p.getResolvedClasspath(true)));
                    System.out.println("PROBE_PENDING_INDEX_JOBS " + JavaModelManager.getIndexManager().awaitingJobsCount());
                    if (Boolean.getBoolean("probe.disableIndex")) {
                        JavaModelManager.getIndexManager().disable();
                        this.disabled=true;
                        System.out.println("PROBE_INDEX_DISABLED");
                    }
                }
            }
            @Override public void testFinished(Description d) throws Exception {
                if (this.disabled) {
                    JavaModelManager.getIndexManager().enable();
                    this.disabled=false;
                }
            }
        });
        Result result=runner.run(new JUnit38ClassRunner(suite));
        for (Failure failure:result.getFailures()) {
            failed.add(failure.getTestHeader());
            System.out.println("PROBE_FAILURE " + label + " " + failure.getTestHeader());
            System.out.println(failure.getTrace());
        }
        System.out.printf("PROBE_LAYER label=%s tests=%d failures=%d ignored=%d%n",label,result.getRunCount(),result.getFailureCount(),result.getIgnoreCount());
    }
    @Override public void stop() {}
}
