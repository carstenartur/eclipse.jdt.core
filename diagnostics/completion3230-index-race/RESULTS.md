# Missing Enum completion: acquired-index deletion reproduction

Recorded **2026-09-05**. This report concerns the remaining `CompletionTests16_2.test002()` failure in [PR 5364](https://github.com/eclipse-jdt/eclipse.jdt.core/pull/5364), with the historical signature tracked in [Core issue #3230](https://github.com/eclipse-jdt/eclipse.jdt.core/issues/3230).

## What has now been demonstrated

**The original test's exact missing-Enum assertion can be reproduced on both upstream and PR code by deleting its already-acquired library search index before that index is queried.** The operation uses the real `IndexManager.removeIndex()` on another thread. The original completion test source, expected proposals, current options, project classpath and Java library are not changed by the experiment.

The actual underlying failure in this reproduction is not option selection or an incorrectly expected type. `PatternSearchJob.search()` silently treats an index that has been deleted since acquisition as successfully searched. Its type matches are lost, while the keyword proposal remains.

A diagnostic counterfactual that cancels this incomplete index search activates the existing model-search fallback and restores the expected Enum proposal under exactly the same index-removal ordering.

**This proves a concrete independent mechanism for the identical failure signature. It does not prove that the failed Jenkins process encountered precisely this interleaving.** The original Jenkins log available through GitHub contains the assertion, not the index lifecycle events needed to establish that historical cause. No spontaneous failure frequency or effect of the options fixes on timing has been measured.

## Executed experiment

[Completed Actions run 33977652458](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977652458), workflow **Completion 3230 acquired-index race**.

Diagnostic execution revision: `2cf85c03e214a6004484cd67cad66172005cf0eb` on `diagnostic/completion-3230-index-race`.

Both arms are built from source with Maven/Tycho, using the same instrumentation and runtime selection:

| Arm | JavaModelManager and other source revision |
| --- | --- |
| base | Upstream `8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51`, without either options fix |
| pr | `d55a8c72e96ba601562fda02e5698da6323d37e7`, with both options fixes |

Each scenario uses a separate test JVM and a fresh workspace. The actual model-test JVM, verified inside the test and in its XML properties, is **Temurin 25.0.4.1**. The original fixture uses `jclMin14.jar` with Java-16 source/compliance settings; changing the host JVM does not replace this fixture with the host JDK library.

| Scenario | Original tests per arm | Base JUnit failures | PR JUnit failures | Enum proposal |
| --- | ---: | ---: | ---: | --- |
| Control: no index deletion | 2 | 0 | 0 | Present |
| Real deletion after index acquisition | 2 | 1 | 1 | Missing; only enum keyword remains |
| Same deletion, cancel incomplete search to invoke existing fallback | 2 | 0 | 0 | Present again |

The failed test in both negative cases is the original `test002`, with the exact expected/actual difference from Jenkins and #3230. All six cases execute both original tests; none is ignored. Maven exits 1 for each negative case and 0 for the four passing cases. The separate `JavaCoreStandaloneTest` also executes and passes in the four successful verify invocations; Maven does not reach that later execution in the intentionally failing invocations. There are 12 original completion-test executions and four additional standalone executions, not 16 distinct tests.

**The two workflow jobs are green because their diagnostic assertions require precisely this pass/fail/pass pattern. Green does not mean that the negative JUnit tests passed.** Startup failures, compiler failures, missing traces, timeouts, skipped tests or a different test failure cannot satisfy those checks.

All six archived workspace logs were inspected directly and contain **zero Eclipse ERROR entries**. They still contain workspace shutdown warnings. Builds may emit compiler/build warnings; an absence of ERROR entries is not a claim of warning-free output.

## Exact mechanism and controlled ordering

The relevant upstream implementation in `PatternSearchJob.search()` is:

```java
ReadWriteMonitor monitor = index.monitor;
if (monitor == null) return COMPLETE; // index got deleted since acquired
```

`IndexManager.removeIndex()` sets the cached index's `monitor` to null, deletes/removes the index and updates its metadata. A caller that already holds the previous `Index` object can therefore enter the branch above. Its result is classified as complete rather than as requiring a retry or another search path.

The diagnostic scheduling point is immediately after `PatternSearchJob.execute()` obtains its `Index[]`. It acts only during the original target completion, for its `enu` type-declaration search, and requires exactly one acquired `jclMin14.jar` index with a non-null monitor.

A separate daemon worker then calls the real `IndexManager.removeIndex(new Path(index.containerPath))`. The search thread waits on the worker's bounded Future before continuing, ensuring that the deletion has completed. The probe checks that the previously acquired index now has a null monitor. It neither sets that field itself nor fabricates an index, search result or preference value. This deliberately schedules one allowed sequence; it is not an observation of the natural Jenkins thread schedule.

Normal product paths such as classpath-change processing also call `IndexManager.removeIndex()`. Their existence makes index invalidation a meaningful lifecycle condition, but it does not identify the writer in the historical failing Jenkins invocation.

The negative case yields exactly:

```text
----------- Expected ------------
Enum[TYPE_REF]{Enum, java.lang, Ljava.lang.Enum;, null, null, 44}\n
enum[KEYWORD]{enum, null, null, enum, null, 49}
------------ but was ------------
enum[KEYWORD]{enum, null, null, enum, null, 49}
```

## Where the successful and failing traces diverge

The complete corresponding trace streams are byte-identical between the upstream and PR arms. The actual `CompletionEngine` settings map also matches across all three scenarios in both arms.

Normal case:

```text
SEARCH prefix=enu rule=129 filter=0 monitor=false
SEARCH_PATH INDEX
INDEX_CANDIDATE java.lang.Enum flags=1057
ENGINE_CANDIDATE java.lang.Enum flags=1057
ENGINE_QUEUED Enum
PROPOSE_TYPE java.lang.Enum
DELIVER kind=9 completion=Enum signature=Ljava.lang.Enum; relevance=44
DELIVER kind=3 completion=enum signature=null relevance=49
```

After real index deletion:

```text
INDEX_RACE_ACQUIRED .../jclMin14.jar
INDEX_RACE_REMOVED .../jclMin14.jar oldMonitorNull=true
```

The subsequent buffered completion trace contains:

```text
SEARCH prefix=enu rule=129 filter=0 monitor=false
SEARCH_PATH INDEX
DELIVER kind=3 completion=enum signature=null relevance=49
```

There is no Enum candidate passed from index search to the engine. This is a missing search result, not a type candidate subsequently rejected by option-dependent engine filtering.

## Causal counterfactual, not a production fix

In the third scenario, only this additional product-source intervention is made in the disposable build:

```diff
-if (monitor == null) return COMPLETE; // index got deleted since acquired
+if (monitor == null) throw new OperationCanceledException(); // diagnostic causal control
```

For the tested completion call, whose progress monitor is null, `SearchableEnvironment.findTypes()` already catches a canceled index search and falls back to searching the Java model. The real index deletion is unchanged. The trace now shows:

```text
SEARCH_PATH INDEX
CAUGHT_L796 org.eclipse.core.runtime.OperationCanceledException
SEARCH_PATH MODEL prefix=enu filter=16777246
MODEL_BINARY enu flags=16777246
MODEL_CHILDREN 27
MODEL_ACCEPT Enum
ENGINE_CANDIDATE java.lang.Enum flags=1025
ENGINE_QUEUED Enum
PROPOSE_TYPE java.lang.Enum
DELIVER kind=9 completion=Enum signature=Ljava.lang.Enum; relevance=44
DELIVER kind=3 completion=enum signature=null relevance=49
```

The unchanged original test passes. The differing model/index modifier encodings do not change the delivered proposal or expected relevance in this case.

This one-line intervention is **not a proposed general search fix**. Other search consumers, monitor-bearing completions, parallel execution, genuine user cancellation and partially delivered results need separate design and regression tests. A production solution must decide whether and how to retry or fall back without conflating user cancellation, returning incomplete results as complete, or duplicating previously delivered proposals.

## Provenance and reproducibility

Source files are checked out at the pinned revisions above. ECJ, JDT Core and required reactor dependencies are source-built via Maven; external target dependencies still come from Maven/Tycho repositories. This is not a rebuild of every Eclipse dependency or an exact Jenkins environment replica.

The original `CompletionTests16_2.java` is byte-for-byte equal to its checked-out source in every scenario. Its SHA-256 is:

```text
798b16ce5b1a232b9b116ba1dbaef3f7d285897ec1e4ca36881d3aaa7e38f25a
```

The diagnostic wrapper selects the original `test001`/`test002` suite and retains its original setup, teardown, source and assertions. Hooks capture existing data and buffer in-engine traces. Instrumentation changes timing; the experiment establishes this scheduled mechanism, not a natural failure probability.

The ordinary `CompletionNodeFound` entry in all traces is normal completion control flow, not the failure cause.

Artifacts contain original XML, full Maven logs, actual test runtime, source hash records, generated instrumentation and counterfactual diffs, proposal traces and workspace logs. Both downloaded archive hashes match the GitHub-returned artifact digests:

| Arm | Artifact | ZIP SHA-256 |
| --- | --- | --- |
| base | [9972876576](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977652458/artifacts/9972876576) | `49523065b43f6680a21799274a08950bbd5ebd23bb60c58c18c289ac8bae28dd` |
| pr | [9972877629](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977652458/artifacts/9972877629) | `26c36b7268c8f526788bdc5bb599cc3e540ded9d2f209aee77ebfdf66acb7141` |

## Consequence for PR 5364

The missing-Enum behavior can occur independently of either options-cache fix and with identical actual engine options. This provides a concrete reproduced search-lifecycle explanation, stronger than merely noting the old #3230 signature or accumulating passing tests.

It remains necessary to capture the corresponding index event in a naturally failing run, or replay the responsible ordinary lifecycle operation, before claiming the exact historical Jenkins cause. Nothing here supports removing Enum from the test expectation.

No production fix, weaker assertion, diagnostic helper or workflow from this experiment has been added to `fix/options-cache-publication-race`. The Core cache PR remains unchanged. A separate full-original-suite comparison is tracked by [run 33977359605](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977359605); its results are not inferred from this targeted experiment.
