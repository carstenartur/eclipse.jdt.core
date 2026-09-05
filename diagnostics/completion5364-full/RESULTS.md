# PR 5364: full original model-suite comparison

Recorded **2026-09-05**. [Completed run 33977359605](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977359605), workflow **Completion 5364 full original suite**.

Diagnostic execution revision: `9a0d1518341caa066a8157c6c21ed9279e413c2a` on `diagnostic/completion-5364-full`.

## Result

All four Maven jobs completed successfully. Both the original `CompletionTests16_2.test002()` and the related `CompletionTests16.testBug564828_2()` pass in every cell. Both PR cells also execute and pass all ten `OptionCacheTests`.

This comparison closes two limitations of the previous targeted experiment: it includes a **true pristine-Java-source control** and uses the **original complete `RunAllJdtModelTestsTracing` entry point**, including its formatter, DOM and Java-model suites. It does not replace that runner with the earlier diagnostic subset wrapper.

| Code | Diagnostic hooks | Original comprehensive-suite testcase elements | Additional standalone testcase | Failures | Skipped |
| --- | --- | ---: | ---: | ---: | ---: |
| Upstream base | None | 25,074 | 1 | 0 | 0 |
| Upstream base | Target-scoped tracing | 25,074 | 1 | 0 | 0 |
| Both PR fixes | None | 25,084 | 1 | 0 | 0 |
| Both PR fixes | Target-scoped tracing | 25,084 | 1 | 0 | 0 |

The difference of ten tests is exactly the PR's new `OptionCacheTests`. Totals are **100,316 comprehensive-suite test executions plus four standalone executions**. These are repeated executions across controls, not counts of distinct tests. Actual XML child elements, their failure/error/skipped elements and process exits were inspected; aggregate XML header counts were not used.

The missing-Enum failure does not arise spontaneously in these four full-suite runs. This cannot establish that an intermittent failure never occurs or that the original Jenkins failure was caused by a particular schedule.

## Code and runtime controls

The source revisions are pinned:

- base: `8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51`;
- pr: `d55a8c72e96ba601562fda02e5698da6323d37e7`.

All four actual model-test JVMs report **Temurin 25.0.4.1** on Linux. Maven is also started on Java 25. The model test POM's selected toolchain is explicitly set to Java 25 and its original suite selector is retained. Dependencies are resolved via the existing Maven/Tycho target configuration; the experiment does not claim a byte-identical external dependency set to the original Jenkins installation.

In pristine cells, the before/after hash manifest for **every tracked Java source** is identical. No tracing helper or diagnostic test wrapper is added. The only generated POM adjustment selects the test JVM. This is a stronger control than merely switching logging off in an instrumented binary.

In traced cells, three existing product files contain the same buffered in-engine hooks used in the earlier experiment: `CompletionEngine`, `SearchableEnvironment`, and `NameLookup`. Each of the two original target methods is bracketed by trace begin/end in a try/finally. Its original body is retained literally, including the test source, API calls and expected results. Original setup/teardown and the original TracingSuite remain in place. A bounded thread-local trace helper is generated; the subset-selection wrapper is not compiled or executed.

Tracing starts inside the original target method and is flushed at its end, before that method's teardown. This is not the same instrumentation scope as the earlier subset wrapper, which started before individual setup and flushed after teardown. The pristine cells independently test the no-hook case.

The script checks the exact list of modified Java files and rejects unexpected modifications. Source manifests, generated diffs and full build logs are retained with each artifact.

## Observed target traces

The complete **81-event captured stream** for the two targets is byte-identical between the traced upstream and PR cells, including actual options received by `CompletionEngine` and candidate delivery. In both arms, the index finds `java.lang.Enum`, the engine queues it, and it is delivered with relevance 44, followed by the `enum` keyword with relevance 49.

The original test targets are identified by their fully qualified class/method names in the original TracingSuite XML output, not by the ambiguous name `test002` alone. Both target entries occur exactly once per run, with no failure/error/skipped child.

All ten cache-test names are present and passing in each PR XML, including `testInstanceNodeRemovalInvalidatesCache` and `testInstanceNodeReplacementKeepsInvalidatingCache`. None is present in the upstream source, as expected.

## Workspace logs are not error-free

Passing JUnit assertions must not be confused with an error-free Eclipse workspace log. Direct inspection finds **32 ERROR entries in each upstream cell and 31 in each PR cell**. All four contain the same set of 20 distinct message strings; the one-entry difference is a repeated invalid-user-library decoding message. Traced and pristine variants within each code arm have the same message counts.

Messages include deliberately malformed ZIP archives, missing resources, invalid user-library data, task-tag inconsistencies and other error-path tests. The complete entries and their stacks are preserved in `summary.json` and the archived workspace logs. No new ERROR message category appears in the PR runs. This report does not treat all ERROR entries as harmless merely because tests passed, nor claim that the log-count difference is a measured improvement from the cache fix.

## Evidence

The four downloaded ZIP digests match the digests returned by GitHub:

| Arm / hooks | Artifact | SHA-256 |
| --- | --- | --- |
| base / pristine | [9972889755](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977359605/artifacts/9972889755) | `cffd5959be59bb0c4f6a15dd0706737a405d61226094ad167eea73bb5fe60607` |
| base / traced | [9972889904](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977359605/artifacts/9972889904) | `67faaef856894b3f4b161b87a328079d842a4c786e94820f78abdb0db95131e3` |
| pr / pristine | [9972887840](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977359605/artifacts/9972887840) | `b971b488619fd7c786e3c697e37d4bc784ab7c81c67fd635ad902c82a26a2b28` |
| pr / traced | [9972911981](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977359605/artifacts/9972911981) | `19a234924bd46942ad5276d90cf94d9b03a380fa8ef11750f1059147059584f8` |

Each artifact retains bootstrap and reactor logs, the complete verify log, original JUnit XML, runtime properties, source manifests, target traces and workspace logs. Three local Python tooling tests also checked the source bracketing and report parser against an existing real report, including rejection of a wrong JVM and of a synthetic failed XML child despite a successful process code. These tooling checks are not additional Java test executions.

## Relationship to the reproduced acquired-index defect

A separate [completed acquired-index experiment, run 33977652458](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33977652458), does reproduce the exact missing-Enum assertion in the original test, on both upstream and PR code. It removes the actual library index after search acquisition and before query execution; the unchanged search treats the removed index as complete. A diagnostic cancellation counterfactual activates the existing model fallback and restores the proposal. Actual engine options remain identical.

See the [acquired-index report](https://github.com/carstenartur/eclipse.jdt.core/blob/72c09a5b32af3c88cefe39b09723047e9bb02801/diagnostics/completion3230-index-race/RESULTS.md) for the controlled ordering, exact traces and limits.

The full-suite controls provide additional regression evidence for the cache PR; the acquired-index experiment supplies a concrete independent mechanism for the historical failure signature. Neither establishes the original Jenkins thread schedule. A production-quality search fix requires separate design and regression coverage, rather than adding the diagnostic one-line cancellation probe to the cache PR.

## PR handling

The product branch remains `fix/options-cache-publication-race` at `d55a8c72e96ba601562fda02e5698da6323d37e7`. No original expectation was weakened, no test was disabled, and no diagnostic source was added to PR 5364.

The independently successful runs do not change the historical red Jenkins #2 check. This comparison covers the complete original entry point of the **model-test module**, not every test module in the repository or every platform/JDK combination.
