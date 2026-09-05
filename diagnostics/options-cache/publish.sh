#!/usr/bin/env bash
# Publish only the three tested product/test files, never this helper branch.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
CANDIDATE="$RUNNER_TEMP/core-options-candidate"
BASE=8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51
BRANCH=fix/options-cache-publication-race
[ "$GITHUB_REPOSITORY" = carstenartur/eclipse.jdt.core ]
[ -s "$ROOT/evidence/validation-success.json" ]
[ "$(git -C "$CANDIDATE" rev-parse HEAD)" = "$BASE" ]
CURRENT=$(git ls-remote origin "refs/heads/$BRANCH" | cut -f1)
[ "$CURRENT" = "$BASE" ] || { echo 'Fix branch moved; refusing to overwrite it'; exit 1; }
python3 - "$CANDIDATE" "$ROOT/evidence" <<'PY'
import hashlib,json,os,pathlib,subprocess,sys
candidate,evidence=map(pathlib.Path,sys.argv[1:])
expected=['org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/AllJavaModelTests.java','org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model/OptionCacheTests.java','org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java']
actual=subprocess.check_output(['git','-C',str(candidate),'diff','--cached','--name-only'],text=True).splitlines()
assert sorted(actual)==sorted(expected), actual
source=candidate/expected[2]
assert hashlib.sha256(source.read_bytes()).hexdigest()==(evidence/'candidate-source-sha256.txt').read_text().strip()
history=json.loads((evidence/'history-origin.json').read_text())
sdk=json.loads((evidence/'sdk-provenance.json').read_text())
run=f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
origin='introduced' if history['introduction_verified'] else 'already present'
message=f'''Prevent stale Java options cache publication after concurrent updates

A cold JavaModelManager.getOptions() can read old preference values, then
publish its map after a concurrent JavaCore.setOptions() has completed or
a preference event has invalidated the cache. Subsequent non-overlapping
getOptions() calls then disagree with getOption(). Defensive Hashtable
copies and the existing volatile reference do not prevent this lost
invalidation / late-publication race.

Track a cache generation and publish a reader's snapshot only if no
writer or invalidation has advanced that generation. Coordinate the
comparison/publication and generation changes under a short private lock.
Keep all preference reads, writes, listeners, copying and tracing outside
that lock; retain the cached fast path and defensive-copy semantics.
An overlapping read may return its snapshot but may not cache it after
an intervening update. Invalidation advances the generation even when
the cache is already null, avoiding null-to-null / ABA invalidations.

Route all cache invalidations through the same protocol. End an options
reset with a generation-advancing invalidation before rebuilding, so a
partially computed reset snapshot cannot become the post-reset cache.

Add OptionCacheTests to the model suite. Real preference reads are paused
using bounded CountDownLatch barriers; delegating proxies retain actual
values and release preference locks before pausing. Cover completed
setter/reset races, direct and repeated invalidations, cache reuse,
returned-copy isolation, sequential writes and reentrant preference
callbacks. Restore settings, lookup nodes and worker threads after tests.

Validation: all eight new native tests, six established headless Core /
formatter tests and two real JavaEditor.doSave integration tests execute
against the same pinned Eclipse SDK. Baseline fails exactly eight race
assertions; the fixed version passes all 16, with no ignored tests or
logged Eclipse errors. Compile the actual patched upstream
JavaModelManager source into the disposable SDK; verify that other SDK
bundles are unchanged. In both arms the minimal UI harness registers IDE
workspace adapters and excludes the unrelated optional Tips add-on to
avoid its startup UI racing test-workbench shutdown. No UI product code
or test assertions are modified. This is targeted validation, not a full
Tycho or complete JDT regression-suite run.
Evidence: {run}
Upstream base: 8c40c7d2ae12c0a32ab3cca1ab31b53956c65d51
SDK: I20260826-2300; JDK 25; Linux GTK x86_64
SDK SHA-256: {sdk['sha256']}
The archive matches Eclipse's official HTTPS SHA-512 checksum manifest.

History: the options cache was {origin} in
{history['sha']} ({history['date']}, "{history['subject']}").
The audit follows both JavaCore.java (the former location) and
JavaModelManager.java (to which the cache moved in 2005), comparing the
historical commit with its parent. This is source-history evidence, not
a claim that a historical runtime or every intervening release was tested.

Related: https://github.com/eclipse-jdt/eclipse.jdt.ui/issues/1445
The tests demonstrate stale formatter options and the missing cast space
through an actual editor save. They do not reproduce or claim to fix the
extra space before assignment or the historical MalformedTreeException.
No UI workaround, diagnostic workflow or generated evidence is included
in this commit. No upstream pull request is opened.
'''
(evidence/'commit-message.txt').write_text(message)
PY
git -C "$CANDIDATE" config user.name "$(git show -s --format=%an HEAD)"
git -C "$CANDIDATE" config user.email "$(git show -s --format=%ae HEAD)"
git -C "$CANDIDATE" commit -F "$ROOT/evidence/commit-message.txt"
gh auth setup-git
git -C "$CANDIDATE" push origin "HEAD:refs/heads/$BRANCH"
git -C "$CANDIDATE" log -1 --format=fuller | tee "$ROOT/evidence/published-commit.txt"
