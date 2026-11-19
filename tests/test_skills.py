from pathlib import Path
import ast
import re
import shutil
from temp_support import temporary_directory
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'fleet-setup', 'fleet-taskbook', 'fleet-dispatch', 'fleet-memory', 'fleet-precheck', 'fleet-chart', 'fleet-values', 'fleet-rounds', 'fleet-issues'}


class SkillStructureTests(unittest.TestCase):
    def test_skill_entrypoints(self):
        folders = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}
        self.assertEqual(folders, NAMES)
        for name in sorted(NAMES):
            for entry in ('SKILL.md', 'SKILL.zh.md'):
                with self.subTest(name=name, entry=entry):
                    text = (ROOT / 'skills' / name / entry).read_text(encoding='utf-8')
                    front = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
                    self.assertIsNotNone(front)
                    fields = dict(re.findall(r'^([a-z-]+):\s*(.+)$', front[1], re.M))
                    self.assertEqual(fields.get('name'), name)
                    self.assertTrue(fields.get('description', '').strip())

    def test_project_card_and_import(self):
        templates = ROOT / 'skills/fleet-setup/templates/zh'
        self.assertEqual((templates / 'CLAUDE.md').read_text(encoding='utf-8'), '@AGENTS.md\n')
        card = (templates / 'AGENTS.md').read_text(encoding='utf-8')
        first = card.splitlines()[0]
        for action in ('重启', '换会话', '上下文压缩后', '先读项目卡', '本岗位或本任务', '最新交接', '和实际状态核对', '再动手', '收工或上下文快满', '先写交接'):
            self.assertIn(action, first)

    def test_templates_deploy_to_project_root(self):
        templates = ROOT / 'skills/fleet-setup/templates/zh'
        with temporary_directory() as directory:
            project = Path(directory)
            fleet = project / 'fleet'
            fleet.mkdir()
            for template in templates.glob('*.md'):
                destination = project if template.name in ('AGENTS.md', 'CLAUDE.md') else fleet
                shutil.copyfile(template, destination / template.name)
            for name in ('岗位卡', '任务书', '交付'):
                (fleet / name).mkdir()
            card = (project / 'AGENTS.md').read_text(encoding='utf-8')
            targets = re.findall(r'`(fleet/[^`]+)`', card)
            self.assertGreater(len(targets), 5)
            self.assertIn('fleet/机会.md', targets)
            for target in targets:
                self.assertTrue((project / target).exists(), target)
            self.assertFalse((fleet / 'AGENTS.md').exists())
            self.assertFalse((fleet / 'CLAUDE.md').exists())
            self.assertTrue((fleet / '价值观.md').is_file())

    def test_brief_and_dispatch_agree_on_separate_delivery_notes(self):
        for lang, brief_name, skill_entry, heading, suffix in (
            ('zh', '任务书.md', 'SKILL.zh.md', '## 说明', '-说明.md'),
            ('en', 'task-brief.md', 'SKILL.md', '## Notes', '-notes.md'),
        ):
            brief = ROOT / 'skills/fleet-setup/templates' / lang / brief_name
            dispatch = ROOT / 'skills/fleet-dispatch' / skill_entry
            for path in (brief, dispatch):
                with self.subTest(path=path):
                    text = path.read_text(encoding='utf-8')
                    self.assertIn(heading, text)
                    self.assertIn(suffix, text)

    def test_relative_links(self):
        checked = 0
        for path in (ROOT / 'skills').rglob('*.md'):
            text = path.read_text(encoding='utf-8')
            for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', text):
                if '://' in target or target.startswith('#'):
                    continue
                checked += 1
                # GitHub line links may carry ?plain=1 before #L...; the query is not part of the file name.
                self.assertTrue((path.parent / target.split('#')[0].split('?')[0]).exists(), str(path.relative_to(ROOT)) + ': ' + target)
        self.assertGreater(checked, 10)

    def test_python39_syntax(self):
        for parent in ('skills', 'tests'):
            for path in (ROOT / parent).rglob('*.py'):
                ast.parse(path.read_text(encoding='utf-8'), feature_version=(3, 9))


if __name__ == '__main__':
    unittest.main()
