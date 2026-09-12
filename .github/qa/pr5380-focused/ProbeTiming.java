package org.eclipse.jdt.core.tests.util;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import org.eclipse.jdt.core.tests.runtime.LocalVMLauncher;
import org.eclipse.jdt.core.tests.runtime.LocalVirtualMachine;
import org.eclipse.jdt.core.tests.runtime.TargetException;

/** Disposable QA instrumentation; not a proposed production change. */
public final class ProbeTiming {
	private static final ThreadMXBean THREADS = ManagementFactory.getThreadMXBean();
	private static final ThreadLocal<String> TEST = new ThreadLocal<>();
	private static Path directory() {
		return Path.of(System.getProperty("qa.probe.dir", "target/qa-probe"));
	}
	public static synchronized void metadata(String key, String value) {
		append("runtime.tsv", key + "\t" + value.replace('\n', ' ').replace('\t', ' '));
	}
	private static synchronized void append(String file, String value) {
		try {
			Files.createDirectories(directory());
			Files.writeString(directory().resolve(file), value + "\n",
					StandardOpenOption.CREATE, StandardOpenOption.APPEND);
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
	}
	public static void environment() {
		for (String key : new String[] { "java.runtime.version", "java.vm.version", "java.vendor", "java.home", "compliance" }) {
			metadata(key, System.getProperty(key, "<missing>"));
		}
		metadata("pid", Long.toString(ProcessHandle.current().pid()));
		metadata("jvm.args", ManagementFactory.getRuntimeMXBean().getInputArguments().toString());
		metadata("original.test.class", "org.eclipse.jdt.core.tests.compiler.regression.PatternMatching16Test");
		String expected = System.getProperty("qa.expected.runtime");
		if (expected != null && !expected.equals(System.getProperty("java.runtime.version"))) {
			throw new AssertionError("Unexpected test JVM: " + System.getProperty("java.runtime.version") + "; expected " + expected);
		}
		if (THREADS.isThreadCpuTimeSupported() && !THREADS.isThreadCpuTimeEnabled()) {
			THREADS.setThreadCpuTimeEnabled(true);
		}
	}
	public static void test(String name) {
		TEST.set(name);
	}
	public static void clearTest() {
		TEST.remove();
	}
	public static long[] start() {
		long process = ProcessHandle.current().info().totalCpuDuration().map(d -> d.toNanos()).orElse(-1L);
		return new long[] { System.nanoTime(),
				THREADS.isCurrentThreadCpuTimeSupported() ? THREADS.getCurrentThreadCpuTime() : -1,
				THREADS.isCurrentThreadCpuTimeSupported() ? THREADS.getCurrentThreadUserTime() : -1, process };
	}
	public static void end(String phase, long[] before) {
		long[] after = start();
		String name = TEST.get();
		if (name == null) {
			name = "<suite>";
		}
		StringBuilder row = new StringBuilder(name).append('\t').append(phase);
		for (int i = 0; i < before.length; i++) {
			row.append('\t').append(before[i] < 0 || after[i] < 0 ? -1 : after[i] - before[i]);
		}
		append("timings.tsv", row.toString());
	}
	public static LocalVirtualMachine launch(LocalVMLauncher launcher) throws TargetException {
		long[] before = start();
		try {
			return launcher.launch();
		} finally {
			end("vm-launch", before);
		}
	}
	public static void childRuntime(String home, String[] arguments) {
		String actual = Path.of(home).toAbsolutePath().normalize().toString();
		String own = Path.of(System.getProperty("java.home")).toAbsolutePath().normalize().toString();
		metadata("child.java.home", actual);
		metadata("child.vm.args", Arrays.toString(arguments));
		if (!actual.equals(own)) {
			throw new AssertionError("Child JVM differs from measured test JVM: " + actual + " != " + own);
		}
	}
}
