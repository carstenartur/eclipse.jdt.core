/*******************************************************************************
 * Copyright (c) 2026 Carsten Hammer and others.
 *
 * This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License 2.0
 * which accompanies this distribution, and is available at
 * https://www.eclipse.org/legal/epl-2.0/
 *
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
package org.eclipse.jdt.core.tests.model;

import java.io.IOException;

import junit.framework.Test;

import org.eclipse.core.resources.IProject;
import org.eclipse.core.resources.IResource;
import org.eclipse.core.runtime.CoreException;
import org.eclipse.core.runtime.IPath;

import org.eclipse.jdt.core.IClasspathEntry;
import org.eclipse.jdt.core.IJavaProject;
import org.eclipse.jdt.core.IOrdinaryClassFile;
import org.eclipse.jdt.core.IPackageFragmentRoot;
import org.eclipse.jdt.core.JavaCore;

import org.eclipse.jdt.core.tests.util.Util;

import org.eclipse.jdt.internal.core.JavaModelManager;

/**
 * Diagnostic regression tests for class-file source buffers after an initially
 * unsuccessful source lookup.
 */
public class SourceAttachmentBufferTests extends ModifyingResourceTests {

	private static final String PROJECT_NAME= "SourceAttachmentBufferTests"; //$NON-NLS-1$
	private static final String[] SOURCES= {
			"pack/age/X.java", //$NON-NLS-1$
			"""
			package pack.age;
			public interface X {
			    String value();
			}
			""" //$NON-NLS-1$
	};

	public SourceAttachmentBufferTests(String name) {
		super(name);
	}

	public static Test suite() {
		return buildModelTestSuite(SourceAttachmentBufferTests.class);
	}

	/**
	 * Verify the normal resource-delta path: if the configured source archive did
	 * not exist during the first lookup but is then created, the source becomes
	 * visible through the same class-file handle.
	 */
	public void testSourceAttachmentAppearingAtSamePath() throws CoreException, IOException {
		IJavaProject javaProject= null;
		try {
			javaProject= createProjectWithLibrary(false);
			IProject project= javaProject.getProject();
			IOrdinaryClassFile classFile= classFile(javaProject);

			assertFalse("The configured source archive must initially be absent", project.getFile("libsrc.zip").exists()); //$NON-NLS-1$ //$NON-NLS-2$
			assertNull("A class file cannot have source before the attachment exists", classFile.getSource()); //$NON-NLS-1$

			Util.createSourceZip(SOURCES, project.getLocation().append("libsrc.zip").toOSString()); //$NON-NLS-1$
			project.refreshLocal(IResource.DEPTH_INFINITE, null);
			assertTrue("The source archive must now exist", project.getFile("libsrc.zip").exists()); //$NON-NLS-1$ //$NON-NLS-2$

			assertExpectedSource(classFile.getSource());
		} finally {
			delete(javaProject);
		}
	}

	/**
	 * Model a transient source-archive read failure without a classpath or resource
	 * change afterwards. ClassFile.openBuffer() represents an unsuccessful source
	 * mapping as a cached NullBuffer. Once the transient failure is gone, a later
	 * getSource() must not be permanently pinned to that no-source result.
	 */
	public void testTransientSourceReadFailureDoesNotBecomePermanent() throws CoreException, IOException {
		IJavaProject javaProject= null;
		try {
			javaProject= createProjectWithLibrary(true);
			IOrdinaryClassFile classFile= classFile(javaProject);
			// Open binary metadata before injecting the source-read failure, so the
			// failure is specific to source lookup rather than class-file discovery.
			assertTrue(classFile.getType().getFlags() >= 0);

			JavaModelManager.throwIoExceptionsInGetZipFile= true;
			try {
				assertNull("The injected transient archive failure must make this source lookup fail", classFile.getSource()); //$NON-NLS-1$
			} finally {
				JavaModelManager.throwIoExceptionsInGetZipFile= false;
			}

			assertExpectedSource(classFile.getSource());
		} finally {
			JavaModelManager.throwIoExceptionsInGetZipFile= false;
			delete(javaProject);
		}
	}

	private IJavaProject createProjectWithLibrary(boolean createSource) throws CoreException, IOException {
		IJavaProject javaProject= createJavaProject(PROJECT_NAME, new String[0], new String[] { "JCL18_LIB" }, "", JavaCore.VERSION_1_8); //$NON-NLS-1$ //$NON-NLS-2$
		IProject project= javaProject.getProject();
		IPath jarLocation= project.getLocation().append("lib.jar"); //$NON-NLS-1$
		Util.createJar(SOURCES, null, jarLocation.toOSString(), getJCLLibrary(JavaCore.VERSION_1_8), JavaCore.VERSION_1_8);
		if (createSource) {
			Util.createSourceZip(SOURCES, project.getLocation().append("libsrc.zip").toOSString()); //$NON-NLS-1$
		}
		project.refreshLocal(IResource.DEPTH_INFINITE, null);

		IPath jarPath= project.getFullPath().append("lib.jar"); //$NON-NLS-1$
		IPath sourcePath= project.getFullPath().append("libsrc.zip"); //$NON-NLS-1$
		IClasspathEntry library= JavaCore.newLibraryEntry(jarPath, sourcePath, null);
		addClasspathEntry(javaProject, library);
		return javaProject;
	}

	private static IOrdinaryClassFile classFile(IJavaProject javaProject) {
		IProject project= javaProject.getProject();
		IPackageFragmentRoot root= javaProject.getPackageFragmentRoot(project.getFile("lib.jar")); //$NON-NLS-1$
		return root.getPackageFragment("pack.age").getOrdinaryClassFile("X.class"); //$NON-NLS-1$ //$NON-NLS-2$
	}

	private static void assertExpectedSource(String source) {
		assertNotNull("Source must be available after the transient condition is gone", source); //$NON-NLS-1$
		assertTrue("Unexpected source contents", source.contains("String value()")); //$NON-NLS-1$ //$NON-NLS-2$
	}

	private void delete(IJavaProject javaProject) throws CoreException {
		if (javaProject != null && javaProject.exists()) {
			deleteProject(javaProject.getElementName());
		}
	}
}
