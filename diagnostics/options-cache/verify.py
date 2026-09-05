#!/usr/bin/env python3
from pathlib import Path
import json
import os
import re
import sys

root=Path(sys.argv[1])
native_class='org.eclipse.jdt.core.tests.model.OptionCacheTests'
expected_failures={
 'native': {name+'('+native_class+')' for name in ['testCompletedSetOptionsCannotBeOverwritten','testPreferenceInvalidationCannotBeUndone','testRepeatedInvalidationCannotBeUndone','testCompletedResetCannotBeOverwritten']},
 'headless': {name+'(diagnostics.OptionsCacheConsistencyTest)' for name in ['completedOptionUpdateMustReachChangedLineFormatter','readerMustNotUndoPreferenceInvalidation','readerMustNotOverwriteCompletedSetOptions']},
 'ui': {'saveMustUseCompletedOptionUpdate(diagnostics.SaveParticipantIntegrationTest)'},
}
summary=['# Options-cache publication fix: executed validation','',
 '| Arm | Test layer | Executed | Failed | Ignored | Logged Eclipse errors |',
 '| --- | --- | ---: | ---: | ---: | ---: |']
for arm in ['stock','fixed']:
    for app,count,prefix in [('native',8,'NATIVE'),('headless',6,'DIAGNOSTIC'),('ui',2,'UI_DIAGNOSTIC')]:
        text=(root/f'{arm}-{app}.txt').read_text(errors='replace')
        wanted=expected_failures[app] if arm=='stock' else set()
        totals=re.findall(rf'^{prefix}_RESULT tests=(\d+) failures=(\d+) ignored=(\d+)$',text,re.M)
        if totals != [(str(count),str(len(wanted)),'0')]:
            raise SystemExit(f'Unexpected {arm}/{app} completion: {totals}')
        actual=set(re.findall(rf'^{prefix}_FAILURE (.+)$',text,re.M))
        if actual != wanted:
            raise SystemExit(f'Unexpected {arm}/{app} failing tests: {actual}')
        status=int((root/f'{arm}-{app}.exit').read_text())
        if status != (1 if wanted else 0):
            raise SystemExit(f'Unexpected exit status: {arm}/{app}={status}')
        errors=len(re.findall(r'^!ENTRY \S+ 4 ',text,re.M))
        if errors:
            raise SystemExit(f'Logged Eclipse errors in {arm}/{app}: {errors}; inspect before publication')
        summary.append(f'| {arm} | {app} | {count} | {len(wanted)} | 0 | {errors} |')
summary += ['', 'Stock fails exactly the four native cache assertions, three original headless assertions and one original editor-save assertion. Fixed passes all 16 tests. No tests were ignored.',
            '', 'Native test source is copied byte-for-byte from the proposed upstream test file. Only JavaModelManager and its nested classes are replaced in the disposable fixed SDK. Other SDK bundles are hash-checked unchanged.',
            '', 'The UI harness registers the standard IDE workspace adapters in both arms. The formatter and editor test assertions are unchanged. This is targeted testing, not a full Tycho/JDT suite run.',
            '', 'The extra space before assignment and historical malformed-edit exceptions of jdt.ui#1445 have not been reproduced or claimed fixed.']
result='\n'.join(summary)+'\n'
(root/'VALIDATION.md').write_text(result)
(root/'validation-success.json').write_text(json.dumps({'native':8,'headless':6,'ui':2,'stock_failures':8,'fixed_failures':0,'ignored':0},indent=2)+'\n')
print(result)
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f: f.write(result)
