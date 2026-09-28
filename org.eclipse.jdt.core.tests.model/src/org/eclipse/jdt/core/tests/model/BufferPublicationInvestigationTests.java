/*******************************************************************************
 * Copyright (c) 2026.
 * SPDX-License-Identifier: EPL-2.0
 * Investigation only: deterministic scheduling around real JDT buffer publication.
 *******************************************************************************/
package org.eclipse.jdt.core.tests.model;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import junit.framework.Test;
import org.eclipse.core.resources.IResource;
import org.eclipse.core.resources.ResourcesPlugin;
import org.eclipse.core.runtime.jobs.Job;
import org.eclipse.jdt.core.IBuffer;
import org.eclipse.jdt.core.IJavaProject;
import org.eclipse.jdt.core.IOpenable;
import org.eclipse.jdt.core.IOrdinaryClassFile;
import org.eclipse.jdt.core.IPackageFragmentRoot;
import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.internal.core.BufferManager;

public class BufferPublicationInvestigationTests extends ModifyingResourceTests {
    private static final String SOURCE = "package publication; public class X { "
            + "public String marker() { return \"ready\"; } public static class Nested {} }";

    public BufferPublicationInvestigationTests(String name) {
        super(name);
    }

    public static Test suite() {
        return buildModelTestSuite(BufferPublicationInvestigationTests.class);
    }

    // Real BufferManager / BufferCache / Buffer are used. The only changed
    // behavior is a scheduling gate AFTER the original addBuffer has returned.
    // In particular, no buffer contents or Java model state are fabricated.
    private static final class GatedBufferManager extends BufferManager {
        final IOpenable target;
        final CountDownLatch published = new CountDownLatch(1);
        final CountDownLatch release = new CountDownLatch(1);
        final AtomicBoolean armed = new AtomicBoolean(true);
        volatile IBuffer observed;

        GatedBufferManager(IOpenable target) {
            this.target = target;
        }

        static BufferManager replaceDefault(BufferManager replacement) {
            synchronized (BufferManager.class) {
                BufferManager previous = getDefaultBufferManager();
                DEFAULT_BUFFER_MANAGER = replacement;
                return previous;
            }
        }

        @Override
        protected void addBuffer(IBuffer buffer) {
            super.addBuffer(buffer);
            if (this.target.equals(buffer.getOwner()) && this.armed.compareAndSet(true, false)) {
                this.observed = buffer;
                this.published.countDown();
                try {
                    if (!this.release.await(60, TimeUnit.SECONDS)) {
                        throw new AssertionError("Publication gate was not released");
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new AssertionError("Publisher interrupted at gate", e);
                }
            }
        }
    }

    private IJavaProject createFixture(String name) throws Exception {
        IJavaProject project = createJavaProject(name, new String[0],
                new String[] { "JCL18_LIB" }, "", JavaCore.VERSION_1_8);
        addLibrary(project, "publication.jar", "publication-src.zip",
                new String[] { "publication/X.java", SOURCE }, JavaCore.VERSION_1_8);
        Job.getJobManager().join(ResourcesPlugin.FAMILY_AUTO_BUILD, null);
        Job.getJobManager().join(ResourcesPlugin.FAMILY_MANUAL_BUILD, null);
        return project;
    }

    private IPackageFragmentRoot root(IJavaProject project) {
        return project.getPackageFragmentRoot(project.getProject().getFile("publication.jar"));
    }

    private static final class ReadResult {
        final IBuffer buffer;
        final String source;
        ReadResult(IBuffer buffer, String source) {
            this.buffer = buffer;
            this.source = source;
        }
    }

    private void checkConcurrentRead(boolean warmModel, boolean innerClass) throws Exception {
        String projectName = "BufferPublication" + (warmModel ? "Warm" : "Cold")
                + (innerClass ? "Inner" : "Outer");
        IJavaProject project = null;
        BufferManager previous = null;
        GatedBufferManager manager = null;
        ExecutorService executor = Executors.newFixedThreadPool(2, runnable -> {
            Thread worker = new Thread(runnable, "buffer-publication-probe");
            worker.setDaemon(true);
            return worker;
        });
        try {
            project = createFixture(projectName);
            IPackageFragmentRoot root = root(project);
            IOrdinaryClassFile writerFile = root.getPackageFragment("publication")
                    .getOrdinaryClassFile("X.class");
            IOrdinaryClassFile readerFile = root.getPackageFragment("publication")
                    .getOrdinaryClassFile(innerClass ? "X$Nested.class" : "X.class");
            if (warmModel) {
                writerFile.getType().getMethods();
                readerFile.getType().getMethods();
            }
            manager = new GatedBufferManager(writerFile);
            previous = GatedBufferManager.replaceDefault(manager);
            assertNull("Fixture must start without a source buffer", manager.getBuffer(writerFile));

            Future<String> writer = executor.submit(writerFile::getSource);
            assertTrue("Real source initialization did not reach publication",
                    manager.published.await(30, TimeUnit.SECONDS));
            IBuffer publishedBuffer = manager.observed;
            assertNotNull("Gate must observe a real buffer", publishedBuffer);
            boolean hadNullCharacters = publishedBuffer.getCharacters() == null;
            assertFalse("This is not a closed/stale buffer", publishedBuffer.isClosed());

            Future<ReadResult> reader = executor.submit(() ->
                    new ReadResult(readerFile.getBuffer(), readerFile.getSource()));
            ReadResult result;
            try {
                result = reader.get(15, TimeUnit.SECONDS);
            } catch (Exception e) {
                Thread.getAllStackTraces().forEach((thread, stack) -> {
                    System.out.println("PROBE_THREAD " + thread.getName() + " " + thread.getState());
                    for (StackTraceElement frame : stack) {
                        System.out.println("  " + frame);
                    }
                });
                throw e;
            }
            assertSame("Reader must reach the genuinely published buffer", publishedBuffer, result.buffer);
            assertFalse("Reader must not have closed the buffer", publishedBuffer.isClosed());
            manager.release.countDown();
            String completedSource = writer.get(30, TimeUnit.SECONDS);
            assertNotNull("Publisher must complete with source", completedSource);
            assertTrue("Fixture source must be the expected source", completedSource.contains("marker()"));
            assertEquals("Source must recover after initialization", completedSource, readerFile.getSource());

            System.out.println("PUBLICATION_OBSERVATION test=" + getName()
                    + " nullCharactersAtPublication=" + hadNullCharacters
                    + " concurrentSourceNull=" + (result.source == null)
                    + " sameBuffer=true closed=false recovered=true");
            assertNotNull("BUFFER_PUBLICATION: concurrent getSource() returned null before initialization completed",
                    result.source);
            assertEquals("Concurrent reader must receive the complete source", completedSource, result.source);
        } finally {
            if (manager != null) {
                manager.release.countDown();
            }
            executor.shutdownNow();
            boolean stopped = executor.awaitTermination(30, TimeUnit.SECONDS);
            try {
                if (project != null) {
                    deleteProject(project);
                }
            } finally {
                if (previous != null) {
                    GatedBufferManager.replaceDefault(previous);
                }
            }
            assertTrue("Probe workers must terminate before teardown completes", stopped);
        }
    }

    public void testConcurrentTopLevelReadWithWarmModel() throws Exception {
        checkConcurrentRead(true, false);
    }

    public void testConcurrentTopLevelReadWithColdModel() throws Exception {
        checkConcurrentRead(false, false);
    }

    public void testConcurrentInnerClassRead() throws Exception {
        checkConcurrentRead(true, true);
    }

    public void testSequentialReadControl() throws Exception {
        IJavaProject project = null;
        try {
            project = createFixture("BufferPublicationSequential");
            IOrdinaryClassFile file = root(project).getPackageFragment("publication")
                    .getOrdinaryClassFile("X.class");
            String source = file.getSource();
            assertNotNull(source);
            assertTrue(source.contains("marker()"));
            assertEquals(source, file.getSource());
        } finally {
            if (project != null) {
                deleteProject(project);
            }
        }
    }

    public void testMissingSourceControl() throws Exception {
        IJavaProject project = null;
        try {
            project = createJavaProject("BufferPublicationMissingSource", new String[0],
                    new String[] { "JCL18_LIB" }, "", JavaCore.VERSION_1_8);
            String jarPath = project.getProject().getLocation().append("publication.jar").toOSString();
            org.eclipse.jdt.core.tests.util.Util.createJar(
                    new String[] { "publication/X.java", SOURCE }, null, jarPath,
                    getJCLLibrary(JavaCore.VERSION_1_8), JavaCore.VERSION_1_8);
            project.getProject().refreshLocal(IResource.DEPTH_INFINITE, null);
            addLibraryEntry(project, project.getPath().append("publication.jar"), true);
            Job.getJobManager().join(ResourcesPlugin.FAMILY_AUTO_BUILD, null);
            IPackageFragmentRoot root = root(project);
            assertNull("Fixture must have no source attachment", root.getSourceAttachmentPath());
            IOrdinaryClassFile file = root.getPackageFragment("publication").getOrdinaryClassFile("X.class");
            assertNull("No attachment must still mean no source", file.getSource());
            assertNull("Repeated access without attachment must remain valid", file.getSource());
        } finally {
            if (project != null) {
                deleteProject(project);
            }
        }
    }
}
