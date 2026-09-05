#!/usr/bin/env bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
HERE="$ROOT/diagnostics/options-cache"
BASE=8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51
CANDIDATE="$RUNNER_TEMP/core-options-candidate"
EVIDENCE="$ROOT/evidence"
mkdir -p "$EVIDENCE"
git worktree add --detach "$CANDIDATE" "$BASE"
python3 "$HERE/apply_fix.py" "$CANDIDATE"
git -C "$CANDIDATE" add org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/AllJavaModelTests.java
git -C "$CANDIDATE" diff --cached --check
git -C "$CANDIDATE" diff --cached --stat | tee "$EVIDENCE/diff-stat.txt"
git -C "$CANDIDATE" diff --cached --binary > "$EVIDENCE/fix.patch"

FILE=org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java
API_FILE=org.eclipse.jdt.core/model/org/eclipse/jdt/core/JavaCore.java
git show "$BASE:$FILE" > "$EVIDENCE/JavaModelManager.baseline.java"
# The cache moved from JavaCore to JavaModelManager in 2005; trace both locations.
git log "$BASE" --reverse --format='%H %as %s' -G 'optionsCache' -- "$FILE" "$API_FILE" > "$EVIDENCE/history.txt"
FIRST=$(head -1 "$EVIDENCE/history.txt" | cut -d ' ' -f 1)
git merge-base --is-ancestor "$FIRST" "$BASE"
git show --format=fuller "$FIRST" -- "$FILE" "$API_FILE" > "$EVIDENCE/cache-introduction.patch"
head -8 "$EVIDENCE/history.txt"
python3 - "$ROOT" "$FIRST" "$FILE" "$API_FILE" <<'PY'
import json, pathlib, subprocess, sys
root=pathlib.Path(sys.argv[1]); sha=sys.argv[2]; paths=sys.argv[3:]
meta=subprocess.check_output(['git','show','-s','--format=%H%n%as%n%s',sha],text=True).splitlines()
def has_cache(revision):
    present=[]
    for path in paths:
        result=subprocess.run(['git','show',revision+':'+path],capture_output=True,text=True)
        if result.returncode==0 and 'optionsCache' in result.stdout:
            present.append(path)
    return present
before,after=has_cache(sha+'^'),has_cache(sha)
diff=subprocess.check_output(['git','show','--format=',sha,'--',*paths],text=True)
result=dict(sha=meta[0],date=meta[1],subject=meta[2],cache_locations_before=before,
            cache_locations_after=after,introduction_verified=not before and bool(after),diff_excerpt=diff[:7500])
p=root/'evidence/history-origin.json'
p.write_text(json.dumps(result,indent=2)+'\n')
print('HISTORY_ORIGIN',p.read_text(),flush=True)
PY

BASE_URL=https://download.eclipse.org/eclipse/downloads/drops4/I20260826-2300
curl --fail --location --retry 2 "$BASE_URL/eclipse-SDK-I20260826-2300-linux-gtk-x86_64.tar.gz" -o "$RUNNER_TEMP/eclipse-sdk.tar.gz"
python3 "$HERE/verify_sdk.py" "$BASE_URL" "$RUNNER_TEMP/eclipse-sdk.tar.gz" "$EVIDENCE"
tar xzf "$RUNNER_TEMP/eclipse-sdk.tar.gz" -C "$RUNNER_TEMP"
# Keep the same documented optional-bundle exclusions in both arms.
python3 - "$RUNNER_TEMP/eclipse" "$EVIDENCE" <<'PY'
import json,pathlib,sys
sdk,evidence=map(pathlib.Path,sys.argv[1:])
p=sdk/'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
lines=p.read_text().splitlines()
removed=[line.split(',')[0] for line in lines if line.startswith('org.eclipse.tips.')]
p.write_text('\n'.join(line for line in lines if not line.startswith('org.eclipse.tips.'))+'\n')
(evidence/'ui-harness.json').write_text(json.dumps({'excluded_optional_bundles':removed,'applies_to':'both stock and fixed','startup':'queued EventAdmin marker after APP_STARTUP_COMPLETE dispatch','reason':'minimal editor-test workbench without the unrelated Tips popup'},indent=2)+'\n')
print('UI_HARNESS_OPTIONAL_TIPS_EXCLUDED',removed,flush=True)
PY
cp -a "$RUNNER_TEMP/eclipse" "$RUNNER_TEMP/eclipse-fixed"

DIAG="$RUNNER_TEMP/jdt1445"
mkdir -p "$DIAG/src/diagnostics" "$DIAG/META-INF"
URL=https://raw.githubusercontent.com/carstenartur/eclipse.jdt.ui/9cea8a527e4810e8c60d18215f1de122bac17120/diagnostics/jdt1445
for f in src/diagnostics/OptionsCacheConsistencyTest.java src/diagnostics/SaveParticipantIntegrationTest.java src/diagnostics/Application.java META-INF/MANIFEST.MF plugin.xml run.sh; do
  curl --fail --silent --show-error --location --retry 2 "$URL/$f" -o "$DIAG/$f"
done
mkdir -p "$DIAG/src/org/eclipse/jdt/core/tests/model"
cp "$CANDIDATE/org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java" "$DIAG/src/org/eclipse/jdt/core/tests/model/"
cp "$HERE/NativeApplication.java" "$DIAG/src/diagnostics/"
python3 - "$DIAG" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); plugin=p/'plugin.xml'
plugin.write_text(plugin.read_text().replace('</plugin>', '''  <extension point="org.eclipse.core.runtime.applications" id="native">
    <application cardinality="singleton-global" thread="main" visible="true">
      <run class="diagnostics.NativeApplication"/>
    </application>
  </extension>
</plugin>'''))
PY
python3 "$HERE/prepare_ui.py" "$DIAG"
sha256sum "$CANDIDATE/org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java" "$DIAG/src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java" | tee "$EVIDENCE/native-source-hashes.txt"
python3 "$HERE/rebuild_core.py" "$RUNNER_TEMP/eclipse-fixed" "$CANDIDATE/$FILE" "$EVIDENCE"

run_tests() {
  local arm=$1 app=$2 id=$3
  local sdk="$RUNNER_TEMP/eclipse"
  if [ "$arm" = fixed ]; then sdk="$RUNNER_TEMP/eclipse-fixed"; fi
  if [ -d "$DIAG/out" ]; then mv "$DIAG/out" "$EVIDENCE/workspace-$arm-$app-previous"; fi
  set +e
  if [ "$app" = ui ]; then
    timeout 180 xvfb-run -a bash "$DIAG/run.sh" "$sdk" "$id" 2>&1 | tee "$EVIDENCE/$arm-$app.txt"
  else
    timeout 180 bash "$DIAG/run.sh" "$sdk" "$id" 2>&1 | tee "$EVIDENCE/$arm-$app.txt"
  fi
  local status=${PIPESTATUS[0]}
  set -e
  echo "$status" > "$EVIDENCE/$arm-$app.exit"
  if [ -d "$DIAG/out" ]; then mv "$DIAG/out" "$EVIDENCE/workspace-$arm-$app"; fi
}
for arm in stock fixed; do
  run_tests "$arm" native jdt1445.diagnostics.native
  run_tests "$arm" headless jdt1445.diagnostics.run
  run_tests "$arm" ui jdt1445.diagnostics.ui
done
python3 "$HERE/verify.py" "$EVIDENCE"
