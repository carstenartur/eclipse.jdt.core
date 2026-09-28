# Verified class-file buffer publication race

Investigation date: 2026-09-28.

## Result

A concurrent ordinary class-file `getSource()` can return `null` while a newly allocated source buffer has already been inserted into the buffer cache but has not yet received its contents. The controlled experiment reproduced this with unchanged upstream production sources, an existing source attachment, no JAR replacement, and no editor.

The buffer was not closed. Once initialization resumed, both the publishing call and a subsequent source lookup returned the complete expected source.

This establishes the narrow publication-order defect below. It does not establish the cause of a particular historical JDT UI I-build failure.

## Immutable inputs and execution evidence

- Upstream production revision: `bb43114e42b4b4d8222d86fbcac45ca6b19a0972`.
- Tested diagnostic revision: `597c9852e793f0ade0be68e5445611601bee59be`.
- Test source was first added in `089097491f973be95f04a26ac01191ba85c34f56` and remained unchanged in the two subsequent test-environment commits.
- Runtime recorded in Surefire XML: Eclipse Adoptium Java `25.0.4.1`, Linux amd64, Tycho headless OSGi test application.
- Workflow: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/36450057727
- Job: https://github.com/carstenartur/eclipse.jdt.core/actions/runs/36450057727/job/109022208211
- Artifact: `buffer-publication-evidence`, artifact ID `10983450941`.
- Artifact SHA-256 reported by GitHub: `21e2bb49f10fea958ecd8425121737296d09e53e704ec83fbe7d698a133f5803`.
- Test source: https://github.com/carstenartur/eclipse.jdt.core/blob/597c9852e793f0ade0be68e5445611601bee59be/org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/BufferPublicationTests.java
- Workflow source: https://github.com/carstenartur/eclipse.jdt.core/blob/597c9852e793f0ade0be68e5445611601bee59be/.github/workflows/ci.yml

The workflow checks `git diff --exit-code` against the upstream revision for `org.eclipse.jdt.core/` before building. A separate comparison of the tested diagnostic revision against upstream shows only the diagnostic test class and the branch-specific workflow as changed files. The model-test POM is adapted only in the temporary CI checkout, not committed as a product change.

## Actual test results

The downloaded Surefire XML and log were inspected, not just the workflow conclusion.

| Test | Result |
| --- | --- |
| `testConcurrentSourceDuringBufferPublication` | Failed at the intended assertion: expected attached source, received `null` |
| `testSequentialJarRecreation` | Passed: recreated JAR/source ZIP provided updated source without any old PR fix |

Totals: **2 tests, 1 failure, 0 errors, 0 skipped**. Maven exited with status **1**.

Observed trace:

```text
BUFFER_PUBLICATION iteration=0 closedAtPublication=false nullAtPublication=true readerWaited=false concurrentSourceNull=true publisherSourcePresent=true afterSourcePresent=true
SEQUENTIAL_RECREATION sourceUpdated=true
```

The failing assertion was:

```text
Concurrent getSource must not expose an uninitialized source buffer
expected: <attached source> but was: <null>
```

The concurrent test has a ten-iteration loop, but this baseline execution stopped at the assertion in iteration 0. This is one controlled reproduction, not ten completed repetitions.

The diagnostic workflow is green because its verifier requires exactly this regression assertion failure and a passing sequential control. **It is not a claim that both tests passed.** Missing tests, skips, execution errors, and unrelated assertion failures are rejected by the verifier.

## Why the interleaving is possible

The relevant non-null-source branch in `ClassFile.mapSource()` currently performs:

1. Find the attached source.
2. Create a buffer.
3. Add it to `BufferManager`.
4. Set the contents.
5. Register the change listener.
6. Complete source mapping.

`BufferManager.addBuffer()` synchronizes insertion into the cache but returns before the caller initializes the contents. Its cache lock therefore does not cover steps 3 and 4 together.

The reader follows the normal inherited path:

```text
AbstractClassFile.getSource()
  -> AbstractClassFile.getBuffer()
  -> Openable.getBuffer()
  -> BufferManager.getBuffer()
  -> Buffer.getContents()
```

With already opened binary model information, `getElementInfo()` can return cached information. That short model-cache access does not hold a lock across the subsequent source-buffer operations.

When a cache entry exists, `Openable.getBuffer()` returns it without calling `openBuffer()` again, unless it is the explicit `NullBuffer` sentinel. Individual synchronized cache and buffer operations do not make publication and initialization one atomic operation. The experiment confirms that the reader did not wait for the paused initializer.

Production sources at the tested revision:

- https://github.com/eclipse-jdt/eclipse.jdt.core/blob/bb43114e42b4b4d8222d86fbcac45ca6b19a0972/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/ClassFile.java
- https://github.com/eclipse-jdt/eclipse.jdt.core/blob/bb43114e42b4b4d8222d86fbcac45ca6b19a0972/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/AbstractClassFile.java
- https://github.com/eclipse-jdt/eclipse.jdt.core/blob/bb43114e42b4b4d8222d86fbcac45ca6b19a0972/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/Openable.java
- https://github.com/eclipse-jdt/eclipse.jdt.core/blob/bb43114e42b4b4d8222d86fbcac45ca6b19a0972/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/BufferManager.java
- https://github.com/eclipse-jdt/eclipse.jdt.core/blob/bb43114e42b4b4d8222d86fbcac45ca6b19a0972/org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/Buffer.java

The IBuffer API explicitly permits null characters for an uninitialized buffer. Null contents alone do not distinguish a newly created buffer from stale state:
https://help.eclipse.org/latest/topic/org.eclipse.jdt.doc.isv/reference/api/org/eclipse/jdt/core/IBuffer.html

## Diagnostic seam and limitations

The test uses the existing model-test project/JAR/source helpers and actual production `ClassFile`, `BufferManager`, `Buffer`, source mapping, and inherited public `getSource()` methods.

A test-only `ClassFile` subclass selects a test-only `BufferManager` subclass with its own real buffer cache. The only overridden cache operation calls `super.addBuffer()` and then pauses the designated publishing thread using latches. It does not modify buffer contents, replace `getSource()`, copy production method bodies, or bypass Java-model validation.

Opening the binary class-file model before the race leaves the source buffer unopened; the test checks this precondition. The reader is allowed to block and finish after release, so the test does not require a particular replacement locking strategy.

This is a deterministic internal test seam, not an uninstrumented whole-UI stress test. It reproduces an ordinary class-file source lookup, not the historical class-file working-copy stack trace verbatim. Neither the modular-classfile path nor all other concurrent buffer lifecycle paths were independently tested. No product fix or A/B validation of a fix was performed in this investigation.

## Relationship to older proposals

For the reproduced top-level class-file cache-hit path, fork PR #14's check in `openBuffer()` is not reached. PR #15's `isClosed()` condition would be false for the observed new, non-closed buffer. These are source-analysis conclusions; the old PR patches were not separately executed in this experiment.

The sequential control passes without either old patch. The appropriate next repair target is safe initialization/publication, not treating every null-content buffer as stale and deleting it. The exact production change still needs implementation, regression coverage, and review.

JDT UI PR #3157 addresses ownership/cancellation of editor background work. The reproduction here uses no editor, so it demonstrates a Core-level concern separately from that lifecycle change. It does not prove that this mechanism caused UI issues #736 or #3153, or that fixing it will eliminate every historical `source=null` symptom.

The two old PRs and `master` were not modified or closed during this investigation.

## Earlier launch attempts (not test evidence)

Runs `36448009831` and `36449344215` did not execute the tests. They started Java 21, while the current target's `org.eclipse.core.filesystem` bundle `1.12.0.v20260927-0940` requires the JavaSE-25 capability. This caused OSGi resolution failure and process exit 13.

The second run preserved the configuration log proving that prerequisite mismatch. The successful diagnostic execution then used the already installed JavaSE-25 toolchain via a temporary model-test profile. The production sources and diagnostic test class remained unchanged between these attempts.
