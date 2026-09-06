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

/**
 * Diagnostic regression tests for class-file buffers whose source attachment
 * becomes available without changing its configured path.
 */
public class SourceAttachmentBufferTests extends ModifyingResourceTests {

	public SourceAttachmentBufferTests(String name) {
		super(name);
	}

	public static Test suite() {
		return buildModelTestSuite(SourceAttachmentBufferTests.class);
	}

	/**
	 * A failed source lookup currently creates a cached NullBuffer. Verify that
	 * creating the already-configured source archive afterwards makes the source
	 * observable through the same class-file handle.
	 *
	 * This deliberately avoids sleeps and concurrent threads: the state change is
	 * source archive absent -> source archive present at the identical path.
	 */
	public void testSourceAttachmentAppearingAtSamePath() throws CoreException, IOException {
		IJavaProject javaProject= null;
		try {
			javaProject= createJavaProject("SourceAttachmentBufferTests", new String[0], //$NON-NLS-1$
					new String[] { "JCL18_LIB" }, "", JavaCore.VERSION_1_8); //$NON-NLS-1$ //$NON-NLS-2$
			IProject project= javaProject.getProject();
			String[] sources= {
					"pack/age/X.java", //$NON-NLS-1$
					"""
					package pack.age;
					public interface X {
					    String value();
					}
					""" //$NON-NLS-1$
			};

			IPath jarLocation= project.getLocation().append("lib.jar"); //$NON-NLS-1$
			IPath sourceLocation= project.getLocation().append("libsrc.zip"); //$NON-NLS-1$
			Util.createJar(sources, null, jarLocation.toOSString(), getJCLLibrary(JavaCore.VERSION_1_8), JavaCore.VERSION_1_8);
			project.refreshLocal(IResource.DEPTH_INFINITE, null);

			IPath jarPath= project.getFullPath().append("lib.jar"); //$NON-NLS-1$
			IPath sourcePath= project.getFullPath().append("libsrc.zip"); //$NON-NLS-1$
			IClasspathEntry library= JavaCore.newLibraryEntry(jarPath, sourcePath, null);
			addClasspathEntry(javaProject, library);

			IPackageFragmentRoot root= javaProject.getPackageFragmentRoot(project.getFile("lib.jar")); //$NON-NLS-1$
			IOrdinaryClassFile classFile= root.getPackageFragment("pack.age").getOrdinaryClassFile("X.class"); //$NON-NLS-1$ //$NON-NLS-2$

			assertFalse("The configured source archive must initially be absent", project.getFile("libsrc.zip").exists()); //$NON-NLS-1$ //$NON-NLS-2$
			assertNull("A class file cannot have source before the attachment exists", classFile.getSource()); //$NON-NLS-1$

			Util.createSourceZip(sources, sourceLocation.toOSString());
			project.refreshLocal(IResource.DEPTH_INFINITE, null);
			assertTrue("The source archive must now exist", project.getFile("libsrc.zip").exists()); //$NON-NLS-1$ //$NON-NLS-2$

			String source= classFile.getSource();
			assertNotNull("Source must be re-evaluated after the configured attachment appears", source); //$NON-NLS-1$
			assertTrue("Unexpected source contents", source.contains("String value()")); //$NON-NLS-1$ //$NON-NLS-2$
		} finally {
			if (javaProject != null && javaProject.exists()) {
				deleteProject(javaProject.getElementName());
			}
		}
	}
}
