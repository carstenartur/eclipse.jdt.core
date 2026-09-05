/*******************************************************************************
 * Copyright (c) 2026 Contributors to the Eclipse Foundation.
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
package org.eclipse.jdt.internal.core.search;

import java.util.Arrays;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import org.eclipse.core.runtime.Path;
import org.eclipse.jdt.core.search.SearchPattern;
import org.eclipse.jdt.internal.codeassist.Completion5364Trace;
import org.eclipse.jdt.internal.core.JavaModelManager;
import org.eclipse.jdt.internal.core.index.Index;
import org.eclipse.jdt.internal.core.search.matching.TypeDeclarationPattern;

/** Controlled ordering only; actual removal is performed by the real IndexManager. */
@SuppressWarnings("nls")
public final class IndexRemovalProbe {
    private static final AtomicBoolean USED = new AtomicBoolean();
    private IndexRemovalProbe() {}

    public static void afterAcquire(SearchPattern pattern, Index[] indexes) {
        if (!Boolean.getBoolean("completion5364.deleteIndex") || !Completion5364Trace.active()
                || !(pattern instanceof TypeDeclarationPattern type)
                || !Arrays.equals(type.simpleName, "enu".toCharArray())) return;
        Index target = null;
        for (Index index : indexes) {
            if (index != null && index.containerPath.endsWith("jclMin14.jar")) {
                if (target != null) throw new AssertionError("Ambiguous test-library index");
                target = index;
            }
        }
        if (target == null) throw new AssertionError("The real test-library index was not acquired");
        if (!USED.compareAndSet(false, true)) return;
        Index selected = target;
        if (selected.monitor == null) throw new AssertionError("Index already invalid before intervention");
        System.out.println("INDEX_RACE_ACQUIRED " + selected.containerPath);
        ExecutorService writer = Executors.newSingleThreadExecutor(r -> {
            Thread thread = new Thread(r, "completion5364-real-index-remover");
            thread.setDaemon(true);
            return thread;
        });
        try {
            writer.submit(() -> JavaModelManager.getIndexManager().removeIndex(new Path(selected.containerPath)))
                    .get(30, TimeUnit.SECONDS);
            if (selected.monitor != null) throw new AssertionError("Real removal did not invalidate acquired index");
            System.out.println("INDEX_RACE_REMOVED " + selected.containerPath + " oldMonitorNull=true");
        } catch (Exception ex) {
            throw new AssertionError("Could not complete controlled real-index removal", ex);
        } finally {
            writer.shutdownNow();
            try {
                if (!writer.awaitTermination(30, TimeUnit.SECONDS)) throw new AssertionError("Index writer leaked");
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                throw new AssertionError(ex);
            }
        }
    }
}
