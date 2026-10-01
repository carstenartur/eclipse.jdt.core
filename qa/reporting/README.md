# Continuation of the JUnit 5 reporting investigation

This branch preserves Stephan Herrmann's complete final migration at
`bb86061a7a8d0c3ee4d02f358cf30be6e3e6ae4e`. The changes here are diagnostic
workflow/script/documentation only; no test methods, compliance selection,
lifecycle implementation, dependencies, or normal build defaults are changed.
The preserved base is `investigate/junit5-reporting-base` in this fork.

The separate Sandbox PR https://github.com/carstenartur/sandbox/pull/1646
reproduces repeated full XML writes with the real Surefire 3.5.6 reporter and
Jupiter 5.14.3. It verifies an experimental report-owner boundary correction
and, separately, consistent XML counts when no retries are configured.

## Real Tycho A/B gate

The opt-in `JUnit 5 reporting investigation` workflow pins this migration,
Sandbox tooling commit `8bbc7e94e98fc5849f4633068f3700591a69b069`, Tycho 5.0.4
and build-parent source commit `96fc148c72af941d7ae8aadf261ad5dca9c4e9ef`.
It uses Java 25 and compliances 1.8/25 for both variants. This is not a claim
that every setting matches Stephan's original Jenkins/JDK-27 run.

It bootstraps the compiler and compiles the selected reactor before timing.
It then runs the unchanged compiler module's configured suites using stock
Tycho. Only afterwards does it replace the two verified Surefire class
families inside disposable Tycho provider/booter artifacts. Original bytecode
must match the stock 3.5.6 jars; originals and hashes are preserved, signed
artifacts are rejected, and the normal user Maven cache is never used.

Class-load logs verify the provider/booter locations in each fork. The second
run uses a fresh test runtime with the same compiled sources and dependency
cache. Complete XML reports and GC logs are retained, including on failure.
The existing Sandbox Core inventory comparator, with an empty exception map,
rejects missing, added, newly skipped or failing/error test cases. A successful
Maven process alone is not an acceptance criterion.

Timing includes Maven's incremental build/verification overhead and identical
class-loading/GC instrumentation. It is a single stock-then-patched comparison,
not a statistically controlled benchmark. The initial P2 composite resolution
is not fully archived/pinned; dependency hashes are recorded after a completed
comparison. Do not claim full external reproducibility or compiler readiness
until these further gates are fulfilled.

No upstream PR is reopened, and no experimental binaries are published. This
branch is an investigation, not a release candidate. Remaining gates include
retries/parallel reporting, bounded interrupted-run reporting, console totals,
resource lifecycle/isolated launches, all migration TODOs, Java-version
coverage, and the separate JDT UI test-tree/progress issues.
