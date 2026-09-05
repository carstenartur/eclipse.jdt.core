/*******************************************************************************
 * Copyright (c) 2026 Contributors to the Eclipse Foundation.
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
package org.eclipse.jdt.internal.codeassist;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.eclipse.jdt.core.CompletionProposal;
import org.eclipse.jdt.core.CompletionRequestor;

/** Diagnostic only: no preference, model, type or index queries are made here. */
@SuppressWarnings({"nls", "rawtypes", "unchecked"})
public final class Completion5364Trace {
    private static final boolean ENABLED = Boolean.getBoolean("completion5364.trace");
    private static final int LIMIT = 512;
    private static final ThreadLocal<List<String>> EVENTS = new ThreadLocal<>();
    private Completion5364Trace() {}
    public static void begin(String test) {
        if (!ENABLED) return;
        EVENTS.set(new ArrayList<>());
        event("TEST", test);
    }
    public static boolean active() { return EVENTS.get() != null; }
    public static void event(String phase, Object value) {
        List<String> events = EVENTS.get();
        if (events != null && events.size() <= LIMIT) {
            events.add(events.size() == LIMIT ? "TRUNCATED" : phase + " " + String.valueOf(value));
        }
    }
    private static String characters(char[] value) {
        return value == null ? "null" : new String(value);
    }
    public static void name(String phase, char[] name) {
        if (active()) event(phase, characters(name));
    }
    public static void type(String phase, char[] pkg, char[] name, int flags) {
        if (active()) event(phase, (pkg == null ? "" : new String(pkg)) + "."
                + characters(name) + " flags=" + flags);
    }
    public static void options(Map settings) {
        if (active()) event("ENGINE_SETTINGS", new TreeMap(settings));
    }
    public static void deliver(CompletionRequestor requestor, CompletionProposal proposal) {
        if (active()) event("DELIVER", "kind=" + proposal.getKind()
                + " completion=" + characters(proposal.getCompletion())
                + " signature=" + characters(proposal.getSignature())
                + " relevance=" + proposal.getRelevance());
        requestor.accept(proposal);
    }
    public static void end() {
        List<String> events = EVENTS.get();
        EVENTS.remove();
        // Defer console I/O until after the test, including its cleanup, has finished.
        if (events != null) {
            System.out.println("COMPLETION5364_TRACE_BEGIN");
            for (String event : events) System.out.println("COMPLETION5364 " + event.replace("\n", "\\n").replace("\r", "\\r"));
            System.out.println("COMPLETION5364_TRACE_END");
        }
    }
}
