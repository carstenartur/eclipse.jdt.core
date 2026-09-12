package org.eclipse.jdt.core.tests.util;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** Diagnostic only: process CPU here excludes child JVMs. */
public final class Pr5380Metrics {
	private static final Path OUTPUT = Path.of(System.getProperty("pr5380.events"));
	private static boolean runtimeReported;

	private Pr5380Metrics() {
	}

	public record Stamp(String phase, String test, long wall, long cpu) {
	}

	public static Stamp start(String phase, String test) {
		return new Stamp(phase, test, System.nanoTime(), cpu());
	}

	public static void finish(Stamp start) {
		long wall = System.nanoTime() - start.wall();
		long current = cpu();
		long cpu = current < 0 || start.cpu() < 0 ? -1 : current - start.cpu();
		write("phase\t" + start.phase() + "\t" + start.test() + "\t" + wall + "\t" + cpu);
	}

	public static synchronized void runtime(String childHome) {
		String version = System.getProperty("java.runtime.version");
		String expected = System.getProperty("pr5380.expectedRuntime");
		if (!version.equals(expected)) {
			throw new IllegalStateException("Expected " + expected + ", got " + version);
		}
		try {
			Path home = Path.of(System.getProperty("java.home")).toRealPath();
			if (!home.equals(Path.of(System.getProperty("pr5380.expectedHome")).toRealPath())
					|| !home.equals(Path.of(childHome).toRealPath())) {
				throw new IllegalStateException("Test JVM and verifier must use the selected JDK");
			}
			if (!runtimeReported) {
				write("runtime\t" + version + "\t" + System.getProperty("java.vendor") + "\t" + home
						+ "\t" + ProcessHandle.current().pid() + "\t17");
				runtimeReported = true;
			}
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
	}

	private static long cpu() {
		return ProcessHandle.current().info().totalCpuDuration().map(java.time.Duration::toNanos).orElse(-1L);
	}

	private static synchronized void write(String line) {
		try {
			Files.writeString(OUTPUT, line + "\n", StandardOpenOption.CREATE, StandardOpenOption.APPEND);
		} catch (IOException e) {
			throw new UncheckedIOException(e);
		}
	}
}
