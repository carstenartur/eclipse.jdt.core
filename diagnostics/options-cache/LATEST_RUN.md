# Latest options-cache validation

Revision: 5424aa47bd25e8811cb499d31cbb02300091fa78
Run: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33954378922
Validation: failure
Publication: skipped

## history-origin.json
```
{
  "sha": "75e4065d4db8d1c67a280c4b46e8853fada67561",
  "date": "2005-04-19",
  "subject": "91716 (fix improvement)",
  "cache_locations_before": [],
  "cache_locations_after": [
    "org.eclipse.jdt.core/model/org/eclipse/jdt/core/JavaCore.java"
  ],
  "introduction_verified": true,
  "diff_excerpt": "diff --git a/org.eclipse.jdt.core/model/org/eclipse/jdt/core/JavaCore.java b/org.eclipse.jdt.core/model/org/eclipse/jdt/core/JavaCore.java\nindex 1ae5293296..b61c167364 100644\n--- a/org.eclipse.jdt.core/model/org/eclipse/jdt/core/JavaCore.java\n+++ b/org.eclipse.jdt.core/model/org/eclipse/jdt/core/JavaCore.java\n@@ -991,6 +991,11 @@ public final class JavaCore extends Plugin {\n \t */\n \tpublic static final String PRIVATE = \"private\"; //$NON-NLS-1$\n \n+\t/*\n+\t * Cache for options.\n+\t */\n+\tstatic Hashtable optionsCache;\n+\n \t/**\n \t * Creates the Java core plug-in.\n \t * <p>\n@@ -2389,6 +2394,9 @@ public final class JavaCore extends Plugin {\n \t */\n \tpublic static Hashtable getOptions() {\n \n+\t\t// return cached options if already computed\n+\t\tif (optionsCache != null) return new Hashtable(optionsCache);\n+\n \t\t// init\n \t\tHashtable options = new Hashtable(10);\n \t\tJavaModelManager manager = JavaModelManager.getJavaModelManager();\n@@ -2412,6 +2420,9 @@ public final class JavaCore extends Plugin {\n \t\toptions.put(COMPILER_PB_INVALID_IMPORT, ERROR);\n \t\toptions.put(COMPILER_PB_UNREACHABLE_CODE, ERROR);\n \n+\t\t// store built map in cache\n+\t\toptionsCache = new Hashtable(options);\n+\n \t\t// return built map\n \t\treturn options;\n \t}\n@@ -3989,8 +4000,8 @@ public final class JavaCore extends Plugin {\n \t\t\t// persist options\n \t\t\tinstancePreferences.flush();\n \t\t\t\n-\t\t\t// reset stored projects options\n-\t\t\tJavaModelManager.getJavaModelManager().resetAllProjectOptions();\n+\t\t\t// update cache\n+\t\t\toptionsCache = newOptions==null ? null : new Hashtable(newOptions);\n \t\t} catch (BackingStoreException e) {\n \t\t\t// ignore\n \t\t}\n@@ -4048,6 +4059,14 @@ public final class JavaCore extends Plugin {\n \t\t\t// Initialize eclipse preferences\n \t\t\tmanager.initializePreferences();\n \n+\t\t\t// Listen to preference changes\n+\t\t\tPreferences.IPropertyChangeListener propertyListener = new Preferences.IPropertyChangeListener() {\n+\t\t\t\tpublic void propertyChange(Preferences.PropertyChangeEvent event) {\n+\t\t\t\t\tJavaCore.optionsCache = null;\n+\t\t\t\t}\n+\t\t\t};\n+\t\t\tJavaCore.getPlugin().getPluginPreferences().addPropertyChangeListener(propertyListener);\n+\n \t\t\t// retrieve variable values\n \t\t\tmanager.loadVariablesAndContainers();\n \ndiff --git a/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java b/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java\nindex 214c659794..f6d55419a5 100644\n--- a/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java\n+++ b/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java\n@@ -660,7 +660,7 @@ public class JavaModelManager implements ISaveParticipant {\n \t\tpublic IPath outputLocation;\n \t\t\n \t\tpublic IEclipsePreferences preferences;\n-\t\tpublic Map options;\n+\t\tpublic Hashtable options;\n \t\t\n \t\tpublic PerProjectInfo(IProject project) {\n \n@@ -1858,19 +1858,6 @@ public class JavaModelManager implements ISaveParticipant {\n \t\t}\n \t}\n \n-\t/*\n-\t * Reset all projects options stored in info cache.\n-\t */\n-\tpublic void resetAllProjectOptions() {\n-\t\tsynchronized(this.perProjectInfos) { // use the perProjectInfo collection as its own lock\n-\t\t\tIterator projects = this.perProjectInfos.keySet().iterator();\n-\t\t\twhile (projects.hasNext()) {\n-\t\t\t\tPerProjectInfo info= (PerProjectInfo) this.perProjectInfos.get(projects.next());\n-\t\t\t\tinfo.options = null;\n-\t\t\t}\n-\t\t}\n-\t}\n-\n \t/*\n \t * Reset project options stored in info cache.\n \t */\n"
}

```
## sdk-provenance.json
```
{
  "archive": "eclipse-SDK-I20260826-2300-linux-gtk-x86_64.tar.gz",
  "checksum_manifest_url": "https://download.eclipse.org/eclipse/downloads/drops4/I20260826-2300/eclipse-I20260826-2300-checksums",
  "sha256": "1a81564c817ba6016557f6b75e3c3a31e3d4532f42e8ab8883b74ebcc68ddbce",
  "sha512": "ca3af8dc5b7d8aaae46357aa0eb949fdd7b47641fc54a62546bb75a0213d79fd7ad29063890fc90f0a69d5fb7ef319023956e43de57d9441817f49c8e54954a2",
  "published_sha512": "ca3af8dc5b7d8aaae46357aa0eb949fdd7b47641fc54a62546bb75a0213d79fd7ad29063890fc90f0a69d5fb7ef319023956e43de57d9441817f49c8e54954a2",
  "checksum_matches": true
}

```
## method-provenance.json
```
[
  {
    "method": "public Hashtable<String, String> getOptions()",
    "equal": true,
    "sdk_sha256": "ae1d69fc7e8f91996c2ea9553c8a93861072cad1d768be9e606ed5f16cf94b06",
    "upstream_sha256": "ae1d69fc7e8f91996c2ea9553c8a93861072cad1d768be9e606ed5f16cf94b06"
  },
  {
    "method": "public void setOptions(Hashtable<String, String> newOptions)",
    "equal": true,
    "sdk_sha256": "49636cb5d2d6ff5a848e422b318e826d715e96d99ee286c33c3a2f5d0cb8abc9",
    "upstream_sha256": "49636cb5d2d6ff5a848e422b318e826d715e96d99ee286c33c3a2f5d0cb8abc9"
  }
]

```
## fixed-headless.txt
```
DIAGNOSTIC_RESULT tests=6 failures=0 ignored=0
```
## fixed-native.txt
```
NATIVE_RESULT tests=8 failures=0 ignored=0
```
## fixed-ui.txt
```
SAVE_BEFORE race=false persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=12
SAVE_AFTER race=false length=105 stamp=14 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String) o;\n    }\n}
SAVE_BEFORE race=true persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=20
SAVE_AFTER race=true length=105 stamp=22 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String) o;\n    }\n}
UI_DIAGNOSTIC_RESULT tests=2 failures=0 ignored=0
```
## stock-headless.txt
```
org.junit.ComparisonFailure: Fresh formatter after both threads completed must see the newly selected spacing expected:<... String s = (String)[ ]o;
org.junit.ComparisonFailure: A read must not resurrect a cache invalidated by a completed preference update expected:<[]insert> but was:<[do not ]insert>
org.junit.ComparisonFailure: Both operations completed: cached options must match persisted preferences expected:<[]insert> but was:<[do not ]insert>
DIAGNOSTIC_FAILURE completedOptionUpdateMustReachChangedLineFormatter(diagnostics.OptionsCacheConsistencyTest)
org.junit.ComparisonFailure: Fresh formatter after both threads completed must see the newly selected spacing expected:<... String s = (String)[ ]o;
DIAGNOSTIC_FAILURE readerMustNotUndoPreferenceInvalidation(diagnostics.OptionsCacheConsistencyTest)
org.junit.ComparisonFailure: A read must not resurrect a cache invalidated by a completed preference update expected:<[]insert> but was:<[do not ]insert>
DIAGNOSTIC_FAILURE readerMustNotOverwriteCompletedSetOptions(diagnostics.OptionsCacheConsistencyTest)
org.junit.ComparisonFailure: Both operations completed: cached options must match persisted preferences expected:<[]insert> but was:<[do not ]insert>
DIAGNOSTIC_RESULT tests=6 failures=3 ignored=0
```
## stock-native.txt
```
junit.framework.ComparisonFailure: A completed REPEATED_INVALIDATION must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
junit.framework.ComparisonFailure: A completed SET_OPTIONS must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
junit.framework.ComparisonFailure: A completed PREFERENCE must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
junit.framework.ComparisonFailure: A completed RESET must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
NATIVE_FAILURE testRepeatedInvalidationCannotBeUndone(org.eclipse.jdt.core.tests.model.OptionCacheTests)
junit.framework.ComparisonFailure: A completed REPEATED_INVALIDATION must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
NATIVE_FAILURE testCompletedSetOptionsCannotBeOverwritten(org.eclipse.jdt.core.tests.model.OptionCacheTests)
junit.framework.ComparisonFailure: A completed SET_OPTIONS must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
NATIVE_FAILURE testPreferenceInvalidationCannotBeUndone(org.eclipse.jdt.core.tests.model.OptionCacheTests)
junit.framework.ComparisonFailure: A completed PREFERENCE must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
NATIVE_FAILURE testCompletedResetCannotBeOverwritten(org.eclipse.jdt.core.tests.model.OptionCacheTests)
junit.framework.ComparisonFailure: A completed RESET must not be undone by an older reader expected:<[]insert> but was:<[do not ]insert>
NATIVE_RESULT tests=8 failures=4 ignored=0
```
## stock-ui.txt
```
SAVE_BEFORE race=false persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=12
SAVE_AFTER race=false length=105 stamp=14 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String) o;\n    }\n}
SAVE_BEFORE race=true persisted=insert cache=do not insert project=do not insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=20
SAVE_AFTER race=true length=104 stamp=21 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String)o;\n    }\n}
org.junit.ComparisonFailure: Real editor save action must use the completed option update expected:<... String s = (String)[ ]o;
UI_DIAGNOSTIC_FAILURE saveMustUseCompletedOptionUpdate(diagnostics.SaveParticipantIntegrationTest)
org.junit.ComparisonFailure: Real editor save action must use the completed option update expected:<... String s = (String)[ ]o;
UI_DIAGNOSTIC_RESULT tests=2 failures=1 ignored=0
```
## Last lines of execution.log
```
	at org.eclipse.swt.widgets.Synchronizer.runAsyncMessages(Synchronizer.java:131)
	at org.eclipse.swt.widgets.Display.runAsyncMessages(Display.java:5078)
	at org.eclipse.swt.widgets.Display.readAndDispatch(Display.java:4534)
	at org.eclipse.e4.ui.internal.workbench.swt.PartRenderingEngine$5.run(PartRenderingEngine.java:1160)
	at org.eclipse.core.databinding.observable.Realm.runWithDefault(Realm.java:339)
	at org.eclipse.e4.ui.internal.workbench.swt.PartRenderingEngine.run(PartRenderingEngine.java:1051)
	at org.eclipse.e4.ui.internal.workbench.E4Workbench.createAndRunUI(E4Workbench.java:153)
	at org.eclipse.ui.internal.Workbench.lambda$3(Workbench.java:680)
	at org.eclipse.core.databinding.observable.Realm.runWithDefault(Realm.java:339)
	at org.eclipse.ui.internal.Workbench.createAndRunWorkbench(Workbench.java:583)
	at org.eclipse.ui.PlatformUI.createAndRunWorkbench(PlatformUI.java:173)
	at diagnostics.UIApp.start(UIApp.java:21)
	at org.eclipse.equinox.internal.app.EclipseAppHandle.run(EclipseAppHandle.java:219)
	at org.eclipse.core.runtime.internal.adaptor.EclipseAppLauncher.runApplication(EclipseAppLauncher.java:149)
	at org.eclipse.core.runtime.internal.adaptor.EclipseAppLauncher.start(EclipseAppLauncher.java:115)
	at org.eclipse.core.runtime.adaptor.EclipseStarter.run(EclipseStarter.java:467)
	at org.eclipse.core.runtime.adaptor.EclipseStarter.run(EclipseStarter.java:298)
	at java.base/jdk.internal.reflect.DirectMethodHandleAccessor.invoke(DirectMethodHandleAccessor.java:104)
	at java.base/java.lang.reflect.Method.invoke(Method.java:565)
	at org.eclipse.equinox.launcher.Main.invokeFramework(Main.java:615)
	at org.eclipse.equinox.launcher.Main.basicRun(Main.java:563)
	at org.eclipse.equinox.launcher.Main.run(Main.java:1415)
	at org.eclipse.equinox.launcher.Main.main(Main.java:1387)
OPTIONS_RACE writer=JavaCore.setOptions overlapping=do not insert persisted=insert subsequentCached=insert
SAVE_BEFORE race=true persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=20
SAVE_AFTER race=true length=105 stamp=22 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String) o;\n    }\n}

Time: 1.5

OK (2 tests)

UI_DIAGNOSTIC_RESULT tests=2 failures=0 ignored=0
Exception in thread "Event Loop Monitor" 
!ENTRY org.eclipse.equinox.event 4 0 2026-09-05 08:08:54.436
!MESSAGE Exception while dispatching event org.osgi.service.event.Event [topic=org/eclipse/e4/ui/LifeCycle/appStartupComplete] {org.eclipse.e4.data=org.eclipse.e4.legacy.ide.application=org.eclipse.e4.ui.model.application.impl.ApplicationImpl@40d60f2 (tags: [activeSchemeId:org.eclipse.ui.defaultAcceleratorConfiguration], contributorURI: platform:/plugin/org.eclipse.platform) (widget: null, toBeRendered: true, visible: true) (context: WorkbenchContext, variables: null)} to handler org.eclipse.e4.ui.internal.di.UIEventObjectSupplier$UIEventHandler@684c6d55
org.eclipse.swt.SWTException: Device is disposed
!STACK 0
org.eclipse.swt.SWTException: Device is disposed
	at org.eclipse.swt.SWT.error(SWT.java:4934)
	at org.eclipse.swt.SWT.error(SWT.java:4849)
	at org.eclipse.swt.SWT.error(SWT.java:4820)
	at org.eclipse.swt.widgets.Display.error(Display.java:1581)
	at org.eclipse.swt.widgets.Display.syncExec(Display.java:5981)
	at org.eclipse.e4.ui.workbench.swt.DisplayUISynchronize.syncExec(DisplayUISynchronize.java:34)
	at org.eclipse.e4.ui.internal.di.UIEventObjectSupplier$UIEventHandler.handleEvent(UIEventObjectSupplier.java:65)
	at org.eclipse.equinox.internal.event.EventHandlerWrapper.handleEvent(EventHandlerWrapper.java:206)
	at org.eclipse.equinox.internal.event.EventHandlerTracker.dispatchEvent(EventHandlerTracker.java:201)
	at org.eclipse.equinox.internal.event.EventHandlerTracker.dispatchEvent(EventHandlerTracker.java:1)
	at org.eclipse.osgi.framework.eventmgr.EventManager.dispatchEvent(EventManager.java:230)
	at org.eclipse.osgi.framework.eventmgr.EventManager$EventThread.run(EventManager.java:341)
	at org.eclipse.swt.SWT.error(SWT.java:4934)
	at org.eclipse.swt.SWT.error(SWT.java:4849)
	at org.eclipse.swt.SWT.error(SWT.java:4820)
	at org.eclipse.swt.widgets.Display.error(Display.java:1581)
	at org.eclipse.swt.widgets.Display.asyncExec(Display.java:924)
	at org.eclipse.ui.internal.monitoring.EventLoopMonitorThread.run(EventLoopMonitorThread.java:492)

!ENTRY org.eclipse.core.resources 2 10035 2026-09-05 08:08:54.514
!MESSAGE The workspace will exit with unsaved changes in this session.
Logged Eclipse errors in stock/ui: 3; inspect before publication
```
