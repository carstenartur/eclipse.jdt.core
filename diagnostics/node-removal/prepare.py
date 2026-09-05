#!/usr/bin/env python3
"""Prepare a two-file follow-up and a separate execution harness; no test weakening."""
from pathlib import Path
import sys

candidate, diag = map(Path, sys.argv[1:])
manager = candidate / 'org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java'
source = manager.read_text()
old = '''					JavaModelManager.this.preferencesLookup[PREF_INSTANCE] = InstanceScope.INSTANCE.getNode(JavaCore.PLUGIN_ID);
					JavaModelManager.this.preferencesLookup[PREF_INSTANCE].addPreferenceChangeListener(new EclipsePreferencesListener());'''
new = '''					IEclipsePreferences preferences = InstanceScope.INSTANCE.getNode(JavaCore.PLUGIN_ID);
					JavaModelManager.this.preferencesLookup[PREF_INSTANCE] = preferences;
					preferences.addPreferenceChangeListener(JavaModelManager.this.instancePreferencesListener = new EclipsePreferencesListener());
					// The old node's listeners are not transferred to its replacement.
					if (JavaModelManager.this.propertyListener != null) {
						preferences.addPreferenceChangeListener(JavaModelManager.this.propertyListener);
					}
					JavaModelManager.this.setOptionsCache(null);'''
assert source.count(old) == 1
manager.write_text(source.replace(old, new))

tests = candidate / 'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java'
source = tests.read_text()
anchor = '\tprivate void setOption(String value) {'
addition = '''	public void testInstanceNodeRemovalInvalidatesCache() throws Exception {
		Hashtable<String, String> preferences = saveInstancePreferences();
		try {
			String defaultValue = JavaCore.getDefaultOptions().get(KEY);
			assertNotNull(defaultValue);
			String oldValue = opposite(defaultValue);
			setOption(oldValue);
			assertEquals(oldValue, JavaCore.getOptions().get(KEY));

			JavaModelManager manager = JavaModelManager.getJavaModelManager();
			IEclipsePreferences removed = manager.getInstancePreferences();
			removed.removeNode();
			assertNotSame(removed, manager.getInstancePreferences());
			assertEquals(defaultValue, JavaCore.getOption(KEY));
			assertEquals("Removing the instance node must invalidate its cached options",
					defaultValue, JavaCore.getOptions().get(KEY));
		} finally {
			restoreInstancePreferences(preferences);
		}
	}

	public void testInstanceNodeReplacementKeepsInvalidatingCache() throws Exception {
		Hashtable<String, String> preferences = saveInstancePreferences();
		try {
			String defaultValue = JavaCore.getDefaultOptions().get(KEY);
			assertNotNull(defaultValue);
			String newValue = opposite(defaultValue);
			JavaModelManager manager = JavaModelManager.getJavaModelManager();
			for (int i = 0; i < 2; i++) {
				IEclipsePreferences removed = manager.getInstancePreferences();
				removed.removeNode();
				IEclipsePreferences replacement = manager.getInstancePreferences();
				assertNotSame(removed, replacement);
				setOption(defaultValue);
				assertEquals(defaultValue, JavaCore.getOptions().get(KEY));
				replacement.put(KEY, newValue);
				assertEquals(newValue, JavaCore.getOption(KEY));
				assertEquals("Preference changes must invalidate the cache after node replacement " + i,
						newValue, JavaCore.getOptions().get(KEY));
			}
		} finally {
			restoreInstancePreferences(preferences);
		}
	}

	private static Hashtable<String, String> saveInstancePreferences() throws Exception {
		IEclipsePreferences node = JavaModelManager.getJavaModelManager().getInstancePreferences();
		Hashtable<String, String> preferences = new Hashtable<>();
		for (String key : node.keys()) {
			preferences.put(key, node.get(key, ""));
		}
		return preferences;
	}

	private static void restoreInstancePreferences(Hashtable<String, String> preferences) throws Exception {
		// Node removal also affects non-option preferences, such as classpath variables.
		IEclipsePreferences node = JavaModelManager.getJavaModelManager().getInstancePreferences();
		node.clear();
		preferences.forEach(node::put);
	}

'''
assert source.count(anchor) == 1
tests.write_text(source.replace(anchor, addition + anchor))
# Prove all eight existing test bodies, fixtures and timeouts remain byte-identical.
assert tests.read_text().replace(addition, '') == source
out = diag / 'src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(tests.read_bytes())

(diag / 'src/diagnostics/NativeApplication.java').write_text('''package diagnostics;

import java.util.Set;
import org.eclipse.core.resources.ResourcesPlugin;
import org.eclipse.core.runtime.preferences.IEclipsePreferences;
import org.eclipse.equinox.app.IApplication;
import org.eclipse.equinox.app.IApplicationContext;
import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.tests.model.OptionCacheTests;
import org.eclipse.jdt.internal.core.JavaModelManager;
import org.junit.internal.TextListener;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;
import junit.framework.TestCase;
import junit.framework.TestSuite;

public class NativeApplication implements IApplication {
    private static final Set<String> LIFECYCLE = Set.of(
        "testInstanceNodeRemovalInvalidatesCache", "testInstanceNodeReplacementKeepsInvalidatingCache");
    @Override
    public Object start(IApplicationContext context) throws Exception {
        ResourcesPlugin.getWorkspace();
        String mode = System.getenv().getOrDefault("NATIVE_MODE", "all");
        boolean remove = Boolean.parseBoolean(System.getenv().getOrDefault("REMOVE_NODE", "false"));
        int repeats = Integer.parseInt(System.getenv().getOrDefault("NATIVE_REPEATS", "1"));
        int failures = 0;
        for (int iteration = 1; iteration <= repeats; iteration++) {
            if (remove) {
                // The same operations as the preceding OptionTests.testBug72214().
                JavaModelManager manager = JavaModelManager.getJavaModelManager();
                IEclipsePreferences previous = manager.getInstancePreferences();
                int size = JavaCore.getOptions().size();
                previous.removeNode();
                if (previous == manager.getInstancePreferences() || size != JavaCore.getOptions().size()) {
                    throw new AssertionError("OptionTests.testBug72214 precondition failed");
                }
                System.out.println("REPLAYED OptionTests.testBug72214 preference-node removal");
            }
            TestSuite suite = new TestSuite();
            TestSuite all = new TestSuite(OptionCacheTests.class);
            for (int i = 0; i < all.testCount(); i++) {
                TestCase test = (TestCase) all.testAt(i);
                boolean lifecycle = LIFECYCLE.contains(test.getName());
                if (mode.equals("all") || (mode.equals("lifecycle") == lifecycle)) {
                    suite.addTest(test);
                }
            }
            JUnitCore runner = new JUnitCore();
            runner.addListener(new TextListener(System.out));
            Result result = runner.run(suite);
            for (Failure failure : result.getFailures()) {
                System.out.println("NATIVE_FAILURE " + failure.getTestHeader());
                System.out.println(failure.getTrace());
            }
            System.out.printf("NATIVE_RESULT tests=%d failures=%d ignored=%d%n",
                    result.getRunCount(), result.getFailureCount(), result.getIgnoreCount());
            failures += result.getFailureCount();
        }
        return Integer.valueOf(failures == 0 ? 0 : 1);
    }
    @Override
    public void stop() {}
}
''')
plugin = diag / 'plugin.xml'
plugin.write_text(plugin.read_text().replace('</plugin>', '''  <extension point="org.eclipse.core.runtime.applications" id="native">
    <application cardinality="singleton-global" thread="main" visible="true">
      <run class="diagnostics.NativeApplication"/>
    </application>
  </extension>
</plugin>'''))
print('Prepared two-file follow-up; original eight tests unchanged')
