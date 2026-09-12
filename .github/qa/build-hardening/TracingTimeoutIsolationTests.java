package org.eclipse.test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Proxy;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import org.eclipse.jdt.core.tests.RunAllJdtModelTestsTracing;
import org.eclipse.test.TracingSuite.TracingOptions;
import org.junit.internal.builders.AllDefaultPossibilitiesBuilder;
import org.junit.runner.Description;

import junit.framework.TestCase;

/** QA-only fault injection against the unmodified Platform TracingSuite. */
public class TracingTimeoutIsolationTests extends TestCase {
	public void testTimeoutKeepsTimerUsableWithoutDisplay() throws Exception {
		TracingSuite suite = new TracingSuite(RunAllJdtModelTestsTracing.class,
				new AllDefaultPossibilitiesBuilder(true));
		TracingOptions original = RunAllJdtModelTestsTracing.class.getAnnotation(TracingOptions.class);
		// Never attempt to terminate the test harness's main thread. All other
		// options, particularly maxScreenshotCount, come from the real entrypoint.
		TracingOptions options = (TracingOptions) Proxy.newProxyInstance(TracingOptions.class.getClassLoader(),
				new Class<?>[] { TracingOptions.class }, (proxy, method, args) -> {
					if (method.getName().equals("throwExceptionInMainThread")) {
						return false;
					}
					return method.invoke(original, args);
				});
		Field field = TracingSuite.class.getDeclaredField("fTracingOptions");
		field.setAccessible(true);
		field.set(suite, options);
		Class<?> dumpClass = Class.forName("org.eclipse.test.TracingSuite$DumpTask");
		Constructor<?> constructor = dumpClass.getDeclaredConstructor(TracingSuite.class, Description.class);
		constructor.setAccessible(true);
		TimerTask dump = (TimerTask) constructor.newInstance(suite,
				Description.createTestDescription(getClass(), "injected-timeout"));
		Timer timer = new Timer(true);
		CountDownLatch completed = new CountDownLatch(1);
		AtomicReference<Throwable> failure = new AtomicReference<>();
		try {
			timer.schedule(new TimerTask() {
				@Override
				public void run() {
					try {
						dump.run();
					} catch (RuntimeException | Error e) {
						failure.set(e);
						throw e;
					} finally {
						completed.countDown();
					}
				}
			}, 0);
			assertTrue("Timeout diagnostic did not complete", completed.await(10, TimeUnit.SECONDS));
			assertNull("The unavailable display killed the diagnostic timer: " + failure.get(), failure.get());
			CountDownLatch subsequent = new CountDownLatch(1);
			timer.schedule(new TimerTask() {
				@Override
				public void run() {
					subsequent.countDown();
				}
			}, 0);
			assertTrue("Subsequent timeout monitoring did not execute", subsequent.await(10, TimeUnit.SECONDS));
		} finally {
			timer.cancel();
		}
	}
}
