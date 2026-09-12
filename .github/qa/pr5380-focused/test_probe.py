import tempfile
import unittest
from pathlib import Path
import probe

class ProbeTests(unittest.TestCase):
    def test_exact_replacement_rejects_drift(self):
        for text in ('absent', 'xxx'):
            with self.assertRaises(ValueError):
                probe.replace_once(text, 'x', 'y')
        self.assertEqual('ayb', probe.replace_once('axb', 'x', 'y'))

    def test_wraps_returns_and_nested_blocks(self):
        source = 'private boolean f() {\n\tif (ok) {\n\t\treturn true;\n\t}\n\treturn false;\n}\npublic void g() {}\n'
        changed = probe.wrap_method(source, 'private boolean f()', 'phase')
        self.assertIn('finally {', changed)
        self.assertIn('return true;', changed)
        self.assertIn('return false;', changed)
        self.assertTrue(changed.endswith('public void g() {}\n'))
        with self.assertRaises(ValueError):
            probe.wrap_method(source, 'private void absent()', 'phase')

    def test_no_reports_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                probe.read_cases(Path(d))

    def test_only_four_real_tests_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'TEST-probe.xml'
            p.write_text('<testsuite tests="4" failures="0" errors="0">' + ''.join(
                '<testcase name="'+n+'" time="0.1"/>' for n in probe.METHODS) + '</testsuite>')
            self.assertEqual(set(probe.METHODS), set(probe.read_cases(Path(d))))
            p.write_text(p.read_text().replace('name="test056d"', 'name="unrelated"'))
            with self.assertRaises(ValueError):
                probe.read_cases(Path(d))

    def test_skipped_or_failed_test_is_rejected(self):
        for issue in ('skipped', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / 'TEST-probe.xml'
                p.write_text('<testsuite>' + ''.join(
                    '<testcase name="'+n+'" time="0.1">' + ('<'+issue+'/>' if n == 'test056d' else '') + '</testcase>'
                    for n in probe.METHODS) + '</testsuite>')
                with self.assertRaises(ValueError):
                    probe.read_cases(Path(d))

    def test_command_replay_replaces_runtime_not_workload(self):
        base = ['/old/bin/java', '-Dcompliance=17', '-jar', '/launcher.jar', '-testproperties', '/props']
        cmd = probe.replay_command(base, Path('/new'), Path('/trial'), '26+34-2887')
        self.assertEqual('/new/bin/java', cmd[0])
        self.assertEqual(base[1:], [x for x in cmd[1:] if not x.startswith('-Dqa.')])

if __name__ == '__main__':
    unittest.main()
