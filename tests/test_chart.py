import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from temp_support import temporary_directory

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/fleet-chart/scripts/fleet_chart.py'
FIX = ROOT / 'tests/fixtures'
spec = importlib.util.spec_from_file_location('fleet_chart', SCRIPT)
chart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chart)


class ChartTests(unittest.TestCase):
    def test_fixture_outputs_exact(self):
        for language in ('zh', 'en', 'special'):
            with self.subTest(language=language):
                source = (FIX / ('roster.' + language + '.md')).read_text(encoding='utf-8')
                expected = (FIX / ('chart.' + language + '.md')).read_bytes()
                self.assertEqual(chart.render(source).encode('utf-8'), expected)

    def source(self):
        return (FIX / 'roster.zh.md').read_text(encoding='utf-8')

    def test_labels_follow_header_language(self):
        for language, title, human, other_title, other_human in (
                ('zh', 'AI 舰队', '人', 'AI Fleet', 'Human'),
                ('en', 'AI Fleet', 'Human', 'AI 舰队', '人')):
            source = (FIX / ('roster.' + language + '.md')).read_text(encoding='utf-8')
            # Accept either reserved parent spelling without changing the chart language.
            source = source.replace('| ' + human + ' |', '| ' + other_human + ' |')
            with self.subTest(language=language):
                rendered = chart.render(source)
                self.assertIn('subgraph fleet["' + title + '"]', rendered)
                self.assertIn('human["' + human + '"]', rendered)
                self.assertNotIn('subgraph fleet["' + other_title + '"]', rendered)
                self.assertNotIn('human["' + other_human + '"]', rendered)

    def test_unknown_parent(self):
        with self.assertRaisesRegex(ValueError, '汇报对象不存在'):
            chart.render(self.source().replace('| 负责人 | 模型 B', '| 不存在 | 模型 B'))

    def test_duplicate_role(self):
        with self.assertRaisesRegex(ValueError, '岗位重名'):
            chart.render(self.source().replace('| 作者 |', '| 负责人 |'))

    def test_cycle(self):
        with self.assertRaisesRegex(ValueError, '成环'):
            chart.render(self.source().replace('| 人 |', '| 作者 |'))

    def test_self_cycle(self):
        with self.assertRaisesRegex(ValueError, '成环'):
            chart.render(self.source().replace('| 人 |', '| 负责人 |'))

    def test_missing_column(self):
        for field in chart.ZH:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, '缺列|找不到'):
                chart.render(self.source().replace(field, '其他列', 1))

    def test_bad_row_and_separator(self):
        for source in (self.source().replace('| 写稿 |', '| 写稿 | 多出 |'),
                       self.source().replace('|---|', '|--|', 1),
                       '| nothing |\n|---|\n| a |'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                chart.render(source)

    def test_reordered_columns(self):
        source = self.source()
        rows = [chart.cells(line) for line in source.splitlines()]
        reordered = '\n'.join('| ' + ' | '.join(reversed(row)) + ' |' for row in rows)
        self.assertEqual(chart.render(reordered), chart.render(source))
        english = (FIX / 'roster.en.md').read_text(encoding='utf-8')
        rows = [chart.cells(line) for line in english.splitlines()]
        reordered = '\n'.join('| ' + ' | '.join(reversed(row)) + ' |' for row in rows)
        self.assertEqual(chart.render(reordered), chart.render(english))

    def test_duplicate_column(self):
        with self.assertRaisesRegex(ValueError, '列名重复'):
            chart.render(self.source().replace('| 交付写进 |', '| 交付写进 | 岗位 |'))

    def test_empty_roster(self):
        with self.assertRaisesRegex(ValueError, '没有岗位'):
            chart.render('\n'.join(self.source().splitlines()[:2]))

    def test_escape_backslash_and_quote(self):
        self.assertEqual(chart.escape_label('x\\"&<>[]{}()|`#;'),
                         'x#92;#34;#38;#60;#62;#91;#93;#123;#125;#40;#41;#124;#96;#35;#59;')

    def test_cli_file_and_bom(self):
        with temporary_directory() as temp:
            input_file = Path(temp) / '成员.md'
            output = Path(temp) / 'chart.md'
            input_file.write_text(self.source(), encoding='utf-8-sig')
            run = subprocess.run([sys.executable, '-I', str(SCRIPT), str(input_file), '-o', str(output)],
                                 capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr.decode('utf-8'))
            self.assertEqual(output.read_bytes(), (FIX / 'chart.zh.md').read_bytes())

    def test_cli_stdout_and_failure(self):
        run = subprocess.run([sys.executable, '-I', str(SCRIPT), str(FIX / 'roster.en.md')],
                             capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout.decode('utf-8').replace('\r\n', '\n'),
                         (FIX / 'chart.en.md').read_text(encoding='utf-8'))
        run = subprocess.run([sys.executable, '-I', str(SCRIPT), str(FIX / 'absent.md')],
                             capture_output=True, timeout=10)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('ERROR', run.stderr.decode('utf-8'))
        self.assertNotIn('Traceback', run.stderr.decode('utf-8'))

    def test_english_validation_diagnostics(self):
        source = (FIX / 'roster.en.md').read_text(encoding='utf-8')
        cases = (
            (source.replace('Role', 'Other', 1), 'Roster table not found'),
            (source.replace('Department', 'Other', 1), 'missing columns'),
            (source.replace('| Delivers to |', '| Delivers to | Role |'), 'duplicate column'),
            (source.replace('|---|', '|--|', 1), 'Markdown separator'),
            (source.replace('|---|---|', '|---|', 1), 'different column counts'),
            (source.replace('| Draft |', '| Draft | Extra |'), 'wrong column count'),
            ('\n'.join(source.splitlines()[:2]), 'no roles'),
            (source.replace('| Writer |', '|  |'), 'must not be empty'),
            (source.replace('| Writer |', '| Human |'), 'reserved'),
            (source.replace('| Writer |', '| Manager |'), 'Duplicate role'),
            (source.replace('| Manager | Model B', '| Absent | Model B'), 'target does not exist'),
            (source.replace('| Human |', '| Writer |'), 'cycle'),
        )
        for invalid, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, expected):
                chart.render(invalid)

    def test_explicit_language_overrides_header(self):
        self.assertIn('AI Fleet', chart.render(self.source(), lang='en'))
        english = (FIX / 'roster.en.md').read_text(encoding='utf-8')
        self.assertIn('AI 舰队', chart.render(english, lang='zh'))
        with self.assertRaisesRegex(ValueError, 'missing columns'):
            chart.render(self.source().replace('部门', 'Other', 1), lang='en')
        with self.assertRaisesRegex(ValueError, '缺列'):
            chart.render(english.replace('Department', 'Other', 1), lang='zh')

    def test_auto_language_uses_the_first_primary_header(self):
        # Later table content must not outweigh the header the parser actually uses.
        text = '| 岗位 | 部门 |\n| ' + ' | '.join(chart.EN) + ' |'
        with self.assertRaisesRegex(ValueError, '缺列'):
            chart.render(text)
        text = '| Role | Department |\n| ' + ' | '.join(chart.ZH) + ' |'
        with self.assertRaisesRegex(ValueError, 'missing columns'):
            chart.render(text)

    def test_auto_language_handles_inaccessible_project_paths(self):
        for method, error in (('is_file', PermissionError('denied')),
                              ('absolute', OSError('unavailable'))):
            with self.subTest(method=method), patch.object(chart.Path, method, side_effect=error):
                self.assertEqual(chart.detect_language('', '成员.md'), 'zh')
                self.assertEqual(chart.detect_language('', 'members.md'), 'en')
                self.assertEqual(chart.detect_language('| Department | Reports to |', '成员.md'), 'en')

    def test_auto_bilingual_project_falls_back_to_input_name(self):
        with patch.object(chart.Path, 'is_file', return_value=True):
            self.assertEqual(chart.detect_language('', 'members.md'), 'en')
            self.assertEqual(chart.detect_language('', '成员.md'), 'zh')

    def test_cli_project_fallback_and_override(self):
        for language, roster_name, expected in (
                ('en', 'members.md', 'Roster table not found'),
                ('zh', '成员.md', '找不到成员表')):
            with self.subTest(language=language), temporary_directory() as temp:
                root = Path(temp)
                (root / 'fleet').mkdir()
                (root / 'fleet' / roster_name).write_text('', encoding='utf-8')
                source = root / 'invalid.md'
                source.write_text('| Nothing |\n|---|\n', encoding='utf-8')
                run = subprocess.run([sys.executable, '-I', str(SCRIPT), str(source)],
                                     capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 2)
                self.assertIn(expected, run.stderr.decode('utf-8'))
                override = 'zh' if language == 'en' else 'en'
                run = subprocess.run([sys.executable, '-I', str(SCRIPT), '--lang', override, str(source)],
                                     capture_output=True, timeout=10)
                self.assertIn('找不到成员表' if override == 'zh' else 'Roster table not found',
                              run.stderr.decode('utf-8'))

    def test_cli_missing_file_language_and_bilingual_help(self):
        with temporary_directory() as temp:
            for filename, expected in (('missing.md', 'File not found'), ('不存在.md', '文件不存在')):
                run = subprocess.run([sys.executable, '-I', str(SCRIPT), str(Path(temp) / filename)],
                                     capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 2)
                self.assertIn(expected, run.stderr.decode('utf-8'))
        run = subprocess.run([sys.executable, '-I', str(SCRIPT), '--help'], capture_output=True, timeout=10)
        self.assertEqual(run.returncode, 0)
        help_text = run.stdout.decode('utf-8')
        self.assertIn('Mermaid organization chart', help_text)
        self.assertIn('成员名册', help_text)
        self.assertIn('--lang', help_text)


if __name__ == '__main__':
    unittest.main()
