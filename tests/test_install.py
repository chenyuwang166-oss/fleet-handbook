import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from temp_support import temporary_directory
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fleet_install', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_chinese_cli_stdout_is_utf8_without_encoding_overrides(self):
        env = os.environ.copy()
        env.pop('PYTHONUTF8', None)
        env.pop('PYTHONIOENCODING', None)
        with temporary_directory() as directory:
            run = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'install.py'),
                 '--lang', 'zh', '--host', 'agents', '--project', directory],
                env=env, capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr.decode('utf-8'))
            self.assertIn('已安装', run.stdout.decode('utf-8'))

    def test_english_template_normalizes_legacy_file_map(self):
        legacy = '\n'.join('fleet/' + name for name in installer.ENGLISH_PATHS)
        translated = installer.english_template(legacy.encode('utf-8'))
        self.assertTrue(translated.isascii())
        self.assertIn(b'fleet/role-cards/', translated)
        self.assertIn(b'fleet/task-briefs/', translated)
        self.assertIn(b'fleet/handoff.md', translated)
        self.assertEqual(installer.english_template(translated), translated)

    def test_both_hosts_and_language_selection(self):
        with temporary_directory() as directory:
            project = Path(directory)
            count, written = installer.install(project, 'zh', 'all')
            self.assertEqual(count, 18)
            self.assertGreater(written, 18)
            for host in ('.agents', '.claude'):
                target = project / host / 'skills/fleet-setup/SKILL.md'
                self.assertEqual(target.read_bytes(), (ROOT / 'skills/fleet-setup/SKILL.zh.md').read_bytes())
                self.assertTrue((target.parent / 'templates/zh/AGENTS.md').exists())
                self.assertTrue((project / host / 'skills/fleet-chart/scripts/fleet_chart.py').is_file())
            self.assertFalse((project / 'AGENTS.md').exists())
            self.assertEqual(installer.install(project, 'zh', 'all'), (18, 0))

    def test_collision_preserves_reader_files_before_any_write(self):
        with temporary_directory() as directory:
            project = Path(directory)
            target = project / '.claude/skills/fleet-values/SKILL.md'
            target.parent.mkdir(parents=True)
            target.write_text('reader-owned skill\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'differs'):
                installer.install(project)
            self.assertEqual(target.read_text(encoding='utf-8'), 'reader-owned skill\n')
            self.assertFalse((project / '.agents').exists())

    def test_single_host_english(self):
        with temporary_directory() as directory:
            project = Path(directory)
            self.assertEqual(installer.install(project, 'en', 'agents')[0], 9)
            self.assertFalse((project / '.claude').exists())
            self.assertEqual((project / '.agents/skills/fleet-memory/SKILL.md').read_bytes(),
                             (ROOT / 'skills/fleet-memory/SKILL.md').read_bytes())

    def test_installed_template_working_filenames_in_both_languages(self):
        fleet_files = {
            '原则.md': 'principles.md', '价值观.md': 'values.md',
            '成员.md': 'members.md', '决定.md': 'decisions.md',
            '交接.md': 'handoff.md', '审批流.md': 'approvals.md',
            '机会.md': 'opportunities.md',
        }
        for language in ('en', 'zh'):
            with self.subTest(language=language), temporary_directory(prefix='install-' + language + '-') as directory:
                project = Path(directory)
                installer.install(project, language, 'all')
                templates = project / '.agents/skills/fleet-setup/templates' / language
                records = set(fleet_files.values() if language == 'en' else fleet_files)
                forms = {'role-card.md', 'task-brief.md'} if language == 'en' else {'岗位卡.md', '任务书.md'}
                self.assertEqual({p.name for p in templates.glob('*.md')},
                                 records | forms | {'AGENTS.md', 'CLAUDE.md'})
                # The installer installs skills; mirror fleet-setup's separate
                # template-copy step without touching the reader's root card.
                fleet = project / 'fleet'
                fleet.mkdir()
                for filename in records:
                    shutil.copyfile(templates / filename, fleet / filename)
                opportunity = 'opportunities.md' if language == 'en' else '机会.md'
                self.assertIn(opportunity, (templates.parent.parent / 'SKILL.md').read_text(encoding='utf-8'))
                self.assertIn('fleet/' + opportunity, (templates / 'AGENTS.md').read_text(encoding='utf-8'))
                self.assertEqual((fleet / opportunity).read_bytes(), (templates / opportunity).read_bytes())
                for name in (('role-cards', 'task-briefs', 'deliveries') if language == 'en'
                             else ('岗位卡', '任务书', '交付')):
                    (fleet / name).mkdir()
                shutil.copyfile(templates / ('task-brief.md' if language == 'en' else '任务书.md'),
                                fleet / ('task-briefs/01.md' if language == 'en' else '任务书/01.md'))
                shutil.copyfile(templates / ('role-card.md' if language == 'en' else '岗位卡.md'),
                                fleet / ('role-cards/writer.md' if language == 'en' else '岗位卡/作者.md'))
                if language == 'en':
                    self.assertTrue(all(p.name.isascii() for p in project.rglob('*')))
                    self.assertFalse((templates.parent / 'zh').exists())
                    self.assertEqual(list(project.glob('*/skills/*/SKILL.zh.md')), [])
                else:
                    self.assertTrue((fleet / '成员.md').is_file())
                    self.assertTrue((fleet / '岗位卡').is_dir())
                roster = fleet / ('members.md' if language == 'en' else '成员.md')
                source = roster.read_text(encoding='utf-8')
                source = source.replace('Department' if language == 'en' else '部门', 'Other', 1)
                roster.write_text(source, encoding='utf-8')
                script = project / '.agents/skills/fleet-chart/scripts/fleet_chart.py'
                run = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(script), str(roster)],
                                     cwd=project, capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 2)
                diagnostic = run.stderr.decode('utf-8')
                self.assertIn('missing' if language == 'en' else '缺列', diagnostic)
                if language == 'en':
                    self.assertFalse(any('\u4e00' <= c <= '\u9fff' for c in diagnostic))


if __name__ == '__main__':
    unittest.main()
