# PR 5364: executed source-built Maven completion comparison

Recorded **2026-09-05**. [Completed run 33974044071](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33974044071), workflow **Completion 5364 Maven tracing**, diagnostic revision `f382b50d343815dbb12c45eff8172a7f0c65b2ab`.

## Result and limits

All six matrix cells completed successfully. All selected JUnit tests passed, with no skipped tests. The original missing-Enum failure did **not** reproduce. The observations supply no evidence that either cache fix removes a valid completion proposal or requires a different test expectation.

This is now a Maven/Tycho build of the relevant repository sources, rather than the earlier experiment that replaced selected classes in a prebuilt SDK. It remains a targeted comparison, not an exact replay of the failed Jenkins process and not a complete repository test-suite run.

The existing PR branch `fix/options-cache-publication-race` was not changed. Its two fixes remain at `d55a8c72e96ba601562fda02e5698da6323d37e7`. The upstream Jenkins #2 check was still red when checked after this experiment. A successful independent workflow does not turn that check green or establish the precise cause of its historical failure.

## Compared revisions and actual test JVMs

| Arm | Pinned repository revision | Model-test Java 21 | Model-test Java 25 |
| --- | --- | --- | --- |
| base | `8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51` | 2,025 completion executions; all pass | 2,025 completion executions; all pass |
| generation | `db389f7e72f88da5ded1debd337956b960fc3711` | 2,025 completion executions; all pass | 2,025 completion executions; all pass |
| lifecycle | `d55a8c72e96ba601562fda02e5698da6323d37e7` | 2,025 completion executions; all pass | 2,025 completion executions; all pass |

Actual model-test JVM versions, recorded inside the test process: **21.0.12.1** and **25.0.4.1**. Maven runs on Java 25 in both configurations. The model POM's selected toolchain is changed for the Java-25 cells, and the reporting gate verifies the actual test JVM rather than inferring it from JAVA_HOME.

Each cell runs four separate Tycho JVMs with fresh workspaces:

| Scenario | Selected original completion tests | Tracing |
| --- | ---: | --- |
| Original test001/test002 pair | 2 | off |
| Same original pair | 2 | on |
| Complete CompletionTests16_2 class | 22 | on |
| Original completion predecessor chain through CompletionTests16_2 | 1,999 | on |
| **Per cell** | **2,025** | |

Across the six cells this is **12,150 completion-test executions**. The existing separate `JavaCoreStandaloneTest` execution also passes once for each of the 24 Maven verify invocations, giving **12,174 individual XML testcase elements** overall. These counts include repeated methods; they are not counts of distinct regression tests. The specific `CompletionTests16_2.test002` target executes **24 times**, including **18 traced executions**. The related `CompletionTests16.testBug564828_2` executes and is traced in each of the six predecessor-chain runs.

Both the explicit JUnit result markers and the individual XML elements were checked. All 24 verify process exit codes are zero; no failure/error/skipped elements are present. The counts are not inferred from aggregate XML headers.

## What is now observed inside completion

For each corresponding scenario and target, the complete captured event sequence is **byte-identical across all six cells**, including the actual settings map passed to the `CompletionEngine` constructor. This is stronger than the earlier snapshots taken before an individual test's setup.

The Enum proposal consistently follows this path:

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

The index finds the type, the engine accepts and queues it, and both the type and keyword proposals reach the original requestor. No type rejection is recorded for Enum in these executions. The test input and expected proposals remain unchanged.

For the related Record case the trace likewise shows both the local-variable proposal and the indexed `java.lang.Record` type delivered. The logged `CompletionNodeFound` exception is part of the engine's normal completion control flow, not a newly discovered failure.

### Test-order differences that are not PR differences

The isolated target and the target after the predecessor chain do have three different compiler-warning settings: `unusedPrivateMember`, `typeParameterHiding` and `unusedLocal` are `ignore` in the isolated scenario and `warning` after the chain. Each difference is identical in base, generation and lifecycle, on both JVMs. Both scenarios return the expected proposals. This is not evidence of newly effective settings caused by our PR.

The trace also identifies the test library as `jclMin14.jar`, along with the original Completion project roots. Thus changing the host JVM is not the same thing as changing the test's Java library to the host JDK. Both host-JVM configurations still exercise the original test fixture and Java-16 source/compliance settings.

## Build and instrumentation provenance

The workflow checks out each pinned revision independently, bootstraps ECJ from it, and runs:

```text
mvn clean install -f org.eclipse.jdt.core.compiler.batch -DlocalEcjVersion=99.99
mvn ... clean install -DskipTests -pl org.eclipse.jdt.core.tests.model -am
mvn ... verify -pl org.eclipse.jdt.core.tests.model -Dtycho.surefire.argLine=...
```

The reactor build includes JDT Core, the compiler batch bundle, the model tests and their required reactor dependencies. Platform and other external dependencies still come from the Maven/Tycho target repositories. This is not a claim that every Eclipse dependency was rebuilt from source or that mutable upstream snapshot repositories were frozen indefinitely.

Identical generated hooks are applied to `CompletionEngine`, `SearchableEnvironment` and `NameLookup`. A diagnostic-only suite wrapper selects the original test suites, without changing their bodies, expected results, or per-test setup/teardown. It is not the original Jenkins `TracingSuite` wrapper.

The hooks capture already-used data: actual engine settings, original source, existing lookup roots, chosen search path, candidate handling and actual proposal delivery. They do not call additional `JavaCore.getOptions()`, `findType()` or index searches. Trace strings are buffered in a bounded thread-local list and printed after the target test's teardown. The original completion requestor is called exactly once per delivery.

Tracing can still affect timing and scheduling. The trace-off control contains dormant hooks in its compiled binary; it is **not** an uninstrumented-binary control. A passing run is not a proof of absence of an intermittent defect.

The SHA-256 of the original `CompletionTests16_2.java` is the same in every cell:

```text
798b16ce5b1a232b9b116ba1dbaef3f7d285897ec1e4ca36881d3aaa7e38f25a
```

Artifacts include the generated instrumentation diff, source hash manifest, actual runtime configuration, full Maven logs, JUnit XML, trace events and workspace logs.

## Log and harness caveats

The initial reporting field `eclipse_error_entries` counted only entries copied into the Maven console. It is zero in the archived summaries, but **does not mean the workspace logs are error-free**. Direct inspection of all 24 archived workspace logs finds exactly three ERROR entries in each predecessor-chain run, from `CompletionTests2.testBug281598` and `testBug281598b` opening their deliberately empty `empty.jar`. All other scenarios contain no workspace ERROR entries. These 18 entries are preserved in the artifacts and are not completion-target failures.

The follow-up reporting change separates console and workspace counts and retains each workspace error's message and originating test frames. The parser was tested against all 24 archived scenario logs. That change is reporting-only; it does not change the Java instrumentation or retroactively rewrite the original run artifacts. Workspaces also log their unsaved-changes shutdown warning. The builds contain warnings, including four unqualified-field-access warnings in the diagnostic wrapper; no compiler errors occurred.

Two earlier calibration attempts are excluded from the results. A null-unsafe rendering of absent keyword signatures was corrected in the diagnostic helper before any actual test result was counted. A generated POM line inherited mixed spaces/tabs and initially failed `git diff --check`; only its generated indentation was normalized. Those setup issues were not product regressions.

## Evidence artifacts

All six downloaded artifact archive digests were verified locally against the digests returned by GitHub:

| Arm / JVM | Artifact ID | Archive SHA-256 |
| --- | ---: | --- |
| base / 21 | 9971842699 | `7086ee5be1456765d2db3f9d4c40df448021a9a3fa467d76e29260847dd4d09a` |
| generation / 21 | 9971849168 | `b89ff18f0a5e57a321a1857a8ea612da13b965dbe709f539bab348d1551614d3` |
| lifecycle / 21 | 9971866769 | `3640facf9361ecfc5e5756936a7a90c45272242392cf1af161c98532ca187b72` |
| base / 25 | 9971867035 | `7bc2d4c2e29e8fa1e69f48bb674ba09c17d2fe6810f93f93b1b3687b0f171f0e` |
| generation / 25 | 9971857285 | `c5bc37e261c01f7b0208b0c640858ca40ac05396bc63a7c66e3b1f723397d3be` |
| lifecycle / 25 | 9971867796 | `eff6474e5e00fe639246e3dc37feea3e99f146960e40266a7193f681e0e17e1b` |

The artifacts are attached to [run 33974044071](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33974044071) and have finite retention. These are validation artifacts, not a release.

## Interpretation for PR 5364

The experiment does not support weakening the original Enum expectation. Neither the generation fix nor the listener-lifecycle fix changed the actual completion options, observed candidate processing or delivered proposals in these scenarios.

The remaining Jenkins failure signature already exists in [Core issue #3230](https://github.com/eclipse-jdt/eclipse.jdt.core/issues/3230). This experiment adds an independently executable instrumented Maven comparison, but it still does not identify the precise failing Jenkins interleaving. A run that actually loses the proposal is needed to compare the first divergent event. More passing unrelated tests alone cannot supply that missing evidence.

No additional product fix is claimed or committed as a consequence of this comparison. PR 5364 and its original expectations remain unchanged.
