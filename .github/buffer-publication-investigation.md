# Class-file buffer publication investigation

Upstream baseline: `a9ba670e61dc6b35c345a34ee97f61d1267bc132`.

This branch is an experiment, not a proposed production fix. Existing PRs #14 and #15 are untouched. All files under `org.eclipse.jdt.core/model` are unchanged.

## Hypothesis

`ClassFile.mapSource()` publishes a fresh buffer via `BufferManager.addBuffer()` before setting its contents. A concurrent ordinary `getSource()` call may retrieve that buffer while it is still open and uninitialized.

## Method

The dedicated `BufferPublicationInvestigationTests` class uses real project/JAR/source fixtures and real JDT model APIs. A `BufferManager` subclass calls the original `addBuffer()` and then pauses the publishing thread with latches. It does not insert a fabricated buffer or alter its contents. The global manager is restored after each test and workers are joined.

Concurrent cases cover warm and cold model state and an inner class reading the outer class's published buffer. Sequential access and an intentionally absent source attachment are controls.

## Interpreting the workflow

The baseline classifier requires exactly five real JUnit executions, no errors/skips, three failures carrying the specific `BUFFER_PUBLICATION:` assertion, and two passing controls. A green classifier would mean that the hypothesized bug was reproduced, not that the production code passed its regression tests.

An unexpected timeout, compilation failure, missing test report, different assertion failure, or skipped test is not evidence for the hypothesis. Check the retained JUnit XML, observation lines and Maven log before drawing conclusions.

No runtime result is claimed by this document. Results must be taken from the completed workflow run.
