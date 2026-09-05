# PR 5364: investigation of the remaining completion failure

Recorded 2026-09-05. PR head examined: `d55a8c72e96ba601562fda02e5698da6323d37e7`.

## Conclusion

The remaining Jenkins #2 failure, `CompletionTests16_2.test002()`, has the same missing-`Enum` failure signature as [JDT Core issue #3230](https://github.com/eclipse-jdt/eclipse.jdt.core/issues/3230), opened on **4 November 2024** for build **I20241030-1630**, long before this PR.

The historical report establishes that this failure signature was not introduced by PR 5364. It does not establish the exact trigger in this particular Jenkins run, exclude an effect of our changes on timing/frequency, or prove that every occurrence has the same underlying cause.

The executed controlled comparisons below found no completion regression attributable to the options-cache changes. They did **not** reproduce the missing proposal. No test expectation or PR production file was changed during this investigation.

## What failed in Jenkins

[PR 5364](https://github.com/eclipse-jdt/eclipse.jdt.core/pull/5364), [Jenkins run #2](https://ci.eclipse.org/jdt/job/eclipse.jdt.core-Github/job/PR-5364/2/), [published test check](https://github.com/eclipse-jdt/eclipse.jdt.core/runs/101301160284).

Expected:

```text
Enum[TYPE_REF]{Enum, java.lang, Ljava.lang.Enum;, null, null, 44}
enum[KEYWORD]{enum, null, null, enum, null, 49}
```

Actual:

```text
enum[KEYWORD]{enum, null, null, enum, null, 49}
```

This is the same test and the same expected/actual difference as the original #3230 report, not just another generic completion failure. Subsequent #3230 comments also document a related missing `Record` type proposal while a local-variable proposal remains, in builds I20260320-1800 and I20260826-2300; those are a related symptom, not the identical test.

The five `OptionCacheTests` failures from Jenkins #1 were a different, already reproduced problem: preference-node replacement lost the cache-invalidation listener. Commit `d55a8c72e96ba601562fda02e5698da6323d37e7` repairs that lifecycle. Jenkins #2 no longer reports those five failures.

## Executed controlled comparison

[Completed Actions run 33968209895](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33968209895).

Diagnostic revision: `ba10cfe88f081825a62cc40a11d23c3438d0d6f6`.

Two disposable copies of Eclipse SDK I20260826-2300 were prepared with the same automated-test bundles and the same test sources. Both arms recompile `JavaModelManager` with the same compiler and packaging procedure:

- **base**: the class from upstream `8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51`;
- **pr**: the class from PR head `d55a8c72e96ba601562fda02e5698da6323d37e7`, including both cache corrections.

The original current `CompletionTests16_2`, `CompletionTests16_1`, `AbstractJavaModelCompletionTests`, `AbstractJavaModelTests` and `CompletionTestsRequestor2` sources are compiled identically into each test runtime. Test inputs and expected proposals are unchanged. Other test classes and SDK dependencies come from the pinned automated-tests archive; this is not a full rebuild of both repository revisions.

Each scenario executes in a separate JVM and workspace.

| Scenario | Tests per arm | Base failures | PR failures |
| --- | ---: | ---: | ---: |
| Original test001/test002 pair, fresh process 1 | 2 | 0 | 0 |
| Original test001/test002 pair, fresh process 2 | 2 | 0 | 0 |
| Original test001/test002 pair, fresh process 3 | 2 | 0 | 0 |
| Complete original CompletionTests16_2 class | 22 | 0 | 0 |
| CompletionTests16_1 followed by test001/test002 using the shared project | 12 | 0 | 0 |
| Original pair with IndexManager disabled around test002 | 2 | 0 | 0 |
| Preceding completion-suite chain through CompletionTests16_2 | 1,999 | 0 | 0 |
| **Total executions** | **2,041** | **0** | **0** |

All seven processes in each arm exited with status 0. No JUnit tests were ignored. Totals count repeated executions, not 2,041 distinct test methods. The target test executed seven times per arm, with its original assertion intact.

The indexing-disabled scenario is a probe of the non-indexed search behavior, not a reproduction of an unknown Jenkins index state. It also passed in both arms.

### State comparison

For `test002`, a JUnit test-start listener recorded sorted global options, sorted inherited project options, the resolved classpath and pending index-job count. These snapshots are taken at test-start, before the individual test's `setUp()`, not at every internal formatter/completion lookup.

For all seven corresponding scenario pairs:

- the serialized global options match exactly;
- the serialized inherited project options match exactly;
- the resolved classpaths match exactly;
- the recorded pending index-job count is 0 in both arms, before the deliberate disable operation where applicable.

This supplies no evidence for an expectation change justified by newly effective options in these scenarios. It does not describe the unobserved state inside the failed Jenkins invocation.

### Runtime and source provenance

Runtime: Temurin Java 25.0.4.1, Linux GTK x86_64; SDK Core bundle version 3.47.0.v20260813-2102, with the designated manager class and its nested classes replaced in each arm.

```text
SDK archive SHA-256:
1a81564c817ba6016557f6b75e3c3a31e3d4532f42e8ab8883b74ebcc68ddbce
Automated-tests archive SHA-256:
c0d56a10ac060f5dc4d917fe7836aa09143ac559bc445e3b987b5f9e2ad8bd0d
CompletionTests16_2.java SHA-256 in both arms:
798b16ce5b1a232b9b116ba1dbaef3f7d285897ec1e4ca36881d3aaa7e38f25a
```

The test-source hash manifests match byte-for-byte. Artifacts contain preparation logs, scenario outputs, exit statuses, source hashes and workspace data:

- [Base evidence, artifact 9970134259](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33968209895/artifacts/9970134259), archive SHA-256 `f70387957b9378ecbec58d4cb7fcaeb211643ea7aaf06e97dc97aa2d11a0d762`.
- [PR evidence, artifact 9970133800](https://github.com/carstenartur/eclipse.jdt.core/actions/runs/33968209895/artifacts/9970133800), archive SHA-256 `e5d99873887f2691c7b17935118e7b493e0d8d3833dca44462af0db55b61dec3`.

### Limitations and runner errors

These are successful **JUnit assertions**, not an error-free Eclipse application launch. Installing the broad automated-tests archive also installs an unrelated `org.eclipse.equinox.http.servlet.tests` bundle that cannot resolve its `org.apache.commons.fileupload` dependency. Each scenario logs that framework error in both arms. The completion chain additionally logs empty-ZIP errors from `CompletionTests2.testBug281598`/`testBug281598b` (three in base, two in PR). All selected JDT tests nevertheless execute and pass; the evidence preserves those messages rather than suppressing them.

An earlier calibration run, 33967961497, incorrectly repeated test scenario IDs in one JVM; Eclipse's performance framework rejects that. Those setup failures were diagnostic-runner errors, not completion failures. The reported comparison uses separate processes and does not count that calibration run.

Direct access to the original Jenkins console and detailed build API returned HTTP 403. The Jenkins failure assessment therefore relies on its GitHub-published check output, not a retrieved full Jenkins trace. No complete upstream Tycho/JDT suite rerun, failure-frequency measurement, or exact replay of the Jenkins process state has been performed here.

## PR handling

Keep the `Enum` expectation and the cache fix unchanged on the present evidence. The remaining red check is consistent with a pre-existing intermittent completion failure tracked in #3230. A Jenkins rerun and a reference to #3230 are justified; marking the PR successful or claiming the precise completion root cause has been fixed is not.

Only `diagnostic/completion-5364` was changed for this investigation. No diagnostic workflows or files were added to `fix/options-cache-publication-race`, and no empty PR commit was created to force a rebuild.
