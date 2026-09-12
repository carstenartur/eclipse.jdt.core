import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape
import qa

class ReportTest(unittest.TestCase):
    def report(self, directory, *, variant='with-fix', error='', missing=False, wrong=False):
        p = directory / 'org.eclipse.jdt.core.tests.model/target/surefire-reports/TEST-model.xml'
        p.parent.mkdir(parents=True)
        cases = []
        for name in qa.PROBES:
            if missing and name == qa.PROBES[0]:
                continue
            outcome = ('without-fix' if variant == 'with-fix' else 'with-fix') if wrong else variant
            cases.append(f'<testcase name="{name}" classname="T" time="0.002"><system-out>org.eclipse.jdt.core.tests.formatter.FormatterRegionTests</system-out><system-err>{qa.MARKER}{outcome}</system-err></testcase>')
        for name in qa.NOOPS:
            cases.append(f'<testcase name="{name}" classname="T" time="0.001"/>')
        if error:
            cases.append(f'<testcase name="runner"><error>{escape(error)}</error></testcase>')
        # Deliberately inaccurate aggregate attributes must not hide a testcase error.
        p.write_text('<testsuite tests="2" errors="0">'+''.join(cases)+'</testsuite>')
        return qa.read_reports(directory, variant)

    def test_positive(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.report(Path(d))
            self.assertEqual(r['problems'], [])
            self.assertEqual(sum(r['identities'].values()), 4)

    def test_negative_is_an_explicit_expected_result(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.report(Path(d), variant='without-fix')['problems'], [])

    def test_extra_runner_error_is_not_hidden_by_aggregate_counts(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(self.report(Path(d), error='Timer already cancelled.')['problems'])

    def test_missing_test_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(self.report(Path(d), missing=True)['problems'])

    def test_wrong_probe_outcome_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(self.report(Path(d), wrong=True)['problems'])

    def test_empty_reports_are_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(qa.read_reports(Path(d), 'with-fix')['problems'])

    def test_replace_requires_exactly_one_match(self):
        self.assertEqual(qa.replace_once('a OLD z', 'OLD', 'NEW'), 'a NEW z')
        for text in ('a z', 'OLD OLD'):
            with self.assertRaises(ValueError):
                qa.replace_once(text, 'OLD', 'NEW')

if __name__ == '__main__':
    unittest.main()
