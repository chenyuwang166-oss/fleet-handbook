from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / '.github' / 'ISSUE_TEMPLATE'
CHOOSE_URL = 'https://github.com/chenyuwang166-oss/fleet-handbook/issues/new/choose'
DISCUSSIONS = 'https://github.com/chenyuwang166-oss/fleet-handbook/discussions/categories/'


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding='utf-8')


def section(text, heading):
    match = re.search(r'(?m)^(#{1,6}) ' + re.escape(heading) + r'\s*$', text)
    if match is None:
        raise AssertionError('Missing section: ' + heading)
    following = text[match.end():]
    next_heading = re.search(r'(?m)^#{1,' + str(len(match.group(1))) + r'} ', following)
    return following[:next_heading.start()] if next_heading else following


class IssueReportingTests(unittest.TestCase):
    def assert_review_gate(self, text, language):
        """Check the approval meaning without pinning down a complete sentence."""
        if language == 'en':
            patterns = (
                r'\bshow\b', r'\btitle\b', r'\bbody\b', r'\bpublic\b',
                r'\b(edit|change|revision|revise)', r'\bagain\b',
                r'\b(approval|approve|confirm|agreement|agree)',
                r'\b(do not|never|must not)\b.{0,160}\b(submit|post|create)\b',
            )
        else:
            patterns = (
                r'给人看|给读者看|展示|过目', r'标题', r'正文', r'公开',
                r'修改|改了|改动', r'再', r'点头|确认|同意',
                r'(没|未|未经|没有).{0,50}(不提|不提交|不得提交|不发)',
            )
        for pattern in patterns:
            with self.subTest(language=language, meaning=pattern):
                self.assertRegex(text.lower(), pattern)

    def test_all_four_issue_forms_are_available(self):
        for name in ('bug.yml', 'stuck.yml', 'feature.yml', 'show-your-fleet.yml'):
            with self.subTest(template=name):
                path = TEMPLATES / name
                self.assertTrue(path.is_file(), name)
                text = path.read_text(encoding='utf-8')
                for key in ('name', 'description', 'body'):
                    self.assertRegex(text, r'(?m)^' + key + r':')

    def test_show_your_fleet_accepts_a_rule_on_its_own(self):
        form = read('.github/ISSUE_TEMPLATE/show-your-fleet.yml')
        fields = re.split(r'(?m)^  - type: ', form)[1:]
        by_id = {}
        for field in fields:
            identifier = re.search(r'(?m)^    id: (\S+)$', field)
            if identifier:
                by_id[identifier[1]] = field
        self.assertIn('organization-chart', by_id)
        self.assertIn('counterexample', by_id['rule'])
        self.assertIn('反例', by_id['rule'])
        for name, field in by_id.items():
            if name != 'rule':
                self.assertNotRegex(field, r'(?m)^\s*required:\s*true\s*$', name)

    def test_discussion_links_and_blank_issue_option(self):
        text = read('.github/ISSUE_TEMPLATE/config.yml')
        self.assertRegex(text, r'(?m)^blank_issues_enabled:\s*true\s*$')
        self.assertRegex(text, r'(?m)^contact_links:\s*$')
        urls = re.findall(r'(?m)^\s+url:\s*[\'\"]?(https://[^\s\'\"]+)', text)
        self.assertCountEqual(urls, [DISCUSSIONS + 'q-a', DISCUSSIONS + 'show-and-tell'])

    def test_readme_contact_lines_offer_both_languages_and_ai_drafting(self):
        for filename, heading, language, anchor in (
            ('README.md', 'Who we are', 'en', 'report-an-issue-to-the-ai-fleet-handbook'),
            ('README.zh-CN.md', '我们是谁', 'zh', '给舰队手册提-issue'),
        ):
            with self.subTest(filename=filename):
                lines = [line for line in section(read(filename), heading).splitlines()
                         if CHOOSE_URL in line]
                self.assertEqual(len(lines), 1, 'One contact line should point to the chooser')
                line = lines[0]
                self.assertIn('AI', line)
                self.assertIn('skills/fleet-setup/SKILL', line)
                self.assertIn('#' + anchor, line)
                if language == 'en':
                    for pattern in (r'\bchinese\b', r'\benglish\b', r'\bdraft'):
                        self.assertRegex(line.lower(), pattern)
                else:
                    self.assertIn('中文', line)
                    self.assertIn('英文', line)
                    self.assertRegex(line, r'起草|草稿')

    def test_agents_issue_instructions_require_review_and_approval_in_both_languages(self):
        text = read('AGENTS.md')
        for heading, language in (('AI Fleet Handbook', 'en'), ('AI 舰队手册', 'zh')):
            with self.subTest(language=language):
                blocks = re.split(r'(?m)^\d+\. ', section(text, heading))
                candidates = [block for block in blocks
                              if 'issue' in block.lower()
                              and ('public' in block.lower() or '公开' in block)]
                self.assertTrue(candidates, 'Missing issue reporting instruction')
                self.assert_review_gate('\n'.join(candidates), language)

    def test_installed_skill_includes_the_review_gate_in_both_languages(self):
        for filename, heading, language in (
            ('skills/fleet-setup/SKILL.md', 'Report an issue to the AI Fleet Handbook', 'en'),
            ('skills/fleet-setup/SKILL.zh.md', '给舰队手册提 issue', 'zh'),
        ):
            with self.subTest(language=language):
                text = read(filename)
                description = re.search(r'(?m)^description:\s*(.+)$', text)
                self.assertIsNotNone(description)
                self.assertRegex(description.group(1).lower(),
                                 r'issue|suggestion|problem report|报.{0,4}问题|提.{0,4}建议')
                body = section(text, heading)
                self.assert_review_gate(body, language)
                self.assertIn('gh issue create', body)
                self.assertIn('--repo chenyuwang166-oss/fleet-handbook', body)
                self.assertIn('--body-file', body)
                self.assertIn('/issues/new?template=', body)
                self.assertRegex(body.lower(), r'url.{0,30}encod|网址编码')


if __name__ == '__main__':
    unittest.main()
