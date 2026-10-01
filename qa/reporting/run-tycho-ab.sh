#!/usr/bin/env bash
# SPDX-License-Identifier: EPL-2.0
# Diagnostic only: unchanged tests, identical observer, isolated Maven repository.
set -euo pipefail
if [[ $# != 5 ]]; then echo 'Expected core, tools, isolated repository, evidence, toolchains.xml' >&2; exit 2; fi
CORE=$(realpath "$1"); TOOLS=$(realpath "$2"); REPO=$(realpath "$3"); EVIDENCE=$(realpath "$4"); TOOLCHAINS=$(realpath "$5")
[[ $(cat "$REPO/.sandbox-reporting-investigation") == bb86061a7a8d0c3ee4d02f358cf30be6e3e6ae4e ]]
[[ $(git -C "$TOOLS" rev-parse HEAD) == 1527bd535afac09ac61aa850cd41f876e872d32b ]]
[[ -f "$EVIDENCE/run-provenance.properties" && -f "$EVIDENCE/maven-settings.xml" ]]
[[ ! -e "$EVIDENCE/stock" && ! -e "$EVIDENCE/patched" ]]
PROBE="$TOOLS/qa/upstream-jdt/compiler-reporting/target"
CP="$PROBE/test-classes:$PROBE/probe-libs/*"
cd "$CORE"
PHASE=bootstrap
seal() {
  local code=$?
  trap - EXIT
  printf 'exitCode=%s\nlastPhase=%s\n' "$code" "$PHASE" > "$EVIDENCE/completion.properties"
  (cd "$EVIDENCE" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  sha256sum "$EVIDENCE/SHA256SUMS" "$EVIDENCE/run-provenance.properties"
  exit "$code"
}
trap seal EXIT
COMMON=(-B -ntp --settings "$EVIDENCE/maven-settings.xml" --toolchains "$TOOLCHAINS" "-Dmaven.repo.local=$REPO" -Dtycho.version=5.0.4 -Dtycho.useJDK=SYSTEM -Dcompare-version-with-baselines.skip=true -Dtycho.baseline.replace=none -DcompilerBaselineMode=disable -DcompilerBaselineReplace=none)
mvn "${COMMON[@]}" -f org.eclipse.jdt.core.compiler.batch -DlocalEcjVersion=99.99 clean install 2>&1 | tee "$EVIDENCE/bootstrap.log"
PHASE=compile
BUILD=(-Ptest-on-javase-25 -Pbree-libs -pl org.eclipse.jdt.core.tests.compiler -am -Dcbi-ecj-version=99.99 -DDetectVMInstallationsJob.disabled=true)
mvn "${COMMON[@]}" "${BUILD[@]}" clean test-compile -DskipTests 2>&1 | tee "$EVIDENCE/compile.log"
# Monitor both variants without changing the stock reporting classes.
java -cp "$CP" org.sandbox.qa.reporting.TychoProbeInstaller "$REPO" "$PROBE/test-classes" "$PROBE/probe-libs" "$EVIDENCE/observer" LEDGER
run_variant() {
  local variant=$1
  PHASE=$variant
  mkdir "$EVIDENCE/$variant"
  mkdir "$EVIDENCE/$variant/ledger"
  local args="-Xmx2g --add-modules ALL-SYSTEM -Dcompliance=1.8,25 -Djdt.performance.asserts=disabled -Djdt.qa.progress.dir=$EVIDENCE/$variant/ledger -Xlog:gc*:file=$EVIDENCE/$variant/gc-%p.log:time,level,tags -Xlog:class+load=info:file=$EVIDENCE/$variant/classes-%p.log"
  local command=(mvn "${COMMON[@]}" "${BUILD[@]}" verify -Dmaven.test.failure.ignore=true "-Dtycho.surefire.argLine=$args")
  printf '%q ' "${command[@]}" > "$EVIDENCE/$variant/command.txt"
  printf '\n' >> "$EVIDENCE/$variant/command.txt"
  set +e
  /usr/bin/time -f 'wallSeconds=%e\nuserSeconds=%U\nsystemSeconds=%S\nmaxRSSKiB=%M\nfileSystemInputs=%I\nfileSystemOutputs=%O' -o "$EVIDENCE/$variant/time.txt" \
    timeout 40m "${command[@]}" 2>&1 | tee "$EVIDENCE/$variant/maven.log"
  local result=${PIPESTATUS[0]}
  set -e
  echo "$result" > "$EVIDENCE/$variant/maven-exit-code.txt"
  if [[ -d org.eclipse.jdt.core.tests.compiler/target/surefire-reports ]]; then
    cp -r org.eclipse.jdt.core.tests.compiler/target/surefire-reports "$EVIDENCE/$variant/reports"
  fi
  # Even interruption is summarized if the prefix is structurally valid.
  # Parse success does NOT imply run completion; require the explicit marker.
  java -cp "$CP" org.sandbox.qa.reporting.ExecutionLedgerSummary "$EVIDENCE/$variant/ledger" "$EVIDENCE/$variant/execution-summary.properties"
  [[ $result == 0 ]] || return "$result"
  grep -qx 'complete=true' "$EVIDENCE/$variant/execution-summary.properties"
  grep -h 'ExecutionLedger source:.*org.eclipse.tycho.surefire.junit5' "$EVIDENCE/$variant"/classes-*.log > "$EVIDENCE/$variant/loaded-ledger.txt"
  grep -h 'RunListenerAdapter source:.*org.eclipse.tycho.surefire.junit5' "$EVIDENCE/$variant"/classes-*.log > "$EVIDENCE/$variant/loaded-adapter.txt"
  grep -h 'StatelessXmlReporter source:.*org.eclipse.tycho.surefire.osgibooter' "$EVIDENCE/$variant"/classes-*.log > "$EVIDENCE/$variant/loaded-reporter.txt"
}
run_variant stock
java -cp "$CP" org.sandbox.qa.reporting.TychoProbeInstaller "$REPO" "$PROBE/test-classes" "$PROBE/probe-libs" "$EVIDENCE/installed-patches"
if [[ -d org.eclipse.jdt.core.tests.compiler/target/work ]]; then mv org.eclipse.jdt.core.tests.compiler/target/work "$EVIDENCE/stock-work"; fi
if [[ -d org.eclipse.jdt.core.tests.compiler/target/surefire-reports ]]; then mv org.eclipse.jdt.core.tests.compiler/target/surefire-reports "$EVIDENCE/stock-original-reports"; fi
run_variant patched
PHASE=compare
# Independent native events guard against a common XML reporting loss.
diff -u "$EVIDENCE/stock/execution-inventory.tsv" "$EVIDENCE/patched/execution-inventory.tsv" > "$EVIDENCE/native-inventory.diff"
printf '{"renames":{},"allowedMissing":[],"allowedAdded":[]}\n' > "$EVIDENCE/identity-mapping.json"
python3 "$TOOLS/qa/upstream-jdt/compare_test_inventory.py" \
  --baseline "$EVIDENCE/stock/reports" --migrated "$EVIDENCE/patched/reports" \
  --mapping "$EVIDENCE/identity-mapping.json" --output "$EVIDENCE/test-inventory-comparison.json"
grep -qx 'successful=true' "$EVIDENCE/stock/execution-summary.properties"
grep -qx 'successful=true' "$EVIDENCE/patched/execution-summary.properties"
find "$REPO" -type f \( -name '*.pom' -o -name '*.jar' \) -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE/resolved-dependency-sha256.txt"
PHASE=PASS
echo PASS > "$EVIDENCE/run-state.txt"
