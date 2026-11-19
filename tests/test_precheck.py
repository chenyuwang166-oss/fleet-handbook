import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from temp_support import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/fleet-precheck/scripts/precheck.py'
spec = importlib.util.spec_from_file_location('precheck', SCRIPT)
precheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(precheck)


class PrecheckTests(unittest.TestCase):
    def rules(self):
        return precheck.load_rules('# comment\nERROR\t内部词|私有词\t改写\nWARN\t承诺\t核实\n')

    def test_levels_line_numbers_and_inline_code(self):
        self.assertEqual(list(precheck.check_text('正常\n内部词和私有词\n`承诺`\n', self.rules())),
                         [('ERROR', 2, '改写'), ('WARN', 3, '核实')])

    def test_backtick_and_tilde_fences(self):
        source = '```text\n内部词\n```\n承诺\n~~~\n内部词\n~~~\n内部词'
        self.assertEqual(list(precheck.check_text(source, self.rules())),
                         [('WARN', 4, '核实'), ('ERROR', 8, '改写')])

    def test_long_fence_and_mismatched_fence(self):
        source = ' ````md\n```\n内部词\n~~~\n`````\n内部词'
        self.assertEqual(list(precheck.check_text(source, self.rules())), [('ERROR', 6, '改写')])

    def test_unclosed_fence(self):
        self.assertEqual(list(precheck.check_text('~~~\n内部词', self.rules())), [])

    def test_bad_backtick_info_is_not_fence(self):
        self.assertEqual(list(precheck.check_text('```bad` 内部词', self.rules())), [('ERROR', 1, '改写')])

    def test_invalid_rules(self):
        for source in ('', '# only comment', 'ERROR a b', 'INFO\tx\twhy',
                       'ERROR\t[\twhy', 'WARN\t\twhy', 'ERROR\tx\t', 'ERROR\t.*\twhy'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                precheck.load_rules(source)

    def run_cli(self, source, rules=None, missing=False, language='zh', lang=None, project=None):
        with temporary_directory() as temp:
            root = Path(temp)
            if project:
                (root / 'fleet').mkdir()
                roster = 'members.md' if project == 'en' else '成员.md'
                (root / 'fleet' / roster).write_text('', encoding='utf-8')
            terms = root / ('词表.txt' if language == 'zh' else 'terms.txt')
            text = root / ('正文.md' if language == 'zh' else 'body.md')
            terms.write_text(rules or 'ERROR\t内部词\t改写\nWARN\t承诺\t核实\n', encoding='utf-8-sig')
            if not missing:
                text.write_text(source, encoding='utf-8-sig')
            command = [sys.executable, '-I', str(SCRIPT), '--terms', str(terms), str(text)]
            if lang:
                command.extend(['--lang', lang])
            return subprocess.run(command,
                                  capture_output=True, timeout=10)

    def test_cli_clean_warn_error_and_missing_file(self):
        for source, status in (('正常', 0), ('承诺', 0), ('内部词\n承诺', 1)):
            with self.subTest(source=source):
                run = self.run_cli(source)
                self.assertEqual(run.returncode, status, run.stderr.decode('utf-8'))
                self.assertIn('检查完成', run.stdout.decode('utf-8'))
                self.assertNotIn('内部词', run.stdout.decode('utf-8'))
        run = self.run_cli('', missing=True)
        self.assertEqual(run.returncode, 2)
        self.assertNotIn('Traceback', run.stderr.decode('utf-8'))

    def test_cli_invalid_regex_is_failed_check(self):
        run = self.run_cli('正常', rules='ERROR\t[\t说明')
        self.assertEqual(run.returncode, 2)
        self.assertIn('正则无效', run.stderr.decode('utf-8'))
        self.assertNotIn('检查完成', run.stdout.decode('utf-8'))

    def test_example_terms_load(self):
        text = (ROOT / 'skills/fleet-precheck/terms.example.txt').read_text(encoding='utf-8')
        self.assertEqual(len(precheck.load_rules(text)), 3)

    def test_english_rule_diagnostics(self):
        for source, expected in (
                ('', 'no valid rules'),
                ('ERROR a b', 'three tab-separated columns'),
                ('INFO\tx\twhy', 'invalid severity'),
                ('ERROR\t[\twhy', 'invalid regular expression'),
                ('ERROR\t.*\twhy', 'matches empty text')):
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, expected):
                precheck.load_rules(source, lang='en')

    def test_auto_language_handles_inaccessible_project_paths(self):
        for method, error in (('is_file', PermissionError('denied')),
                              ('absolute', OSError('unavailable'))):
            with self.subTest(method=method), patch.object(precheck.Path, method, side_effect=error):
                self.assertEqual(precheck.detect_language(['正文.md', 'terms.txt']), 'zh')
                self.assertEqual(precheck.detect_language(['body.md', 'terms.txt']), 'en')

    def test_auto_bilingual_project_falls_back_to_input_names(self):
        with patch.object(precheck.Path, 'is_file', return_value=True):
            self.assertEqual(precheck.detect_language(['body.md', 'terms.txt']), 'en')
            self.assertEqual(precheck.detect_language(['正文.md', '词表.txt']), 'zh')

    def test_cli_english_clean_warn_error_and_missing_file(self):
        rules = 'ERROR\tinternal\tRewrite\nWARN\tpromise\tVerify\n'
        for source, status in (('clean', 0), ('promise', 0), ('internal\npromise', 1)):
            with self.subTest(source=source):
                run = self.run_cli(source, rules=rules, language='en')
                self.assertEqual(run.returncode, status, run.stderr.decode('utf-8'))
                self.assertIn('Check complete', run.stdout.decode('utf-8'))
                self.assertNotIn('检查完成', run.stdout.decode('utf-8'))
                self.assertNotIn('internal', run.stdout.decode('utf-8'))
        run = self.run_cli('', language='en', missing=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('File not found', run.stderr.decode('utf-8'))
        self.assertNotIn('Traceback', run.stderr.decode('utf-8'))
        run = self.run_cli('clean', rules='ERROR\t[\tWhy', language='en')
        self.assertEqual(run.returncode, 2)
        self.assertIn('invalid regular expression', run.stderr.decode('utf-8'))

    def test_cli_project_language_and_explicit_override(self):
        for project, language, expected in (
                ('en', 'zh', 'invalid regular expression'),
                ('zh', 'en', '正则无效')):
            with self.subTest(project=project):
                run = self.run_cli('clean', rules='ERROR\t[\tWhy', language=language, project=project)
                self.assertEqual(run.returncode, 2)
                self.assertIn(expected, run.stderr.decode('utf-8'))
                override = 'zh' if project == 'en' else 'en'
                run = self.run_cli('clean', rules='ERROR\t[\tWhy', language=language,
                                   project=project, lang=override)
                self.assertIn('正则无效' if override == 'zh' else 'invalid regular expression',
                              run.stderr.decode('utf-8'))
        run = self.run_cli('clean', language='zh', lang='en')
        self.assertIn('Check complete', run.stdout.decode('utf-8'))
        run = self.run_cli('clean', language='en', lang='zh')
        self.assertIn('检查完成', run.stdout.decode('utf-8'))

    def test_bilingual_help(self):
        run = subprocess.run([sys.executable, '-I', str(SCRIPT), '--help'], capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0)
        help_text = run.stdout.decode('utf-8')
        self.assertIn('Check explicit files', help_text)
        self.assertIn('用自有词表', help_text)
        self.assertIn('--lang', help_text)


if __name__ == '__main__':
    unittest.main()
