# PR 5380: disposable four-method JDK diagnosis

Only for `carstenartur/eclipse.jdt.core`, branch `qa/pr5380-focused-jdk`.
The actual PR branch is not changed. This is a diagnostic experiment, not an upstream fix.

Source is pinned to PR 5380 head `6b777ed704d1a0e00eb87f63ec9042b01b0acd6f`.
The inherited original test bodies `PatternMatching16Test.test056`, `test056a`,
`test056b`, `test056d` are run at compliance 17, without weakening assertions.
A disposable subclass selects exactly these four methods using `RegressionTestSetup`.

## Controlled comparison

* A: OpenJDK `26+34-2887`, official archive SHA-256
  `e7c907ec1036e5480609f8212e6f1e7f710310e029d097e4e1a9645c43676945`.
  Archive location and digest were recovered from
  `docker-library/openjdk@5b84a21f46f4b8ec5ca7faa67ba6308bda53a4cf/versions.json`.
* B: Temurin `26.0.2.1+1`. The installer selector is 26, but both preflight and
  the real test suite REQUIRE this exact runtime string. No silent replacement.
* One runner, one compilation, same generated Tycho/OSGi command and binaries.
* A-B-B-A order with a fresh JVM and restored OSGi workspace each time.
* Maven/bootstrap/download time is excluded from test measurements.

The first four-test setup invocation produces the real Tycho command, which is
replayed without Maven. The command changes only the Java executable and the
QA metadata/output properties. Source patches and class hashes are archived.

## Measurements

`timings.tsv`: test name, phase, wall nanoseconds, current-thread CPU nanoseconds,
current-thread user nanoseconds, parent-process CPU nanoseconds. Unsupported CPU
measurements are -1. Phases are inclusive and MUST NOT be added together.
`vm-launch` measures `LocalVMLauncher.launch()`, not readiness of the child VM.
`launch-and-run` includes launch, output-reader waits and program execution.
The child JDK path is checked against the test JVM's `java.home`.
GNU time records aggregate process-tree user/system times, separate from phases.
Neither parent CPU nor wall minus CPU is an exact measure of Java-versus-OS work.

The gate requires exactly the four test results, no skips/errors/failures,
one compilation event per method, one child launch for each positive test and
no launch for the negative test, and the expected actual runtime/compliance.

## Limits

The uploaded Jenkins log identifies the Maven JVM as A; it does not independently
record `java.runtime.version` from the historical forked test JVM. Its `latest`
symlink prevents claiming byte-for-byte identity with that JVM.
Two measurements per JDK are diagnostic, not a statistically established benchmark.
No parser preconditioning or full regression-suite run is included in this first step.
All instrumentation is temporary and can perturb very short timings equally in
both variants. A failure to acquire the exact JDK is a failed prerequisite, not
proof that either JDK or the original test is slow.
