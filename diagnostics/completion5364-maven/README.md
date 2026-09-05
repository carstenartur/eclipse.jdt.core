# Source-built Maven tracing for PR 5364

This diagnostic branch is separate from `fix/options-cache-publication-race`.
No production source changes or adjusted test expectations are committed here.
The workflow creates disposable instrumented checkouts for three pinned revisions:
upstream `8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51`, the generation fix
`db389f7e72f88da5ded1debd337956b960fc3711`, and both fixes at
`d55a8c72e96ba601562fda02e5698da6323d37e7`.

## Execution

`.github/workflows/completion-5364-maven.yml` runs each revision on GitHub-hosted
Ubuntu 24.04 with model-test JVMs 21 and 25. It bootstraps ECJ and builds the
required Maven reactor projects from source, rather than replacing classes in a
prebuilt SDK. It then runs the original test pair, full class and ordered
predecessor completion chain in separate Tycho JVMs and fresh workspaces.

Four processes per matrix cell: pair with tracing disabled; pair with tracing
enabled; full class with tracing; predecessor chain with tracing. The expected
JUnit counts, actual test JVM, target-test execution, exit status, XML results
and presence of diagnostic output are checked explicitly. The separate existing
standalone test execution is retained. Missing/zero tests cannot pass validation.
This is a targeted source build, not a full repository regression-suite run.

## What is observed

Only the target Enum and related Record test activate a bounded thread-local
buffer. The probes record actual CompletionEngine settings, existing name-lookup
roots, original source, index/model path, candidates, rejection sites, swallowed
exceptions and proposals actually delivered to the original requestor. No extra
JavaCore.getOptions(), findType(), model warmup or index search is performed.
The original requestor is called exactly once. Console output is deferred until
the test and its teardown finish. The generated patch and source hashes are
retained with the evidence.

Even buffered tracing can change timings. The trace-disabled control still has
dormant hooks in its binary, so it is not an uninstrumented-binary control. A
successful comparison does not prove absence of the intermittent defect or
replicate the unobserved state of the failed Eclipse Jenkins process.

Only this diagnostic branch excludes its ordinary duplicate full CI run; the
PR branch and its workflow are not changed. The diagnostic workflow has read-only
repository permissions, uploads evidence, and never commits product fixes.

Results have not been assumed in advance. Inspect each run's artifacts and exact
`summary.json` before drawing conclusions or claiming success.
