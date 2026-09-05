#!/usr/bin/env python3
"""Apply the small candidate patch to a checkout of the pinned upstream revision."""
from pathlib import Path
import re
import shutil
import sys

root = Path(sys.argv[1]).resolve()
here = Path(__file__).resolve().parent
manager = root / 'org.eclipse.jdt.core/model/org/eclipse/jdt/internal/core/JavaModelManager.java'
source = manager.read_text()

def replace(old, new):
    global source
    if source.count(old) != 1:
        raise SystemExit('Non-unique or missing patch anchor: ' + repr(old))
    source = source.replace(old, new)

replace('private volatile Hashtable<String, String> optionsCache;', '''private volatile Hashtable<String, String> optionsCache;

	// Only cache publication and invalidation hold this lock. In particular,
	// preference access and callbacks must remain outside it.
	private final Object optionsCacheLock = new Object();
	private volatile long optionsCacheGeneration;''')
replace('public Hashtable<String, String> getOptions() {', '''/**
	 * Publishes a writer's cache, or invalidates it. Advance the generation even
	 * when the cache is already null: an older reader may still be building it.
	 */
	private void setOptionsCache(Hashtable<String, String> newCache) {
		synchronized (this.optionsCacheLock) {
			this.optionsCacheGeneration++;
			this.optionsCache = newCache;
		}
	}

	/**
	 * A read overlapping an update may return its snapshot, but must not make
	 * that snapshot the cache used by subsequent, non-overlapping reads.
	 */
	private void cacheOptions(Hashtable<String, String> options, long generation) {
		synchronized (this.optionsCacheLock) {
			if (this.optionsCacheGeneration == generation) {
				this.optionsCache = options;
			}
		}
	}

	public Hashtable<String, String> getOptions() {
		// Capture before reading either the cache or the preferences.
		long generation = this.optionsCacheGeneration;''')
replace('this.optionsCache = defaults;', 'cacheOptions(defaults, generation);')
replace('this.optionsCache = new Hashtable<>(options);', 'cacheOptions(new Hashtable<>(options), generation);')
replace('this.optionsCache = cachedValue;', 'setOptionsCache(cachedValue);')
# Cover every existing invalidation site, including default-node and encoding listeners.
count = len(re.findall(r'(?:JavaModelManager\.)?this\.optionsCache = null;', source))
if count < 4:
    raise SystemExit('Unexpected invalidation-site count: ' + str(count))
source = source.replace('JavaModelManager.this.optionsCache = null;', 'JavaModelManager.this.setOptionsCache(null);')
source = source.replace('this.optionsCache = null;', 'setOptionsCache(null);')
# Inspect the complete reset branch, rather than depending on comment spelling.
pattern = r'if \(cachedValue == null\) \{(?P<body>.*?)\n\s*\} else \{\s*Util\.fixTaskTags\(cachedValue\);'
matches = list(re.finditer(pattern, source, re.S))
if len(matches) != 1:
    raise SystemExit('Expected one setOptions reset branch, found ' + str(len(matches)))
match = matches[0]
body = match.group('body')
print('RESET_BRANCH_BEFORE', repr(body), flush=True)
statements = re.sub(r'//[^\n]*', '', body)
statements = re.sub(r'/\*.*?\*/', '', statements, flags=re.S)
statements = re.sub(r'\s+', '', statements)
if statements not in ('getOptions();', 'setOptionsCache(null);getOptions();'):
    raise SystemExit('Unexpected reset statements: ' + repr(statements))
replacement = '''
			// Discard a cache built while the individual preferences were being
			// cleared, and prevent an in-flight reader from publishing one later.
			setOptionsCache(null);
			getOptions();'''
source = source[:match.start('body')] + replacement + source[match.end('body'):]
assignments = re.findall(r'this\.optionsCache = ([^;]+);', source)
if assignments != ['newCache', 'options']:
    raise SystemExit('Cache assignment outside the publication helpers: ' + repr(assignments))
manager.write_text(source)
print('PATCHED_INVALIDATION_SITES', count)
tests = root / 'org.eclipse.jdt.core.tests.model/src/org/eclipse/jdt/core/tests/model'
shutil.copyfile(here / 'OptionCacheTests.java', tests / 'OptionCacheTests.java')
suite = tests / 'AllJavaModelTests.java'
text = suite.read_text()
if text.count('OptionTests.class,') != 1:
    raise SystemExit('Missing OptionTests suite registration anchor')
suite.write_text(text.replace('OptionTests.class,', 'OptionTests.class,\n\t\tOptionCacheTests.class,'))
