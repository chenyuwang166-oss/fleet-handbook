import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from temp_support import temporary_directory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/fleet-chart/scripts/fleet_org_card.py'
spec = importlib.util.spec_from_file_location('fleet_org_card', SCRIPT)
org = importlib.util.module_from_spec(spec)
spec.loader.exec_module(org)


def svg_from(page):
    return re.search(r'<svg\b.*?</svg>', page, re.S).group()


class OrgCardTests(unittest.TestCase):
    def make_project(self, directory, language='en', source=None):
        project = Path(directory) / 'Example project'
        fleet = project / 'fleet'
        fleet.mkdir(parents=True, exist_ok=True)
        if source is None:
            source = (ROOT / 'tests/fixtures' / ('roster.' + language + '.md')).read_text(encoding='utf-8')
        (fleet / ('成员.md' if language == 'zh' else 'members.md')).write_text(source, encoding='utf-8')
        return project

    def test_roster_hierarchy_and_bilingual_labels(self):
        for language, human, manager, writer, department, assigned in (
                ('en', 'Human', 'Manager', 'Writer', 'Department:', 'Assigned:'),
                ('zh', '人', '负责人', '作者', '部门：', '派驻：')):
            with self.subTest(language=language), temporary_directory() as directory:
                project = self.make_project(directory, language)
                page = org.render(project, today='2026-11-15')
                svg = ET.fromstring(svg_from(page))
                text = ' '.join(svg.itertext())
                for label in ('Example project', human, manager, writer, department, assigned, '2026-11-15'):
                    self.assertIn(label, text)
                self.assertIn('Reports to: Manager' if language == 'en' else '汇报给：负责人', text)
                nodes = svg.findall('{*}g')
                self.assertEqual([node.attrib['data-role'] for node in nodes], [human, manager, writer])
                self.assertEqual(len(svg.findall('{*}path')), 2)

    def test_missing_and_invalid_rosters_have_empty_state(self):
        for language, message in (('zh', '还没有可读取的成员名册'), ('en', 'No readable roster yet')):
            with self.subTest(language=language), temporary_directory() as directory:
                project = Path(directory)
                page = org.render(project, language, '2026-11-15')
                self.assertIn(message, page)
                self.assertIn('save-image', page)
                project = self.make_project(directory, language, '| malformed |')
                self.assertIn(message, org.render(project, language, '2026-11-15'))

    def test_empty_or_unreadable_preferred_roster_uses_other_language(self):
        for language in ('zh', 'en'):
            for unavailable in ('empty', 'unreadable'):
                with self.subTest(language=language, unavailable=unavailable), temporary_directory() as directory:
                    fallback = 'en' if language == 'zh' else 'zh'
                    project = self.make_project(directory, fallback)
                    preferred = project / 'fleet' / org.board.MAPS[language][0]
                    preferred.write_text('' if unavailable == 'empty' else 'Unreadable roster', encoding='utf-8')
                    real_read = org.board.read

                    def read(path, boundary):
                        return '' if unavailable == 'unreadable' and path == preferred else real_read(path, boundary)

                    with mock.patch.object(org.board, 'read', side_effect=read):
                        page = org.render(project, language, '2026-11-15')
                    self.assertIn('data-role="Manager"' if fallback == 'en' else 'data-role="负责人"', page)
                    self.assertIn('fleet/' + org.board.MAPS[fallback][0], page)
                    self.assertNotIn('No readable roster yet', page)
                    self.assertNotIn('还没有可读取的成员名册', page)

    def test_content_is_escaped_as_svg_text(self):
        with temporary_directory() as directory:
            source = (ROOT / 'tests/fixtures/roster.en.md').read_text(encoding='utf-8')
            source = source.replace('Manager', '</text><script>alert(1)</script>&"')
            project = self.make_project(directory, source=source)
            page = org.render(project, 'en', '2026-11-15')
            svg = ET.fromstring(svg_from(page))
            self.assertEqual(svg.findall('.//{*}script'), [])
            self.assertIn('</text><script>alert(1)</script>&"', ''.join(svg.itertext()))
            self.assertIn('&lt;script&gt;', page)
            self.assertNotIn('alert(1)</script>', page)

    def test_export_is_inline_native_svg_and_has_png_fallback(self):
        with temporary_directory() as directory:
            project = self.make_project(directory)
            page = org.render(project, today='2026-11-15')
            self.assertIn('Save as image', page)
            for implementation in ('XMLSerializer', "type: 'image/svg+xml;charset=utf-8'", 'drawImage',
                                   'canvas.toBlob', "canvas.toDataURL('image/png')", 'alternative.download', 'download.click()'):
                self.assertIn(implementation, page)
            self.assertNotIn('foreignObject', page)
            self.assertNotIn('<image', page)
            self.assertNotRegex(page.replace('http://www.w3.org/2000/svg', ''), r'https?://')
            self.assertNotRegex(page, r'<(?:script|link)\b[^>]+(?:src|href)=')
            self.assertIn("connect-src 'none'", page)

    def test_cli_default_output_and_language_override(self):
        for language, filename, save in (('zh', '组织图.html', '存成图片'), ('en', 'chart.html', 'Save as image')):
            with self.subTest(language=language), temporary_directory() as directory:
                project = self.make_project(directory, language)
                run = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--project', str(project),
                                      '--today', '2026-11-15'], capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr.decode('utf-8'))
                self.assertEqual(run.stdout.decode('utf-8').strip(), 'fleet/' + filename)
                self.assertIn(save, (project / 'fleet' / filename).read_text(encoding='utf-8'))
                other = 'en' if language == 'zh' else 'zh'
                other_page = org.render(project, other, '2026-11-15')
                self.assertIn('Save as image' if other == 'en' else '存成图片', other_page)
                self.assertIn('Model A' if language == 'en' else '模型 A', other_page)

    def test_cli_invalid_date(self):
        with temporary_directory() as directory:
            run = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--project', directory,
                                  '--today', '2026-02-30'], capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertIn('YYYY-MM-DD', run.stderr.decode('utf-8'))
            self.assertFalse((Path(directory) / 'fleet').exists())

    def test_long_names_and_deep_hierarchy_expand_without_truncating(self):
        with temporary_directory() as directory:
            source = '| Role | Department | Reports to | Assigned | How to call | Does | Delivers to |\n|---|---|---|---|---|---|---|\n'
            parent = 'Human'
            names = []
            for i in range(14):
                name = '岗位' + str(i) + 'LongUnbrokenRoleName' * 7
                source += '| {} | Department | {} | Model {} | Local | Work | out.md |\n'.format(name, parent, i)
                parent = name
                names.append(name)
            project = self.make_project(directory, source=source)
            svg = ET.fromstring(svg_from(org.render(project, 'en', '2026-11-15')))
            roles = svg.findall('{*}g')
            self.assertEqual([node.attrib['data-role'] for node in roles][1:], names)
            height = float(svg.attrib['height'])
            last_bottom = 0
            for node in roles:
                rectangle = node.find('{*}rect')
                top = float(rectangle.attrib['y'])
                bottom = top + float(rectangle.attrib['height'])
                self.assertGreaterEqual(top, last_bottom)
                last_bottom = bottom
                for text in node.findall('{*}text'):
                    self.assertLess(float(text.attrib['y']), bottom)
                    self.assertLessEqual(org.card._width(text.text or '') * float(text.attrib['font-size']),
                                         float(rectangle.attrib['width']) - 42)
            self.assertGreater(height, last_bottom)

    def test_shared_helpers_preserve_text_and_xml_validity(self):
        value = 'Alpha < & "\x01 ' + '没有空格的中文长名字' * 10
        lines = org.card.text_lines(value, 140, 20)
        self.assertGreater(len(lines), 3)
        fragment = '<svg>' + org.card.wrapped_text(value, 0, 20, 140, 20) + '</svg>'
        parsed = ET.fromstring(fragment)
        self.assertIn('Alpha < & "\ufffd', ' '.join(''.join(parsed.itertext()).split()))
        self.assertNotIn('\x01', fragment)
        for line in lines:
            self.assertLessEqual(org.card._width(line), 140 / 20)

    def test_absolute_paths_in_roster_are_hidden(self):
        with temporary_directory() as directory:
            project = self.make_project(directory)
            roster = project / 'fleet/members.md'
            source = roster.read_text(encoding='utf-8')
            source = source.replace('Model A', 'Model A; D:\\private\\notes.txt; /private/notes; \\\\server\\private\\notes')
            source = source.replace('Model B', 'Model B; ' + str(project / 'local-file.txt'))
            roster.write_text(source, encoding='utf-8')
            page = org.render(project, 'en', '2026-11-15')
            self.assertIn('[path hidden]', page)
            for path in ('D:\\private', '/private/notes', '\\\\server', str(project)):
                self.assertNotIn(path, page)

    def test_roster_resolved_outside_fleet_is_rejected(self):
        with temporary_directory() as directory:
            project = self.make_project(directory)
            roster = project / 'fleet/members.md'
            outside = Path(directory) / 'outside.md'
            outside.write_text((ROOT / 'tests/fixtures/roster.en.md').read_text(encoding='utf-8'), encoding='utf-8')
            real_resolve = Path.resolve

            def resolve(path, *args, **kwargs):
                return real_resolve(outside if path == roster else path, *args, **kwargs)

            # Emulate a symlink target without requiring Windows symlink rights.
            with mock.patch.object(Path, 'resolve', resolve):
                page = org.render(project, 'en', '2026-11-15')
            self.assertIn('No readable roster yet', page)
            self.assertNotIn('data-role="Manager"', page)

    def test_shared_document_escapes_title_and_filename(self):
        page = org.card.document('<svg viewBox="0 0 1 1"></svg>', 'en',
                                 '</title><script>bad()</script>', '\" onclick=\"bad()')
        self.assertIn('&lt;/title&gt;&lt;script&gt;', page)
        self.assertIn('data-filename="&quot; onclick=&quot;bad()"', page)
        self.assertNotIn('<script>bad()', page)


if __name__ == '__main__':
    unittest.main()
