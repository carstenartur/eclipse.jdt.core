# Latest options-cache validation

Revision: b6378ff2141ba4b945e97d7c8b754c7848f509e4
Run: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33955492150
Validation: success
Publication: success

## VALIDATION.md
```
# Options-cache publication fix: executed validation

| Arm | Test layer | Executed | Failed | Ignored | Logged Eclipse errors |
| --- | --- | ---: | ---: | ---: | ---: |
| stock | native | 8 | 4 | 0 | 0 |
| stock | headless | 6 | 3 | 0 | 0 |
| stock | ui | 2 | 1 | 0 | 0 |
| fixed | native | 8 | 0 | 0 | 0 |
| fixed | headless | 6 | 0 | 0 | 0 |
| fixed | ui | 2 | 0 | 0 | 0 |

Stock fails exactly the four native cache assertions, three original headless assertions and one original editor-save assertion. Fixed passes all 16 tests. No tests were ignored.

Native test source is copied byte-for-byte from the proposed upstream test file. Only JavaModelManager and its nested classes are replaced in the disposable fixed SDK. Other SDK bundles are hash-checked unchanged.

The UI harness registers the standard IDE workspace adapters in both arms. The formatter and editor test assertions are unchanged. This is targeted testing, not a full Tycho/JDT suite run.

The extra space before assignment and historical malformed-edit exceptions of jdt.ui#1445 have not been reproduced or claimed fixed.

```
## validation-success.json
```
{
  "native": 8,
  "headless": 6,
  "ui": 2,
  "stock_failures": 8,
  "fixed_failures": 0,
  "ignored": 0
}

```
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
## published-commit.txt
```
commit db389f7e72f88da5ded1debd337956b960fc3711
Author:     Carsten Hammer <carsten.hammer@t-online.de>
AuthorDate: Sat Sep 5 08:33:22 2026 +0000
Commit:     Carsten Hammer <carsten.hammer@t-online.de>
CommitDate: Sat Sep 5 08:33:22 2026 +0000

    Prevent stale Java options cache publication after concurrent updates
    
    A cold JavaModelManager.getOptions() can read old preference values, then
    publish its map after a concurrent JavaCore.setOptions() has completed or
    a preference event has invalidated the cache. Subsequent non-overlapping
    getOptions() calls then disagree with getOption(). Defensive Hashtable
    copies and the existing volatile reference do not prevent this lost
    invalidation / late-publication race.
    
    Track a cache generation and publish a reader's snapshot only if no
    writer or invalidation has advanced that generation. Coordinate the
    comparison/publication and generation changes under a short private lock.
    Keep all preference reads, writes, listeners, copying and tracing outside
    that lock; retain the cached fast path and defensive-copy semantics.
    An overlapping read may return its snapshot but may not cache it after
    an intervening update. Invalidation advances the generation even when
    the cache is already null, avoiding null-to-null / ABA invalidations.
    
    Route all cache invalidations through the same protocol. End an options
    reset with a generation-advancing invalidation before rebuilding, so a
    partially computed reset snapshot cannot become the post-reset cache.
    
    Add OptionCacheTests to the model suite. Real preference reads are paused
    using bounded CountDownLatch barriers; delegating proxies retain actual
    values and release preference locks before pausing. Cover completed
    setter/reset races, direct and repeated invalidations, cache reuse,
    returned-copy isolation, sequential writes and reentrant preference
    callbacks. Restore settings, lookup nodes and worker threads after tests.
    
    Validation: all eight new native tests, six established headless Core /
    formatter tests and two real JavaEditor.doSave integration tests execute
    against the same pinned Eclipse SDK. Baseline fails exactly eight race
    assertions; the fixed version passes all 16, with no ignored tests or
    logged Eclipse errors. Compile the actual patched upstream
    JavaModelManager source into the disposable SDK; verify that other SDK
    bundles are unchanged. In both arms the minimal UI harness registers IDE
    workspace adapters and excludes the unrelated optional Tips add-on to
    avoid its startup UI racing test-workbench shutdown. No UI product code
    or test assertions are modified. This is targeted validation, not a full
    Tycho or complete JDT regression-suite run.
    Evidence: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33955492150
    Upstream base: 8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51
    SDK: I20260826-2300; JDK 25; Linux GTK x86_64
    SDK SHA-256: 1a81564c817ba6016557f6b75e3c3a31e3d4532f42e8ab8883b74ebcc68ddbce
    The archive matches Eclipse's official HTTPS SHA-512 checksum manifest.
    
    History: the options cache was introduced in
    75e4065d4db8d1c67a280c4b46e8853fada67561 (2005-04-19, "91716 (fix improvement)").
    The audit follows both JavaCore.java (the former location) and
    JavaModelManager.java (to which the cache moved in 2005), comparing the
    historical commit with its parent. This is source-history evidence, not
    a claim that a historical runtime or every intervening release was tested.
    
    Related: https://github.com/eclipse-jdt/eclipse.jdt.ui/issues/1445
    The tests demonstrate stale formatter options and the missing cast space
    through an actual editor save. They do not reproduce or claim to fix the
    extra space before assignment or the historical MalformedTreeException.
    No UI workaround, diagnostic workflow or generated evidence is included
    in this commit. No upstream pull request is opened.

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
.SAVE_BEFORE race=false persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=12
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
.SAVE_BEFORE race=false persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=12
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

UI_DIAGNOSTIC_RESULT tests=2 failures=1 ignored=0
Sep 05, 2026 8:33:00 AM org.apache.aries.spifly.BaseActivator log
INFO: Registered provider org.slf4j.simple.SimpleServiceProvider of service org.slf4j.spi.SLF4JServiceProvider in bundle slf4j.simple
........
Time: 0.233

OK (8 tests)

NATIVE_RESULT tests=8 failures=0 ignored=0
Sep 05, 2026 8:33:07 AM org.apache.aries.spifly.BaseActivator log
INFO: Registered provider org.slf4j.simple.SimpleServiceProvider of service org.slf4j.spi.SLF4JServiceProvider in bundle slf4j.simple
BUNDLE org.eclipse.jdt.core 3.47.0.v20260813-2102
BUNDLE org.eclipse.text 3.14.800.v20260815-0849
BUNDLE org.eclipse.core.runtime 3.35.0.v20260623-1631
.OPTIONS_RACE writer=JavaCore.setOptions overlapping=do not insert persisted=insert subsequentCached=insert
..FORMATTER_CONTROL: 200 invocations, four workers, fixed source/options
.OPTIONS_RACE writer=preferences.put overlapping=do not insert persisted=insert subsequentCached=insert
..OPTIONS_RACE writer=JavaCore.setOptions overlapping=do not insert persisted=insert subsequentCached=insert

Time: 0.627

OK (6 tests)

DIAGNOSTIC_RESULT tests=6 failures=0 ignored=0
Sep 05, 2026 8:33:14 AM org.apache.aries.spifly.BaseActivator log
INFO: Registered provider org.slf4j.simple.SimpleServiceProvider of service org.slf4j.spi.SLF4JServiceProvider in bundle slf4j.simple

(java:2994): dbind-WARNING **: 08:33:16.902: AT-SPI: Error retrieving accessibility bus address: org.freedesktop.DBus.Error.ServiceUnknown: The name org.a11y.Bus was not provided by any .service files
UI_HARNESS_STARTUP_DISPATCH_COMPLETE
.SAVE_BEFORE race=false persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=12
SAVE_AFTER race=false length=105 stamp=14 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String) o;\n    }\n}
.OPTIONS_RACE writer=JavaCore.setOptions overlapping=do not insert persisted=insert subsequentCached=insert
SAVE_BEFORE race=true persisted=insert cache=insert project=insert bufferType=org.eclipse.jdt.internal.ui.javaeditor.DocumentAdapter length=107 stamp=20
SAVE_AFTER race=true length=105 stamp=22 text=package test1;\npublic class E1 {\n    public void foo( Object o ) {\n        String s = (String) o;\n    }\n}

Time: 1.076

OK (2 tests)

UI_DIAGNOSTIC_RESULT tests=2 failures=0 ignored=0
# Options-cache publication fix: executed validation

| Arm | Test layer | Executed | Failed | Ignored | Logged Eclipse errors |
| --- | --- | ---: | ---: | ---: | ---: |
| stock | native | 8 | 4 | 0 | 0 |
| stock | headless | 6 | 3 | 0 | 0 |
| stock | ui | 2 | 1 | 0 | 0 |
| fixed | native | 8 | 0 | 0 | 0 |
| fixed | headless | 6 | 0 | 0 | 0 |
| fixed | ui | 2 | 0 | 0 | 0 |

Stock fails exactly the four native cache assertions, three original headless assertions and one original editor-save assertion. Fixed passes all 16 tests. No tests were ignored.

Native test source is copied byte-for-byte from the proposed upstream test file. Only JavaModelManager and its nested classes are replaced in the disposable fixed SDK. Other SDK bundles are hash-checked unchanged.

The UI harness registers the standard IDE workspace adapters in both arms. The formatter and editor test assertions are unchanged. This is targeted testing, not a full Tycho/JDT suite run.

The extra space before assignment and historical malformed-edit exceptions of jdt.ui#1445 have not been reproduced or claimed fixed.

```
## Last lines of publication.log
```

    Prevent stale Java options cache publication after concurrent updates
    
    A cold JavaModelManager.getOptions() can read old preference values, then
    publish its map after a concurrent JavaCore.setOptions() has completed or
    a preference event has invalidated the cache. Subsequent non-overlapping
    getOptions() calls then disagree with getOption(). Defensive Hashtable
    copies and the existing volatile reference do not prevent this lost
    invalidation / late-publication race.
    
    Track a cache generation and publish a reader's snapshot only if no
    writer or invalidation has advanced that generation. Coordinate the
    comparison/publication and generation changes under a short private lock.
    Keep all preference reads, writes, listeners, copying and tracing outside
    that lock; retain the cached fast path and defensive-copy semantics.
    An overlapping read may return its snapshot but may not cache it after
    an intervening update. Invalidation advances the generation even when
    the cache is already null, avoiding null-to-null / ABA invalidations.
    
    Route all cache invalidations through the same protocol. End an options
    reset with a generation-advancing invalidation before rebuilding, so a
    partially computed reset snapshot cannot become the post-reset cache.
    
    Add OptionCacheTests to the model suite. Real preference reads are paused
    using bounded CountDownLatch barriers; delegating proxies retain actual
    values and release preference locks before pausing. Cover completed
    setter/reset races, direct and repeated invalidations, cache reuse,
    returned-copy isolation, sequential writes and reentrant preference
    callbacks. Restore settings, lookup nodes and worker threads after tests.
    
    Validation: all eight new native tests, six established headless Core /
    formatter tests and two real JavaEditor.doSave integration tests execute
    against the same pinned Eclipse SDK. Baseline fails exactly eight race
    assertions; the fixed version passes all 16, with no ignored tests or
    logged Eclipse errors. Compile the actual patched upstream
    JavaModelManager source into the disposable SDK; verify that other SDK
    bundles are unchanged. In both arms the minimal UI harness registers IDE
    workspace adapters and excludes the unrelated optional Tips add-on to
    avoid its startup UI racing test-workbench shutdown. No UI product code
    or test assertions are modified. This is targeted validation, not a full
    Tycho or complete JDT regression-suite run.
    Evidence: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33955492150
    Upstream base: 8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51
    SDK: I20260826-2300; JDK 25; Linux GTK x86_64
    SDK SHA-256: 1a81564c817ba6016557f6b75e3c3a31e3d4532f42e8ab8883b74ebcc68ddbce
    The archive matches Eclipse's official HTTPS SHA-512 checksum manifest.
    
    History: the options cache was introduced in
    75e4065d4db8d1c67a280c4b46e8853fada67561 (2005-04-19, "91716 (fix improvement)").
    The audit follows both JavaCore.java (the former location) and
    JavaModelManager.java (to which the cache moved in 2005), comparing the
    historical commit with its parent. This is source-history evidence, not
    a claim that a historical runtime or every intervening release was tested.
    
    Related: https://github.com/eclipse-jdt/eclipse.jdt.ui/issues/1445
    The tests demonstrate stale formatter options and the missing cast space
    through an actual editor save. They do not reproduce or claim to fix the
    extra space before assignment or the historical MalformedTreeException.
    No UI workaround, diagnostic workflow or generated evidence is included
    in this commit. No upstream pull request is opened.
```
