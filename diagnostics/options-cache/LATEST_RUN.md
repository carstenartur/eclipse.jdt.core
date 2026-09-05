# Latest options-cache validation

Revision: d087d1062c5548b36cd0d3fa6b49ffa46bb50e72
Run: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33954118986
Validation: failure
Publication: skipped

## history-origin.json
```
{
  "sha": "665fa70c145e3460af8c3efab89c50489feb17d0",
  "date": "2005-05-17",
  "subject": "Support for simulating exit/restart of workspace in tests"
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

Time: 1.479

OK (2 tests)

UI_DIAGNOSTIC_RESULT tests=2 failures=0 ignored=0

!ENTRY org.eclipse.ui.workbench 4 0 2026-09-05 08:03:09.397
!MESSAGE An internal error has occurred.
!STACK 0
java.lang.NullPointerException: Cannot invoke "org.eclipse.ui.services.IEvaluationService.addSourceProvider(org.eclipse.ui.ISourceProvider)" because "evaluationService" is null
	at org.eclipse.tips.ide.internal.IDETipManager.open(IDETipManager.java:110)
	at org.eclipse.tips.ide.internal.TipsStartupService$3.runInUIThread(TipsStartupService.java:204)
	at org.eclipse.ui.progress.UIJob.lambda$0(UIJob.java:148)
	at org.eclipse.swt.widgets.RunnableLock.run(RunnableLock.java:40)
	at org.eclipse.swt.widgets.Synchronizer.runAsyncMessages(Synchronizer.java:131)
	at org.eclipse.swt.widgets.Display.runAsyncMessages(Display.java:5078)
	at org.eclipse.swt.widgets.Display.readAndDispatch(Display.java:4534)
	at org.eclipse.swt.widgets.Display.release(Display.java:4602)
	at org.eclipse.swt.graphics.Device.dispose(Device.java:297)
	at diagnostics.UIApp.start(UIApp.java:54)
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

!ENTRY org.eclipse.equinox.event 4 0 2026-09-05 08:03:09.405
!MESSAGE Exception while dispatching event org.osgi.service.event.Event [topic=org/eclipse/e4/ui/LifeCycle/appStartupComplete] {org.eclipse.e4.data=org.eclipse.e4.legacy.ide.application=org.eclipse.e4.ui.model.application.impl.ApplicationImpl@34b87182 (tags: [activeSchemeId:org.eclipse.ui.defaultAcceleratorConfiguration], contributorURI: platform:/plugin/org.eclipse.platform) (widget: null, toBeRendered: true, visible: true) (context: WorkbenchContext, variables: null)} to handler org.eclipse.e4.ui.internal.di.UIEventObjectSupplier$UIEventHandler@284c0a32Exception in thread "Event Loop Monitor" 
!STACKorg.eclipse.swt.SWTException: Device is disposed
	at org.eclipse.swt.SWT.error(SWT.java:4934)
 0
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
	at org.eclipse.swt.SWT.error(SWT.java:4849)
	at org.eclipse.swt.SWT.error(SWT.java:4820)
	at org.eclipse.swt.widgets.Display.error(Display.java:1581)
	at org.eclipse.swt.widgets.Display.asyncExec(Display.java:924)
	at org.eclipse.ui.internal.monitoring.EventLoopMonitorThread.run(EventLoopMonitorThread.java:492)

!ENTRY org.eclipse.core.resources 2 10035 2026-09-05 08:03:09.989
!MESSAGE The workspace will exit with unsaved changes in this session.
Logged Eclipse errors in stock/ui: 2; inspect before publication
```
