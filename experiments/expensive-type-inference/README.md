# ECJ inference work on wide generic varargs calls

This experiment compares three spellings of the generated tables in Apache Camel's [ArtifactUtils.java](https://github.com/apache/camel/blob/8314239af1d44bba087620cf237d7cb6a6608e70/core/camel-util/src/main/java/org/apache/camel/util/ArtifactUtils.java). The four tables contain 413, 29, 56 and 65 entries. The original calls infer all types. The proposed quick fix writes `Map.<String, String>ofEntries(...)` on the three tables with at least 50 entries. Camel's committed fix writes `Map.<String, String>entry(...)` at all 563 inner calls. The ordinary control includes a stream pipeline, a method reference, a `toMap` collector, and a two-entry `Arrays.asList`.

## Reproduce

Requirements are Git, JDK 25 and Python 3 on a Unix-like host. Run the following in a clone of Eclipse JDT Core, using unused worktree paths. Each checkout is an independent build. The experimental branch is the [actual #5681 head](https://github.com/eclipse-jdt/eclipse.jdt.core/pull/5681), whose base branch had moved since it was created. The measurements compare the two named revisions. They do not isolate the PR diff against an identical base.

```sh
experiment=$(pwd)/experiments/expensive-type-inference
git fetch https://github.com/eclipse-jdt/eclipse.jdt.core.git master refs/pull/5681/head
git worktree add --detach ../ecj-master dd2c87485ce2f01b4fc88167f1db701dd6540b35
git worktree add --detach ../ecj-5681 9f253554bceaf371fab277914330ff480b6bd673
python3 "$experiment/benchmark.py" --repo ../ecj-master
python3 "$experiment/benchmark.py" --repo ../ecj-5681
```

The script builds the batch compiler and downloads digest-checked copies of Ant and the pinned Camel source. Offline runs can supply `--ant-jar` and `--camel-source`. Set `JAVA_HOME` or pass `--jdk`. Use `--ecj-jar` to test an existing batch jar, `--repetitions 5` for alternating case order, and `--warning` on a build that implements the proposed compiler option. The script checks the expected class files and compares the Camel output hashes across spellings for each ECJ build. With `--warning` it checks ECJ's problem ID and exact selector offsets for all three expected sites and checks the other fixtures for warnings. Each fixture compilation has a 90-second timeout by default. The JDK's javac builds ECJ from source. ECJ compiles every measured fixture.

For deterministic work counts, apply the instrumentation to each temporary worktree and repeat the same source builds.

```sh
git -C ../ecj-master apply "$experiment/solver-probe.patch"
git -C ../ecj-5681 apply "$experiment/solver-probe.patch"
python3 "$experiment/benchmark.py" --repo ../ecj-master --probe
python3 "$experiment/benchmark.py" --repo ../ecj-5681 --probe
```

## Measured results

ECJ ran under Temurin 25.0.5 with `-XX:ActiveProcessorCount=2 -XX:+UseSerialGC -Xmx512m`. The batch compiler options were `-17 -proc:none -g:none -warn:none`. Each cell below is CPU seconds / elapsed seconds, one fresh uninstrumented process per input on a shared host. CPU includes all compiler JVM threads. These observations establish reproducibility of the example. Timing ratios and small differences between revisions require repeated controlled measurements.

| Fixture | ECJ master | PR #5681 head |
|---|---:|---:|
| Ordinary control | 6.983 / 4.557 | 3.173 / 2.098 |
| Camel, fully inferred | 17.352 / 13.598 | 6.841 / 3.318 |
| Camel, three outer witnesses | 9.307 / 5.599 | 4.896 / 2.731 |
| Camel, 563 inner witnesses | 5.345 / 2.966 | 5.920 / 3.847 |

All six Camel runs produced `ArtifactUtils.class` with SHA-256 `415a5e7d0fe9bfd9e6d8701e30b51169af8e484277c7ad047b2738d37c6d543a`. The source-built warning candidate reported exactly three diagnostics on the original Camel file, on the outer selector at lines 34, 490 and 553. The other two Camel spellings and ordinary control produced zero. With the new warning disabled, the original produced zero. The candidate also compiled all 552 unmodified ECJ batch Java sources, producing 815 classes with zero diagnostics with the option switched off and on.

### Per-invocation work

The probe counts the solver work associated with `InferenceContext18.currentInvocation`. The first count is the Cartesian bound-pair slots presented in `BoundSet.incorporate`: once per outer row, add the length of the inner array, including self-pairs skipped by the loop. An unsuccessful early return can overestimate that row. The second is the actual number of entries to `BoundSet.reduceOneConstraint`, including recursive reductions. The counts measure different operations and should be evaluated separately.

| Site in unmodified source | Master pair slots | Master reduction calls | #5681 pair slots | #5681 reduction calls |
|---|---:|---:|---:|---:|
| Camel COMPONENTS, 413 entries | 11,793,234 | 1,114,602 | 411 | 55 |
| Camel LANGUAGES, 29 entries | 59,730 | 5,898 | 411 | 55 |
| Camel DATAFORMATS, 56 entries | 219,651 | 21,168 | 411 | 55 |
| Camel BEANS, 65 entries | 295,314 | 28,407 | 411 | 55 |
| Ordinary control, largest site (`collect`) | 269 | 124 | 269 | 124 |

On master the Camel file dropped from 12,374,122 pair slots and 1,182,461 reductions to 81,943 and 21,488 with three witnesses. On the PR head the corresponding totals were 24,487 and 15,936 before, then 23,434 and 15,807 after. The remaining 29-entry table accounted for 59,730 slots on master. A source-shape diagnostic continues to recognize the three large calls even when a newer ECJ optimizes them. A measured-work diagnostic should respond to the new counts.

This developer-only probe is for one source file in one compiler process. A bounded identity map tracks up to 2,048 invocation objects, and each counter saturates at one billion. It prints the six highest pair-slot sites and the totals at JVM shutdown. Operations with no active invocation contribute to neither total. The published fixtures tracked at most 567 sites, and both totals stayed below the saturation threshold. The identity follows ECJ's active invocation at each operation, including repeated attempts. It records work at that invocation rather than cumulatively attributing descendants to all ancestors. The scratch JVM exits after compilation. Concurrent compiler instances, long-lived IDE sessions, and choosing a production threshold require separate work.
