#!/usr/bin/env bash
# SPDX-License-Identifier: EPL-2.0
# Diagnostic only. Never modify a normal Maven cache or JDT test sources.
set -euo pipefail
if [[ $# != 5 ]]; then echo 'Expected core checkout, pinned Sandbox tools, isolated Maven repository, evidence directory, toolchains.xml' >&2; exit 2; fi
CORE=$(realpath "$1"); TOOLS=$(realpath "$2"); REPO=$(realpath "$3"); EVIDENCE=$(realpath "$4"); TOOLCHAINS=$(realpath "$5")
[[ $(cat "$REPO/.sandbox-reporting-investigation") == bb86061a7a8d0c3ee4d02f358cf30be6e3e6ae4e ]]
[[ $(git -C "$TOOLS" rev-parse HEAD) == 8bbc7e94e98fc5849f4633068f3700591a69b069 ]]
cd "$CORE"
COMMON=(-B -ntp --toolchains "$TOOLCHAINS" "-Dmaven.repo.local=$REPO" -Dtycho.version=5.0.4 -Dtycho.useJDK=SYSTEM -Dcompare-version-with-baselines.skip=true -Dtycho.baseline.replace=none -DcompilerBaselineMode=disable -DcompilerBaselineReplace=none)
# Same bootstrap used by the upstream Jenkins build. It is outside timed test runs.
mvn "${COMMON[@]}" -f org.eclipse.jdt.core.compiler.batch -DlocalEcjVersion=99.99 clean install 2>&1 | tee "$EVIDENCE/bootstrap.log"
BUILD=(-Ptest-on-javase-25 -Pbree-libs -pl org.eclipse.jdt.core.tests.compiler -am -Dcbi-ecj-version=99.99 -DDetectVMInstallationsJob.disabled=true)
mvn "${COMMON[@]}" "${BUILD[@]}" clean test-compile -DskipTests 2>&1 | tee "$EVIDENCE/compile.log"

run_variant() {
  local variant=$1
  mkdir -p "$EVIDENCE/$variant"
  printf '%q ' mvn "${COMMON[@]}" "${BUILD[@]}" verify > "$EVIDENCE/$variant/command.txt"
  local args="-Xmx2g --add-modules ALL-SYSTEM -Dcompliance=1.8,25 -Djdt.performance.asserts=disabled -Xlog:gc*:file=$EVIDENCE/$variant/gc-%p.log:time,level,tags -Xlog:class+load=info:file=$EVIDENCE/$variant/classes-%p.log"
  printf '\nargLine=%s\n' "$args" >> "$EVIDENCE/$variant/command.txt"
  set +e
  /usr/bin/time -f 'wallSeconds=%e\nuserSeconds=%U\nsystemSeconds=%S\nmaxRSSKiB=%M\nfileSystemInputs=%I\nfileSystemOutputs=%O' -o "$EVIDENCE/$variant/time.txt" \
    timeout 30m mvn "${COMMON[@]}" "${BUILD[@]}" verify -Dmaven.test.failure.ignore=true "-Dtycho.surefire.argLine=$args" 2>&1 | tee "$EVIDENCE/$variant/maven.log"
  local result=${PIPESTATUS[0]}
  set -e
  echo "$result" > "$EVIDENCE/$variant/maven-exit-code.txt"
  if [[ -d org.eclipse.jdt.core.tests.compiler/target/surefire-reports ]]; then
    cp -r org.eclipse.jdt.core.tests.compiler/target/surefire-reports "$EVIDENCE/$variant/reports"
  fi
  [[ $result == 0 ]] || return "$result"
  grep -h 'RunListenerAdapter source:.*org.eclipse.tycho.surefire.junit5' "$EVIDENCE/$variant"/classes-*.log > "$EVIDENCE/$variant/loaded-adapter.txt"
  grep -h 'StatelessXmlReporter source:.*org.eclipse.tycho.surefire.osgibooter' "$EVIDENCE/$variant"/classes-*.log > "$EVIDENCE/$variant/loaded-reporter.txt"
}
run_variant stock
PROBE="$TOOLS/qa/upstream-jdt/compiler-reporting/target"
java -cp "$PROBE/test-classes:$PROBE/probe-libs/*" org.sandbox.qa.reporting.TychoProbeInstaller "$REPO" "$PROBE/test-classes" "$PROBE/probe-libs" "$EVIDENCE/installed-patches"
# Retire only the first fork's runtime/configuration and reports, not compiled tests.
if [[ -d org.eclipse.jdt.core.tests.compiler/target/work ]]; then
  mv org.eclipse.jdt.core.tests.compiler/target/work "$EVIDENCE/stock-work"
fi
if [[ -d org.eclipse.jdt.core.tests.compiler/target/surefire-reports ]]; then
  mv org.eclipse.jdt.core.tests.compiler/target/surefire-reports "$EVIDENCE/stock-original-reports"
fi
run_variant patched
printf '{"renames":{},"allowedMissing":[],"allowedAdded":[]}\n' > "$EVIDENCE/identity-mapping.json"
# Reuse the existing Core QA comparator: non-empty inventories, identities,
# multiplicities and states must agree; failures on either side reject success.
python3 "$TOOLS/qa/upstream-jdt/compare_test_inventory.py" \
  --baseline "$EVIDENCE/stock/reports" --migrated "$EVIDENCE/patched/reports" \
  --mapping "$EVIDENCE/identity-mapping.json" --output "$EVIDENCE/test-inventory-comparison.json"
find "$REPO" -type f \( -name '*.pom' -o -name '*.jar' \) -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE/resolved-dependency-sha256.txt"
echo PASS > "$EVIDENCE/run-state.txt"
