#!/usr/bin/env python3
"""Check the actual JUnit XML produced by the focused JDT investigation.

This does not execute Java. It distinguishes a demonstrated baseline failure
from a launch/build failure, skipped tests, and unexpected assertions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

CLASS = 'org.eclipse.jdt.core.tests.model.BufferPublicationInvestigationTests'
CONCURRENT = {
    'testConcurrentTopLevelReadWithWarmModel',
    'testConcurrentTopLevelReadWithColdModel',
    'testConcurrentInnerClassRead',
}
CONTROLS = {'testSequentialReadControl', 'testMissingSourceControl'}
EXPECTED = CONCURRENT | CONTROLS
MARKER = 'BUFFER_PUBLICATION: concurrent getSource() returned null before initialization completed'


def read_cases(root: Path) -> list[dict]:
    cases = []
    for path in sorted(root.rglob('TEST-*.xml')):
        for case in ET.parse(path).iter('testcase'):
            if case.get('classname') != CLASS:
                continue
            cases.append({
                'name': case.get('name'),
                'failures': [failure.get('message', '') for failure in case.findall('failure')],
                'errors': [error.get('message', '') for error in case.findall('error')],
                'skipped': len(case.findall('skipped')),
                'report': str(path.relative_to(root)),
            })
    return cases


def validate(cases: list[dict], variant: str) -> None:
    names = [case['name'] for case in cases]
    if len(names) != len(EXPECTED) or set(names) != EXPECTED:
        raise ValueError(f'Expected exactly the five distinct investigation tests, got: {names}')
    for case in cases:
        if case['errors'] or case['skipped']:
            raise ValueError(f'Infrastructure error or skipped test: {case}')
        expected_failure = variant == 'baseline' and case['name'] in CONCURRENT
        if expected_failure:
            if len(case['failures']) != 1 or MARKER not in case['failures'][0]:
                raise ValueError(f'Not the required regression failure: {case}')
        elif case['failures']:
            raise ValueError(f'Test unexpectedly failed: {case}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='Extracted artifact directory for exactly one variant/run')
    parser.add_argument('--variant', choices=['baseline', 'initialized-before-publication'], required=True)
    args = parser.parse_args()
    cases = read_cases(args.root)
    print(json.dumps({'variant': args.variant, 'cases': cases}, indent=2))
    validate(cases, args.variant)
    print('EVIDENCE_VALID: expected regression outcomes were observed in real JUnit XML.')


if __name__ == '__main__':
    main()
