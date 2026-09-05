# Latest options-cache validation

Revision: b45f26001068b76d79451287c8b5b8cf69f36fc8
Run: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33954892515
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

```
## Last lines of execution.log
```
	at org.eclipse.core.runtime.internal.adaptor.EclipseAppLauncher.start(EclipseAppLauncher.java:115)
	at org.eclipse.core.runtime.adaptor.EclipseStarter.run(EclipseStarter.java:467)
	at org.eclipse.core.runtime.adaptor.EclipseStarter.run(EclipseStarter.java:298)
	at java.base/jdk.internal.reflect.DirectMethodHandleAccessor.invoke(DirectMethodHandleAccessor.java:104)
	at java.base/java.lang.reflect.Method.invoke(Method.java:565)
	at org.eclipse.equinox.launcher.Main.invokeFramework(Main.java:615)
	at org.eclipse.equinox.launcher.Main.basicRun(Main.java:563)
	at org.eclipse.equinox.launcher.Main.run(Main.java:1415)
	at org.eclipse.equinox.launcher.Main.main(Main.java:1387)

!ENTRY org.eclipse.equinox.event 4 0 2026-09-05 08:19:56.537
!MESSAGE Exception while dispatching event org.osgi.service.event.Event [topic=org/eclipse/e4/ui/LifeCycle/appStartupComplete] {org.eclipse.e4.data=org.eclipse.e4.legacy.ide.application=org.eclipse.e4.ui.model.application.impl.ApplicationImpl@51ab1ee3 (tags: [activeSchemeId:org.eclipse.ui.defaultAcceleratorConfiguration], contributorURI: platform:/plugin/org.eclipse.platform) (widget: null, toBeRendered: true, visible: true) (context: WorkbenchContext, variables: null)} to handler org.eclipse.ui.internal.monitoring.MonitoringStartup@3c41614
!STACK 0
org.eclipse.swt.SWTException: Device is disposed
	at org.eclipse.swt.SWT.error(SWT.java:4934)
	at org.eclipse.swt.SWT.error(SWT.java:4849)
	at org.eclipse.swt.SWT.error(SWT.java:4820)
	at org.eclipse.swt.widgets.Display.error(Display.java:1581)
	at org.eclipse.swt.widgets.Display.asyncExec(Display.java:924)
	at org.eclipse.ui.internal.monitoring.MonitoringStartup.createAndStartMonitorThread(MonitoringStartup.java:70)
	at org.eclipse.ui.internal.monitoring.MonitoringStartup.handleEvent(MonitoringStartup.java:47)
	at org.eclipse.equinox.internal.event.EventHandlerWrapper.handleEvent(EventHandlerWrapper.java:206)
	at org.eclipse.equinox.internal.event.EventHandlerTracker.dispatchEvent(EventHandlerTracker.java:201)
	at org.eclipse.equinox.internal.event.EventHandlerTracker.dispatchEvent(EventHandlerTracker.java:1)
	at org.eclipse.osgi.framework.eventmgr.EventManager.dispatchEvent(EventManager.java:230)
	at org.eclipse.osgi.framework.eventmgr.EventManager$EventThread.run(EventManager.java:341)

!ENTRY org.eclipse.e4.ui.workbench 4 0 2026-09-05 08:19:56.555
!MESSAGE FrameworkEvent ERROR
!STACK 0
org.eclipse.swt.SWTException: Device is disposed
	at org.eclipse.swt.SWT.error(SWT.java:4934)
	at org.eclipse.swt.SWT.error(SWT.java:4849)
	at org.eclipse.swt.SWT.error(SWT.java:4820)
	at org.eclipse.swt.widgets.Display.error(Display.java:1581)
	at org.eclipse.swt.widgets.Display.asyncExec(Display.java:924)
	at org.eclipse.ui.internal.WorkbenchWindow$3.changed(WorkbenchWindow.java:883)
	at org.eclipse.e4.core.internal.contexts.TrackableComputationExt.update(TrackableComputationExt.java:109)
	at org.eclipse.e4.core.internal.contexts.EclipseContext.processScheduled(EclipseContext.java:371)
	at org.eclipse.e4.core.internal.contexts.EclipseContext.dispose(EclipseContext.java:189)
	at org.eclipse.e4.core.internal.contexts.EclipseContext.dispose(EclipseContext.java:172)
	at org.eclipse.e4.core.internal.contexts.EclipseContext.dispose(EclipseContext.java:172)
	at org.eclipse.e4.core.internal.contexts.EclipseContext.dispose(EclipseContext.java:172)
	at org.eclipse.e4.core.internal.contexts.EclipseContext.dispose(EclipseContext.java:172)
	at org.eclipse.e4.core.internal.contexts.osgi.EclipseContextOSGi.dispose(EclipseContextOSGi.java:106)
	at org.eclipse.e4.core.internal.contexts.osgi.EclipseContextOSGi.bundleChanged(EclipseContextOSGi.java:149)
	at org.eclipse.osgi.internal.framework.BundleContextImpl.dispatchEvent(BundleContextImpl.java:987)
	at org.eclipse.osgi.framework.eventmgr.EventManager.dispatchEvent(EventManager.java:230)
	at org.eclipse.osgi.framework.eventmgr.ListenerQueue.dispatchEventSynchronous(ListenerQueue.java:151)
	at org.eclipse.osgi.internal.framework.EquinoxEventPublisher.publishBundleEventPrivileged(EquinoxEventPublisher.java:237)
	at org.eclipse.osgi.internal.framework.EquinoxEventPublisher.publishBundleEvent(EquinoxEventPublisher.java:136)
	at org.eclipse.osgi.internal.framework.EquinoxEventPublisher.publishBundleEvent(EquinoxEventPublisher.java:128)
	at org.eclipse.osgi.internal.framework.EquinoxContainerAdaptor.publishModuleEvent(EquinoxContainerAdaptor.java:232)
	at org.eclipse.osgi.container.Module.publishEvent(Module.java:534)
	at org.eclipse.osgi.container.Module.doStop(Module.java:697)
	at org.eclipse.osgi.container.Module.stop(Module.java:557)
	at org.eclipse.osgi.container.SystemModule.stop(SystemModule.java:212)
	at org.eclipse.osgi.internal.framework.EquinoxBundle$SystemBundle$EquinoxSystemModule$1.run(EquinoxBundle.java:244)
	at java.base/java.lang.Thread.run(Thread.java:1474)
Unexpected stock/ui completion: []
```
