package diagnostics;

import org.eclipse.equinox.app.IApplication;
import org.eclipse.equinox.app.IApplicationContext;
import org.eclipse.jdt.core.tests.model.OptionCacheTests;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;
import org.junit.internal.TextListener;

public class NativeApplication implements IApplication {
    @Override
    public Object start(IApplicationContext context) {
        JUnitCore runner = new JUnitCore();
        runner.addListener(new TextListener(System.out));
        Result result = runner.run(OptionCacheTests.class);
        for (Failure failure : result.getFailures()) {
            System.out.println("NATIVE_FAILURE " + failure.getTestHeader());
            System.out.println(failure.getTrace());
        }
        System.out.printf("NATIVE_RESULT tests=%d failures=%d ignored=%d%n",
                result.getRunCount(), result.getFailureCount(), result.getIgnoreCount());
        return result.wasSuccessful() ? EXIT_OK : Integer.valueOf(1);
    }
    @Override
    public void stop() {}
}
