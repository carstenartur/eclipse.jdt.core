/*******************************************************************************
 * Copyright (c) 2026 Contributors to the Eclipse Foundation.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License 2.0 which accompanies this distribution,
 * and is available at https://www.eclipse.org/legal/epl-2.0/
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
package org.eclipse.jdt.core.tests.model;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import junit.framework.Test;

import org.eclipse.jdt.core.IBuffer;
import org.eclipse.jdt.core.IJavaProject;
import org.eclipse.jdt.core.IOrdinaryClassFile;
import org.eclipse.jdt.core.IPackageFragmentRoot;
import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.internal.core.BufferManager;
import org.eclipse.jdt.internal.core.ClassFile;
import org.eclipse.jdt.internal.core.PackageFragment;

/**
 * Diagnostic tests: no production methods are copied, mocked or bypassed.
 * The only seam pauses after the real BufferManager.addBuffer() has returned.
 */
public class BufferPublicationTests extends ModifyingResourceTests {
	private static final String SOURCE = "package pack.age;\npublic interface X { String value(); }\n";

	public BufferPublicationTests(String name) {
		super(name);
	}

	public static Test suite() {
		return buildModelTestSuite(BufferPublicationTests.class);
	}

	private static final class PausingBufferManager extends BufferManager {
		final CountDownLatch published = new CountDownLatch(1);
		final CountDownLatch resume = new CountDownLatch(1);
		volatile Thread publishingThread;
		volatile IBuffer publishedBuffer;

		@Override
		protected void addBuffer(IBuffer buffer) {
			super.addBuffer(buffer);
			if (Thread.currentThread() != this.publishingThread) {
				return;
			}
			this.publishedBuffer = buffer;
			this.published.countDown();
			try {
				if (!this.resume.await(30, TimeUnit.SECONDS)) {
					throw new AssertionError("Diagnostic publisher was not released");
				}
			} catch (InterruptedException e) {
				Thread.currentThread().interrupt();
				throw new AssertionError("Diagnostic publisher interrupted", e);
			}
		}
	}

	private static final class PausingClassFile extends ClassFile {
		private final PausingBufferManager manager;

		PausingClassFile(PackageFragment parent, PausingBufferManager manager) {
			super(parent, "X"); // internal ClassFile names omit the .class suffix
			this.manager = manager;
		}

		@Override
		protected BufferManager getBufferManager() {
			return this.manager;
		}
	}

	public void testConcurrentSourceDuringBufferPublication() throws Exception {
		for (int iteration = 0; iteration < 10; iteration++) {
			checkConcurrentSource(iteration);
		}
	}

	private void checkConcurrentSource(int iteration) throws Exception {
		IJavaProject project = null;
		PausingBufferManager manager = new PausingBufferManager();
		IOrdinaryClassFile classFile = null;
		Thread publisherThread = null;
		Thread readerThread = null;
		try {
			project = createJavaProject("BufferPublication" + iteration, new String[0],
					new String[] { "JCL18_LIB" }, "", JavaCore.VERSION_1_8);
			addLibrary(project, "lib.jar", "src.zip",
					new String[] { "pack/age/X.java", SOURCE }, JavaCore.VERSION_1_8);
			IPackageFragmentRoot root = project.getPackageFragmentRoot(project.getProject().getFile("lib.jar"));
			classFile = new PausingClassFile((PackageFragment) root.getPackageFragment("pack.age"), manager);
			// Warm the real Java-model/binary state, but not the source buffer.
			classFile.open(null);
			assertNull("Source buffer must not have been opened yet", manager.getBuffer(classFile));
			IOrdinaryClassFile handle = classFile;
			FutureTask<String> publisher = new FutureTask<>(handle::getSource);
			publisherThread = new Thread(publisher, "buffer-source-publisher");
			publisherThread.setDaemon(true);
			manager.publishingThread = publisherThread;
			publisherThread.start();
			assertTrue("Real ClassFile.mapSource did not reach buffer publication",
					manager.published.await(20, TimeUnit.SECONDS));
			IBuffer published = manager.publishedBuffer;
			assertNotNull(published);
			assertSame("The published buffer must be in the real cache", published, manager.getBuffer(handle));
			boolean closedAtPublication = published.isClosed();
			boolean nullAtPublication = published.getCharacters() == null;
			FutureTask<String> reader = new FutureTask<>(handle::getSource);
			readerThread = new Thread(reader, "buffer-source-reader");
			readerThread.setDaemon(true);
			readerThread.start();
			String concurrentSource = null;
			boolean readerWaited = false;
			try {
				concurrentSource = reader.get(5, TimeUnit.SECONDS);
			} catch (TimeoutException e) {
				// A production lock that waits for initialization is also correct.
				readerWaited = true;
			} finally {
				manager.resume.countDown();
			}
			String publisherSource = publisher.get(20, TimeUnit.SECONDS);
			if (readerWaited) {
				concurrentSource = reader.get(20, TimeUnit.SECONDS);
			}
			String afterSource = handle.getSource();
			System.out.println("BUFFER_PUBLICATION iteration=" + iteration
					+ " closedAtPublication=" + closedAtPublication
					+ " nullAtPublication=" + nullAtPublication
					+ " readerWaited=" + readerWaited
					+ " concurrentSourceNull=" + (concurrentSource == null)
					+ " publisherSourcePresent=" + SOURCE.equals(publisherSource)
					+ " afterSourcePresent=" + SOURCE.equals(afterSource));
			assertEquals("Publisher must recover after release", SOURCE, publisherSource);
			assertEquals("Source must be intact after initialization", SOURCE, afterSource);
			assertFalse("A newly published source buffer must not be closed", closedAtPublication);
			assertEquals("Concurrent getSource must not expose an uninitialized source buffer", SOURCE, concurrentSource);
		} finally {
			manager.resume.countDown();
			if (publisherThread != null) {
				publisherThread.join(25000);
				assertFalse("Publisher did not terminate", publisherThread.isAlive());
			}
			if (readerThread != null) {
				readerThread.join(25000);
				assertFalse("Reader did not terminate", readerThread.isAlive());
			}
			if (classFile != null) {
				classFile.close();
			}
			if (project != null) {
				deleteProject(project);
			}
		}
	}

	/** Control corresponding to the old PRs: no concurrent operations. */
	public void testSequentialJarRecreation() throws Exception {
		IJavaProject project = null;
		try {
			project = createJavaProject("SequentialRecreation", new String[0],
					new String[] { "JCL18_LIB" }, "", JavaCore.VERSION_1_8);
			addLibrary(project, "lib.jar", "src.zip",
					new String[] { "pack/age/X.java", SOURCE }, JavaCore.VERSION_1_8);
			IPackageFragmentRoot root = project.getPackageFragmentRoot(project.getProject().getFile("lib.jar"));
			assertEquals(SOURCE, root.getPackageFragment("pack.age").getOrdinaryClassFile("X.class").getSource());
			removeLibrary(project, "lib.jar", "src.zip");
			String replacement = SOURCE.replace("value()", "replacement()");
			addLibrary(project, "lib.jar", "src.zip",
					new String[] { "pack/age/X.java", replacement }, JavaCore.VERSION_1_8);
			root = project.getPackageFragmentRoot(project.getProject().getFile("lib.jar"));
			assertEquals(replacement, root.getPackageFragment("pack.age").getOrdinaryClassFile("X.class").getSource());
			System.out.println("SEQUENTIAL_RECREATION sourceUpdated=true");
		} finally {
			if (project != null) {
				deleteProject(project);
			}
		}
	}
}
