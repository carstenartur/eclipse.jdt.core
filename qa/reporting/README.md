# Continuation of the JUnit 5 reporting investigation

This branch preserves Stephan Herrmann's final migration at
`bb86061a7a8d0c3ee4d02f358cf30be6e3e6ae4e`. Only the opt-in diagnostic workflow
and `qa/reporting` change. The workflow rejects any change outside those
paths. Normal builds, test implementation and lifecycle remain unchanged.

## Evidence and limits

Sandbox PR https://github.com/carstenartur/sandbox/pull/1646 independently
reproduces the Surefire 3.5.6 XML rewrite amplification and tests an
experimental correction. The current tooling pin is
`1527bd535afac09ac61aa850cd41f876e872d32b` (18 probe/installer/ledger tests per
variant). Parent source remains pinned to
`96fc148c72af941d7ae8aadf261ad5dca9c4e9ef`, Tycho to 5.0.4, Java to 25 and
compliances to 1.8/25. This does not reproduce the original JDK-27 environment.

The first workflow did not establish acceptable, consistently attributable
JDT A/B evidence. Its console reported a dependency-resolution timeout for
`jakarta.annotation-api:3.0.0` at the Eclipse annotation repository. The
retrieved archive did not agree with the console/pinned-parent provenance.
Do not use those archived timing numbers as a verified speedup.

The new diagnostic settings redirect only that explicit annotation repository
ID to Maven Central; Eclipse snapshots and P2 repositories are not mirrored.
The settings are copied into evidence and used identically by both variants.
No normal Maven settings or user cache are changed.

## Comparison

Build once, then execute the same compiled compiler-test suites through stock
and experimentally corrected Tycho. Use a marked disposable repository;
verify original reporter bytecode and retain backups and patch hashes.
Run stock then corrected with identical heap, GC and class-load logging.
Timing is a single instrumented comparison, not a statistical benchmark.

Install the same optional native JUnit observer before both variants. It
appends and flushes event records independently of final XML reports. The
observer is explicitly verified in the actual fork's class-load log.
The strict summary rejects absent/corrupt evidence and distinguishes normal
completion from success. A complete failing run may be compared with its
counterpart, but cannot pass the final gate. Native identities/multiplicities/
outcomes and the existing strict XML inventory comparison must both agree;
failed/errored tests or unfinished native plans reject success.

This append-only ledger preserves progress on process termination, but is NOT
yet interrupted-run Jenkins XML support. XML reporting remains enabled; no
failure is hidden by the temporary `maven.test.failure.ignore` needed to
collect both sides' complete results. The final acceptance checks override
Maven's zero exit status for test failures.

## Provenance

Every new run starts with empty evidence/repository directories. The artifact
name includes run ID and attempt. `run-provenance.properties` records those,
a fresh nonce, checkout/tooling/parent commits, and is printed to the console.
Copies of the actual workflow, script and diagnostic settings accompany the
results. `SHA256SUMS` covers available evidence on success or failure; its
hash is printed before upload. To accept an archive, verify its API digest,
its manifest, the manifest's console hash, run ID/attempt and pinned commits.
This is consistency checking, not a cryptographic attestation of the runner.

No upstream PR is reopened or experimental binary published. Remaining work
includes the complete real JDT A/B result, full migration semantic coverage,
resource lifecycle/isolated launches, parallel/retry reporting, partial XML,
console counts and IDE tree/progress/display problems. Compare the existing
Apache proposal https://github.com/apache/maven-surefire/pull/3471 rather than
claim this diagnostic prototype is an upstream-ready replacement.
