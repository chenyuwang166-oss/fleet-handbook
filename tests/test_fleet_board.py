import html
from html.parser import HTMLParser
import importlib.util
import io
import json
from datetime import date, timedelta, datetime, time
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest import mock
from urllib.parse import unquote

from temp_support import temporary_directory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/fleet-chart/scripts/fleet_board.py'
spec = importlib.util.spec_from_file_location('fleet_board', SCRIPT)
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    @property
    def text(self):
        if self.tag in ('style', 'script'):
            return ''
        return ' '.join(' '.join(child.text if isinstance(child, Node) else child
                                 for child in self.children).split())

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.nodes()


class PageText(HTMLParser):
    """Read sections and records independently of their presentation tags."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                       'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    @property
    def text(self):
        return self.root.text

    def section(self, name):
        return next(node for node in self.root.nodes()
                    if node.tag == 'section' and node.attrs.get('id') == name)

    @property
    def rows(self):
        return [node for node in self.root.nodes() if 'data-task' in node.attrs]


TODAY = date(2026, 11, 17)


LANGUAGES = {
    'zh': {
        'roster': '成员.md', 'briefs': '任务书', 'deliveries': '交付',
        'decisions': '决定.md', 'output': '看板.html',
        'headers': '岗位|部门|汇报给|派驻|怎么调用|做什么|交付写进',
        'manager': '项目经理', 'writer': '作者', 'human': '人',
        'brief_title': '任务书', 'current': '现状', 'work': '要做的',
        'needed': '等我定', 'following': '文件地图',
        'decision': '定了什么', 'maker': '谁定',
        'question': '请人决定是否采用第二方案',
        'empty': '还没有记录，开始用以后会出现在这里',
        'nothing': '现在没有要你做的', 'date': '日期',
        'first_pass': '一次', 'busy': '忙', 'idle': '闲',
        'returned': '退回', 'mtime': '按文件时间', 'no_date': '没写日期',
        'footer': '按 fleet/ 里的文件生成；文件变了，重新生成就更新。',
        'states': ('派出', '在跑', '收到', '待审', '审过', '看不出'),
        'facts': (
            '看到的：已派发给作者，交付尚未收到。',
            '看到的：作者正在运行，本次调用未结束。',
            '看到的：交付已收到。',
            '看到的：本任务交付与日志已保存，按日志核对。',
            '看到的：交付已收到，另有独立审核报告。',
            '看到的：任务书已准备，尚无实际执行记录。',
        ),
        'future': '完成后等待审核；审核通过后再由项目经理收口。',
        'complete': '完成', 'notes': '说明',
        'success': '状态：成功；已收到交付，尚未审核。',
        'review_title': '独立审核',
        'review': '结论：交付齐全，质量通过，无必修项。',
        'review_input': '已对照原材料及交付',
    },
    'en': {
        'roster': 'members.md', 'briefs': 'task-briefs',
        'deliveries': 'deliveries', 'decisions': 'decisions.md',
        'output': 'board.html',
        'headers': 'Role|Department|Reports to|Assigned|How to call|Does|Delivers to',
        'manager': 'Manager', 'writer': 'Writer', 'human': 'Human',
        'brief_title': 'Task brief', 'current': 'Current state',
        'work': 'Work required', 'needed': 'Decisions needed',
        'following': 'File map', 'decision': 'Decision',
        'maker': 'Decision maker',
        'question': 'Human to decide whether to use option two',
        'empty': 'No records yet. They will show up here once you start.',
        'nothing': 'Nothing needs you right now.', 'date': 'Date',
        'first_pass': 'first', 'busy': 'Busy', 'idle': 'Idle',
        'returned': 'Returned', 'mtime': 'File time', 'no_date': 'No date',
        'footer': 'Built from the files in fleet/. Run it again to refresh.',
        'states': ('Dispatched', 'Running', 'Received',
                   'Awaiting review', 'Review passed', 'Unknown'),
        'facts': (
            'Observed: Dispatched to Writer; no delivery received yet.',
            'Observed: Writer is running; this invocation has not ended.',
            'Observed: Delivery received.',
            'Observed: The delivery and log are saved; check the log.',
            'Observed: Delivery received, with a separate independent review.',
            'Observed: The brief is prepared; no actual execution is recorded.',
        ),
        'future': 'After completion, wait for review; close only after review passes.',
        'complete': 'Complete', 'notes': 'Notes',
        'success': 'Status: succeeded; delivery received, not yet reviewed.',
        'review_title': 'Independent review',
        'review': 'Conclusion: delivery complete, quality passed, no required fixes.',
        'review_input': 'Checked source materials and delivery',
    },
}


def write(project, relative, content):
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode('utf-8'))


def write_task(project, words, current, work, filename='task.md', title='TARGET_TASK'):
    relative = words['briefs'] + '/' + filename
    write(project, 'fleet/' + relative,
          '# {}: {}\n\n## {}\n\n{}\n\n## {}\n\n{}\n'.format(
              words['brief_title'], title, words['current'], current, words['work'], work))
    return relative


def make_project(project, lang):
    """Use template names and existing dispatch prose, never a new status schema."""
    words = LANGUAGES[lang]
    header = '| ' + ' | '.join(words['headers'].split('|')) + ' |\n'
    roster = header + '|---|---|---|---|---|---|---|\n'
    roster += '| {} | Example team | {} | Model A | Local session | Coordinate | fleet/handoff.md |\n'.format(
        words['manager'], words['human'])
    roster += '| {} | Example team | {} | Model B | Verified local command | Draft | fleet/{}/03.md |\n'.format(
        words['writer'], words['manager'], words['deliveries'])
    write(project, 'fleet/' + words['roster'], roster)

    # The project card below is generated test data.
    write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n- {}\n\n## {}\n\nSECTION_BOUNDARY_SENTINEL\n'.format(
        words['needed'], words['question'], words['following']))
    decision_sections = ['# Decision log\n']
    for number in range(1, 8):
        decision_sections.append(
            '\n## 2026-11-{:02d} D{:03d}\n\n- {}: {}\n- {}: DECISION_{:03d}\n'.format(
                number, number, words['maker'], words['manager'],
                words['decision'], number))
    write(project, 'fleet/' + words['decisions'], ''.join(decision_sections))

    for index, fact in enumerate(words['facts'], 1):
        delivery = 'fleet/{}/{:02d}.md'.format(words['deliveries'], index)
        brief = '# {}: ASSIGNMENT_{:02d}\n\n## {}\n\n{}\n\n## {}\n\n'.format(
            words['brief_title'], index, words['current'], fact, words['work'])
        brief += '{} `{}`\n\n{}\n'.format(
            '交付' if lang == 'zh' else 'Deliver to', delivery, words['future'])
        write(project, 'fleet/{}/{:02d}.md'.format(words['briefs'], index), brief)
        if index in (3, 4, 5):
            write(project, delivery, '{}\n\nDraft {:02d}\n\n## {}\n\nEvidence checked.\n'.format(
                words['complete'], index, words['notes']))
    # This exact line is emitted by the existing fleet-dispatch API runner.
    write(project, 'fleet/{}/04.log'.format(words['deliveries']),
          'HTTP 200\n' + words['success'] + '\n')
    # The independent review includes a reference to the delivery.
    review = '# {}\n\n{}: 2026-11-17\n\n{}\n\n- {}: `fleet/{}/05.md`.\n'.format(
        words['review_title'], words['date'], words['review'],
        words['review_input'], words['deliveries'])
    review_name = '05-审核.md' if lang == 'zh' else '05-review.md'
    write(project, 'fleet/' + words['deliveries'] + '/' + review_name, review)
    return words


class FleetBoardTests(unittest.TestCase):
    def task_node(self, page, filename, section=None):
        parsed = PageText(page)
        root = parsed.section(section) if section else parsed.root
        rows = [row for row in root.nodes() if row.attrs.get('data-task') == filename]
        self.assertEqual(len(rows), 1, 'Expected one task row for ' + filename)
        return rows[0]

    def task_row(self, page, filename, section=None):
        return self.task_node(page, filename, section).text

    def render(self, project, lang, today=TODAY):
        return board.render(project, lang=lang, today=today)

    def reviewed_task(self, project, words, name, recorded_date=None,
                      round_number=None, passed=True, report_name=None):
        delivery = 'fleet/{}/{}.md'.format(words['deliveries'], name)
        work = ('交付到 `{}`。' if words is LANGUAGES['zh'] else
                'Deliver to `{}`.').format(delivery)
        relative = write_task(project, words, words['facts'][2], work, name + '.md')
        write(project, delivery, words['complete'] + '\n\nDelivery.\n')
        content = '# {}\n\n'.format(words['review_title'])
        if recorded_date:
            content += '{}: {}\n\n'.format(words['date'], recorded_date)
        if round_number:
            content += '{}: {}\n\n'.format(
                '审核轮次' if words is LANGUAGES['zh'] else 'Review round', round_number)
        if passed:
            content += words['review'] + '\n\n'
        else:
            content += ('结论：未通过，退回修订。\n\n' if words is LANGUAGES['zh'] else
                        'Conclusion: failed; changes required.\n\n')
        content += '- {}: `{}`.\n'.format(words['review_input'], delivery)
        report_name = report_name or name + ('-审核.md' if words is LANGUAGES['zh'] else '-review.md')
        write(project, 'fleet/' + words['deliveries'] + '/' + report_name, content)
        return relative, delivery

    def test_bilingual_projects_show_members_and_each_task_stage(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                page = self.render(project, lang)
                visible = PageText(page).text
                for member in (words['manager'], words['writer'], 'Model A', 'Model B'):
                    self.assertIn(member, visible)
                for number, state in enumerate(words['states'], 1):
                    with self.subTest(lang=lang, state=state):
                        filename = '{}/{:02d}.md'.format(words['briefs'], number)
                        section = 'done' if number == 5 else 'active'
                        self.assertIn(state, self.task_row(page, filename, section))
                self.assertNotIn(words['briefs'] + '/05.md',
                                 PageText(page).section('active').text)
                self.assertNotIn(str(project), page)
                self.assertNotIn(project.as_posix(), page)

    def test_waiting_stops_at_next_section_and_old_decision_log_is_not_a_fifth_block(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                page = self.render(project, lang)
                visible = PageText(page).text
                self.assertIn(words['question'], visible)
                self.assertNotIn('SECTION_BOUNDARY_SENTINEL', visible)
                for number in range(1, 8):
                    self.assertNotIn('DECISION_{:03d}'.format(number), visible)
                sections = [node.attrs.get('id') for node in PageText(page).root.nodes()
                            if node.tag == 'section']
                self.assertEqual(sections, ['waiting', 'active', 'done', 'people'])

    def test_waiting_is_sorted_by_leading_date_with_undated_items_last(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                who = ('谁在等：' if lang == 'zh' else 'Waiting: ') + words['manager']
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n'.format(words['needed']) +
                      '- NO_DATE_ITEM: choose a version.\n' +
                      '- 2026-11-16 RECENT_ITEM: choose a version.\n' +
                      '- 2026-11-01 OLDEST_ITEM; {}; choose a version.\n'.format(who) +
                      '- LATER_DATE_IN_TEXT 2026-10-01: choose a version.\n')
                waiting = PageText(self.render(project, lang)).section('waiting').text
                self.assertLess(waiting.index('OLDEST_ITEM'), waiting.index('RECENT_ITEM'))
                self.assertLess(waiting.index('RECENT_ITEM'), waiting.index('NO_DATE_ITEM'))
                self.assertLess(waiting.index('RECENT_ITEM'), waiting.index('LATER_DATE_IN_TEXT'))
                self.assertIn(words['manager'], waiting)
                self.assertNotIn(words['no_date'], waiting)
                self.assertNotIn(words['states'][-1], waiting)
                self.assertRegex(waiting, r'16\s*(?:天|days?)')
                section = PageText(self.render(project, lang)).section('waiting')
                rows = [node for node in section.nodes()
                        if 'wait-item' in node.attrs.get('class', '').split()]
                self.assertEqual(len(rows), 4)
                for marker in ('NO_DATE_ITEM', 'LATER_DATE_IN_TEXT'):
                    row = next(node for node in rows if marker in node.text)
                    self.assertIn('undated', row.attrs.get('class', '').split())
                    self.assertFalse(any('wait-age' in node.attrs.get('class', '').split()
                                         for node in row.nodes()))
                for marker in ('OLDEST_ITEM', 'RECENT_ITEM'):
                    row = next(node for node in rows if marker in node.text)
                    self.assertTrue(any('wait-age' in node.attrs.get('class', '').split()
                                        for node in row.nodes()))
                page = self.render(project, lang)
                rule = re.search(r'\.wait-item\.undated\s*\{([^}]+)\}', page)
                self.assertIsNotNone(rule)
                self.assertRegex(rule[1], r'display\s*:\s*block|grid-template-columns\s*:\s*(?:1fr|minmax\(0,\s*1fr\))')

    def test_explicit_no_action_notes_are_collapsed_and_do_not_count_as_waiting(self):
        examples = {
            'zh': (
                '当前没有需要人拍板的事项。',
                '暂无',
                '暂无需确认的决定。',
                '没有待确认事项。',
                '无待人确认事项。',
                '这个选择不再需要人确认。',
                '不再将旧版本选择视为待定事项。',
                '不再视为需要确认的事项。',
                '这项已不需要人做决定。',
            ),
            'en': (
                'Nothing pending for the project owner.',
                'No pending',
                'No pending decisions for the team.',
                'None pending at this time.',
                'There is nothing to decide now.',
                'Approval is no longer needed.',
                'A decision is no longer required.',
            ),
        }
        for lang, notes in examples.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                pending = ('待讨论与人确认' if lang == 'zh' else
                           'Await discussion and confirmation')
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n{}\n- {}\n'.format(
                    words['needed'], '\n'.join('- ' + note for note in notes), pending))
                section = PageText(self.render(project, lang)).section('waiting')
                rows = [node for node in section.nodes()
                        if 'wait-item' in node.attrs.get('class', '').split()]
                self.assertEqual(len(rows), 1)
                self.assertIn(pending, rows[0].text)
                details = [node for node in section.nodes()
                           if node.tag == 'details' and
                           'waiting-notes' in node.attrs.get('class', '').split()]
                self.assertEqual(len(details), 1)
                self.assertNotIn('open', details[0].attrs)
                summaries = [node.text for node in details[0].nodes() if node.tag == 'summary']
                expected = ('另有 {} 条说明写明当前不用你做' if lang == 'zh' else
                            '{} more notes say nothing is needed from you now').format(len(notes))
                self.assertEqual(summaries, [expected])
                self.assertEqual([node.text for node in details[0].nodes() if node.tag == 'li'],
                                 list(notes))
                self.assertNotIn(words['nothing'], section.text)
                self.assertEqual(self.run_status(project),
                                 '舰队：2 在跑 · 1 等你' if lang == 'zh' else
                                 'Fleet: 2 running · 1 waiting for you')

    def test_negated_no_action_claims_and_explicit_requests_still_need_you(self):
        examples = {
            'zh': (
                '并非当前没有待办，请确认第二方案。',
                '当前没有待办，请确认第二方案。',
                '当前没有生效条目；请人决定是否采用第二方案。',
            ),
            'en': (
                'It is not true that there is nothing to decide.',
                'No pending items; please confirm option two.',
                'No pending items; please confirm whether to choose option two.',
            ),
        }
        for lang, items in examples.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n{}\n'.format(
                    words['needed'], '\n'.join('- ' + item for item in items)))
                section = PageText(self.render(project, lang)).section('waiting')
                rows = [node for node in section.nodes()
                        if 'wait-item' in node.attrs.get('class', '').split()]
                self.assertEqual(len(rows), len(items))
                for item, row in zip(items, rows):
                    self.assertIn(item, row.text)
                self.assertFalse(any('waiting-notes' in node.attrs.get('class', '').split()
                                     for node in section.nodes()))
                self.assertNotIn(words['nothing'], section.text)
                self.assertEqual(self.run_status(project),
                                 ('舰队：2 在跑 · {} 等你' if lang == 'zh' else
                                  'Fleet: 2 running · {} waiting for you').format(len(items)))

    def test_only_no_action_notes_keep_the_nothing_message_and_zero_status_count(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                note = ('2026-11-02 谁在等：项目经理；当前没有待人决定的事项。' if lang == 'zh'
                        else '2026-11-02 Requested by: Manager; nothing pending for you now.')
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n- {}\n'.format(
                    words['needed'], note))
                section = PageText(self.render(project, lang)).section('waiting')
                self.assertIn(words['nothing'], section.text)
                self.assertFalse(any('wait-item' in node.attrs.get('class', '').split()
                                     for node in section.nodes()))
                notes = next(node for node in section.nodes()
                             if 'waiting-notes' in node.attrs.get('class', '').split())
                self.assertEqual([node.text for node in notes.nodes() if node.tag == 'li'], [note])
                self.assertIn('另有 1 条说明写明当前不用你做' if lang == 'zh' else
                              '1 more notes say nothing is needed from you now', notes.text)
                self.assertEqual(self.run_status(project),
                                 '舰队：2 在跑 · 0 等你' if lang == 'zh' else
                                 'Fleet: 2 running · 0 waiting for you')

    def test_collapsed_no_action_note_escapes_text_and_hides_absolute_paths(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                prefix = '当前没有待人决定的事项' if lang == 'zh' else 'Nothing pending'
                payload = '<img src=x onerror="bad"> & "quoted"'
                machine_path = 'C:\\sample\\restricted\\draft.md'
                note = '{}; {}; {}'.format(prefix, payload, machine_path)
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n- {}\n'.format(
                    words['needed'], note))
                page = self.render(project, lang)
                notes = next(node for node in PageText(page).section('waiting').nodes()
                             if 'waiting-notes' in node.attrs.get('class', '').split())
                self.assertIn(payload, notes.text)
                self.assertIn(html.escape(payload), page)
                self.assertNotIn(payload, page)
                self.assertFalse(any(node.tag == 'img' for node in notes.nodes()))
                self.assertNotIn(machine_path, page)
                self.assertNotIn(html.escape(machine_path), page)

    def test_existing_empty_decisions_section_uses_the_exact_nothing_message(self):
        for lang, words in LANGUAGES.items():
            for content in ('', '- 〔待定〕\n'):
                with self.subTest(lang=lang, content=content), temporary_directory() as directory:
                    project = Path(directory)
                    write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n{}\n## {}\n\nOTHER_SECTION\n'.format(
                        words['needed'], content, words['following']))
                    waiting = PageText(self.render(project, lang)).section('waiting').text
                    self.assertIn(words['nothing'], waiting)
                    self.assertNotIn('OTHER_SECTION', waiting)
                    self.assertNotIn(words['empty'], waiting)

    def test_done_window_has_today_and_six_previous_days_and_excludes_future(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                records = {}
                for name, recorded_date in (('start', '2026-11-11'), ('end', '2026-11-17'),
                                            ('old', '2026-11-10'), ('future', '2026-11-18')):
                    records[name] = self.reviewed_task(project, words, name, recorded_date)[0]
                page = self.render(project, lang)
                for name in ('start', 'end'):
                    self.task_node(page, records[name], 'done')
                found = [node.attrs['data-task'] for node in PageText(page).rows]
                self.assertNotIn(records['old'], found)
                self.assertNotIn(records['future'], found)
                done = PageText(page).section('done').text
                self.assertRegex(done, r'这周审过\s*2\s*单' if lang == 'zh' else
                                 r'2\s+passed\s+review\s+this\s+week')

    def test_explicit_review_date_precedes_delivery_date_and_file_time(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                relative, delivery = self.reviewed_task(project, words, 'dated', '2026-11-17')
                write(project, delivery, '{}: 2020-01-01\n\nDelivery.\n'.format(words['date']))
                old = date(2020, 1, 1)
                stamp = datetime.combine(old, time()).timestamp()
                os.utime(project / delivery, (stamp, stamp))
                self.task_node(self.render(project, lang), relative, 'done')

    def test_undated_delivery_falls_back_to_its_file_time_and_marks_the_block(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                relative, delivery = self.reviewed_task(project, words, 'undated')
                moment = datetime(2026, 11, 14, 12).timestamp()
                os.utime(project / delivery, (moment, moment))
                page = self.render(project, lang)
                self.task_node(page, relative, 'done')
                self.assertIn(words['mtime'].casefold(), PageText(page).section('done').text.casefold())
                summary = next(node for node in PageText(page).section('done').nodes()
                               if 'weekly' in node.attrs.get('class', '').split())
                self.assertIn(words['mtime'].casefold(), summary.text.casefold())
                self.assertIn('·', summary.text)
                older = datetime(2026, 11, 10, 12).timestamp()
                os.utime(project / delivery, (older, older))
                page = self.render(project, lang)
                self.assertNotIn(relative, [node.attrs['data-task'] for node in PageText(page).rows])

    def test_delivery_or_log_date_is_used_before_file_time(self):
        for lang, words in LANGUAGES.items():
            for source in ('delivery', 'log'):
                with self.subTest(lang=lang, source=source), temporary_directory() as directory:
                    project = Path(directory)
                    relative, delivery = self.reviewed_task(project, words, 'recorded')
                    record = '{}: 2026-11-17\n\n'.format(words['date'])
                    if source == 'delivery':
                        write(project, delivery, record + 'Delivery.\n')
                    else:
                        write(project, 'fleet/' + words['deliveries'] + '/recorded.log',
                              record + words['success'] + '\n')
                    old = datetime(2020, 1, 1, 12).timestamp()
                    os.utime(project / delivery, (old, old))
                    page = self.render(project, lang)
                    self.task_node(page, relative, 'done')
                    self.assertNotIn(words['mtime'].casefold(),
                                     PageText(page).section('done').text.casefold())

    def test_first_pass_ratio_is_hidden_without_explicit_first_review_evidence(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                self.reviewed_task(project, words, 'unknown-history', TODAY.isoformat())
                done = PageText(self.render(project, lang)).section('done').text
                self.assertNotRegex(done, r'(?i)一次(?:就)?过|first[- ](?:review[- ]?)?pass')
                self.assertNotIn('0%', done)

    def test_first_pass_ratio_uses_the_first_explicit_review_of_each_task(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                self.reviewed_task(project, words, 'one', '2026-11-15', round_number=1)
                self.reviewed_task(project, words, 'two', '2026-11-15', round_number=1,
                                   passed=False, report_name='two-first-review.md')
                self.reviewed_task(project, words, 'two', '2026-11-16', round_number=2,
                                   report_name='two-second-review.md')
                done = PageText(self.render(project, lang)).section('done').text
                self.assertRegex(done, r'(?i)一次(?:就)?过|first[- ](?:review[- ]?)?pass')
                self.assertIn('50%', done)

    def test_explicit_task_number_joins_briefs_but_preserves_an_unreviewed_new_version(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                _, delivery = self.reviewed_task(project, words, 'original-v1', TODAY.isoformat(), 1)
                work = ('交付到 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
                for filename in ('original-v1.md', 'review-v1.md', 'patch-v1.md'):
                    write_task(project, words, words['facts'][2], work, filename, '001 Annual draft v1')
                page = self.render(project, lang)
                done_rows = [node for node in PageText(page).section('done').nodes()
                             if 'data-task' in node.attrs]
                self.assertEqual(len(done_rows), 1)
                self.assertFalse(any('data-task' in node.attrs
                                     for node in PageText(page).section('active').nodes()))
                current_delivery = 'fleet/' + words['deliveries'] + '/draft-v2.md'
                current_work = ('交付到 `{}`。' if lang == 'zh' else
                                'Deliver to `{}`.').format(current_delivery)
                current = write_task(project, words, words['facts'][1], current_work,
                                     'revision-v2.md', '001 Annual draft v2')
                page = self.render(project, lang)
                self.assertEqual(self.task_node(page, current, 'active').attrs['data-status'], 'running')
                done_rows = [node for node in PageText(page).section('done').nodes()
                             if 'data-task' in node.attrs]
                self.assertEqual(len(done_rows), 0)

    def test_review_date_and_history_do_not_confuse_first_pass_or_new_output(self):
        for lang, words in LANGUAGES.items():
            for declaration in ('narrative', 'late-round-one'):
                with self.subTest(lang=lang, declaration=declaration), temporary_directory() as directory:
                    project = Path(directory)
                    delivery = 'fleet/' + words['deliveries'] + '/fresh-v2.md'
                    old_delivery = 'fleet/' + words['deliveries'] + '/fresh-v1.md'
                    work = ('新稿保存到 `{}`。保留旧稿 `{}`。' if lang == 'zh' else
                            'The draft is saved by host to `{}`. Preserve old drafts `{}`.').format(
                                delivery, old_delivery)
                    relative = write_task(project, words, words['facts'][2], work)
                    write(project, delivery, 'New delivery.\n')
                    write(project, old_delivery, 'Old delivery.\n')
                    previous = '# {}\n\n{}: 2026-11-15\n\n{}\n\n- {}: `{}`.\n'.format(
                        words['review_title'], words['date'],
                        '结论：未通过，退回修订。' if lang == 'zh' else 'Conclusion: failed; changes required.',
                        words['review_input'], delivery)
                    write(project, 'fleet/' + words['deliveries'] + '/earlier-review.md', previous)
                    declaration_text = ('首审未过，见 2026-11-15 的报告。' if lang == 'zh' else
                                        'First review failed; see the report dated 2026-11-15.')
                    if declaration == 'late-round-one':
                        declaration_text += '\n{}: 1'.format('审核轮次' if lang == 'zh' else 'Review round')
                    current = '# {}\n\n## Materials 2026-11-01\n\n{}: 2026-11-17\n\n{}\n\n{}\n\n- {}: `{}`.\n'.format(
                        words['review_title'], words['date'], words['review'], declaration_text,
                        words['review_input'], delivery)
                    write(project, 'fleet/' + words['deliveries'] + '/latest-review.md', current)
                    page = self.render(project, lang)
                    node = self.task_node(page, relative, 'done')
                    self.assertEqual(node.attrs['data-status'], 'passed')
                    self.assertIn('2026-11-17', node.text)
                    links = [unquote(child.attrs['href']) for child in node.nodes()
                             if child.tag == 'a' and 'href' in child.attrs]
                    self.assertIn(delivery.removeprefix('fleet/'), links)
                    self.assertNotIn(old_delivery.removeprefix('fleet/'), links)
                    done = PageText(page).section('done').text
                    self.assertNotRegex(done, r'(?i)一次(?:就)?过|first[- ](?:review[- ]?)?pass')

    def test_exit_code_proves_run_ended_but_only_nonzero_marks_failure(self):
        for lang, words in LANGUAGES.items():
            for code in (0, 1):
                with self.subTest(lang=lang, code=code), temporary_directory() as directory:
                    project = Path(directory)
                    relative = write_task(project, words, words['facts'][5], words['future'])
                    write(project, 'fleet/' + words['deliveries'] + '/task.log',
                          'Exit code: {}\n'.format(code))
                    node = self.task_node(self.render(project, lang), relative, 'active')
                    self.assertEqual(node.attrs['data-blocked'], 'true' if code else 'false')
                    self.assertEqual(node.attrs['data-status'], 'unknown')
                    self.assertIn('跑完: 是' if lang == 'zh' else 'Run ended: Yes', node.text)
                    self.assertNotEqual(node.attrs['data-status'], 'pending')
                    if code:
                        self.assertIn('blocked', node.attrs.get('class', '').split())

    def test_busy_and_idle_use_only_dispatched_or_running_tasks_and_show_assigned(self):
        for lang, words in LANGUAGES.items():
            for state_index, busy in ((0, True), (1, True), (2, False), (5, False)):
                with self.subTest(lang=lang, state=state_index), temporary_directory() as directory:
                    project = Path(directory)
                    make_project(project, lang)
                    # Replace every current state so fixture file presence alone cannot make a role busy.
                    for index in range(1, 7):
                        filename = '{:02d}.md'.format(index)
                        current = words['facts'][state_index] if index == 1 else words['facts'][5]
                        current += '\n{}: {}'.format('派给' if lang == 'zh' else 'Assigned to', words['writer'])
                        write_task(project, words, current, words['future'], filename)
                    page = self.render(project, lang)
                    people = PageText(page).section('people')
                    roles = [node for node in people.nodes() if node.attrs.get('data-role') == words['writer']]
                    self.assertEqual(len(roles), 1)
                    self.assertEqual(roles[0].attrs.get('data-busy'), 'true' if busy else 'false')
                    self.assertIn(words['busy'] if busy else words['idle'], roles[0].text)
                    self.assertIn('Model B', roles[0].text)
                    manager = next(node for node in people.nodes()
                                   if node.attrs.get('data-role') == words['manager'])
                    self.assertEqual(manager.attrs.get('data-busy'), 'false')
                    self.assertIn(words['idle'], manager.text)
                    self.assertIn('Model A', manager.text)
                    self.assertIn(words['human'], people.text)

    def test_member_assignment_stops_at_the_first_semicolon_and_keeps_full_title(self):
        for lang, words in LANGUAGES.items():
            for separator in ('；', ';', ''):
                with self.subTest(lang=lang, separator=separator), temporary_directory() as directory:
                    project = Path(directory)
                    make_project(project, lang)
                    first = '主派驻模型' if lang == 'zh' else 'Primary model'
                    rest = '备用派驻模型；另一配置' if lang == 'zh' else 'Fallback model; another setting'
                    assignment = first + separator + rest if separator else first
                    roster = (project / 'fleet' / words['roster']).read_text(encoding='utf-8')
                    write(project, 'fleet/' + words['roster'], roster.replace('Model B', assignment))
                    page = self.render(project, lang)
                    role = next(node for node in PageText(page).section('people').nodes()
                                if node.attrs.get('data-role') == words['writer'])
                    assigned = [node for node in role.nodes() if 'title' in node.attrs]
                    self.assertEqual(len(assigned), 1)
                    self.assertEqual(assigned[0].text, first)
                    self.assertEqual(assigned[0].attrs['title'], assignment)
                    self.assertNotIn(rest, role.text)
                    self.assertIn(html.escape(assignment), page)

    def test_member_assignment_title_escapes_text_and_hides_absolute_paths(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                first = '<b>Model & "primary"</b>'
                rest = '<script>fallback()</script>'
                paths = ('C:\\sample\\restricted\\model.md', '/sample/restricted/model.md')
                assignment = '{}; {} {} {}'.format(first, rest, *paths)
                roster = (project / 'fleet' / words['roster']).read_text(encoding='utf-8')
                write(project, 'fleet/' + words['roster'], roster.replace('Model B', assignment))
                page = self.render(project, lang)
                role = next(node for node in PageText(page).section('people').nodes()
                            if node.attrs.get('data-role') == words['writer'])
                assigned = next(node for node in role.nodes() if 'title' in node.attrs)
                self.assertEqual(assigned.text, first)
                self.assertIn(first + '; ' + rest, assigned.attrs['title'])
                self.assertNotIn(rest, assigned.text)
                self.assertFalse(any(node.tag in ('b', 'script') for node in assigned.nodes()))
                for payload in (first, rest):
                    self.assertNotIn(payload, page)
                    self.assertIn(html.escape(payload), page)
                for path in paths:
                    self.assertNotIn(path, page)
                    self.assertNotIn(html.escape(path), page)

    def test_observed_assignee_wins_over_future_manager_instructions(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                page = self.render(project, lang)
                for index in (1, 2):
                    row = self.task_row(page, '{}/{:02d}.md'.format(words['briefs'], index), 'active')
                    self.assertIn(words['writer'], row)
                    self.assertIn('Model B', row)
                    self.assertNotIn(words['manager'], row)
                row = self.task_row(page, words['briefs'] + '/06.md', 'active')
                self.assertNotIn(words['manager'], row)

    def test_full_chart_link_is_relative_and_only_shown_when_the_file_exists(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                filename = '组织图.md' if lang == 'zh' else 'chart.md'
                def links(page):
                    return [node.attrs['href'] for node in PageText(page).section('people').nodes()
                            if node.tag == 'a' and 'href' in node.attrs]
                self.assertFalse(any('chart.md' in item or '%E7%BB%84' in item
                                     for item in links(self.render(project, lang))))
                write(project, 'fleet/' + filename, '# Chart\n')
                targets = [unquote(item).replace('\\', '/') for item in links(self.render(project, lang))]
                self.assertTrue(any(item.endswith(filename) for item in targets))
                self.assertTrue(all(not re.match(r'^[a-z]+:|^/', item, re.I) for item in targets))

    def test_render_accepts_iso_date_and_cli_rejects_an_invalid_today(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                relative, _ = self.reviewed_task(project, words, 'fixed-day', '2026-11-17')
                self.task_node(self.render(project, lang, '2026-11-17'), relative, 'done')
                run = subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), '--project', str(project),
                                      '--lang', lang, '--today', '2026-02-30'],
                                     capture_output=True, timeout=10)
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse((project / 'fleet' / words['output']).exists())

    def test_duration_requires_an_explicit_start_and_end_timestamp_pair(self):
        for lang, words in LANGUAGES.items():
            for complete in (False, True):
                with self.subTest(lang=lang, complete=complete), temporary_directory() as directory:
                    project = Path(directory)
                    timing = ('开始时间：2026-11-17 10:00:00\n' if lang == 'zh' else
                              'Started at: 2026-11-17 10:00:00\n')
                    if complete:
                        timing += ('结束时间：2026-11-17 11:30:00\n' if lang == 'zh' else
                                   'Finished at: 2026-11-17 11:30:00\n')
                    relative = write_task(project, words, words['facts'][0] + '\n' + timing,
                                          words['future'])
                    row = self.task_row(self.render(project, lang), relative, 'active')
                    if complete:
                        self.assertRegex(row, r'(?i)(?:1\.5\s*(?:小时|h(?:ours?)?)|90\s*(?:分钟|min(?:utes?)?)|1\s*(?:小时|h(?:our)?)\s*30)')
                    else:
                        self.assertIn(words['states'][-1], row)

    def test_task_title_is_escaped(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                relative, delivery = self.reviewed_task(project, words, 'markup', TODAY.isoformat())
                title = 'TASK <img src=x onerror="bad"> & review'
                work = ('交付到 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
                write(project, 'fleet/' + relative, '# {}: {}\n\n## {}\n\n{}\n\n## {}\n\n{}\n'.format(
                    words['brief_title'], title, words['current'], words['facts'][2], words['work'], work))
                page = self.render(project, lang)
                self.assertIn(html.escape(title), page)
                self.assertNotIn(title, page)
                self.assertFalse(any(node.tag in ('img', 'script') for node in PageText(page).root.nodes()))

    def test_missing_files_render_empty_sections(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                page = self.render(project, lang)
                self.assertIn('<html', page.lower())
                for name in ('waiting', 'active', 'done', 'people'):
                    self.assertIn(LANGUAGES[lang]['empty'], PageText(page).section(name).text)
                self.assertNotIn(str(project), page)
                # A partial project must still show its task with all other files missing.
                words = LANGUAGES[lang]
                write(project, 'fleet/' + words['briefs'] + '/only.md',
                      '# {}: ONLY_TASK\n\n## {}\n\nNo execution evidence.\n'.format(
                          words['brief_title'], words['current']))
                page = self.render(project, lang)
                self.assertIn('ONLY_TASK', PageText(page).text)
                self.assertIn(words['states'][-1], self.task_row(page, words['briefs'] + '/only.md'))
                self.assertIn(words['empty'], PageText(page).text)

    def test_future_acceptance_instructions_are_not_execution_evidence(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                page = self.render(project, lang)
                row = self.task_row(page, words['briefs'] + '/06.md')
                self.assertIn(words['states'][-1], row)
                self.assertEqual(self.task_node(page, words['briefs'] + '/06.md').attrs['data-status'], 'unknown')

    def test_explicit_output_filename_with_fleet_prefix_can_have_independent_review(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                delivery = 'fleet/' + words['deliveries'] + '/final-v2.md'
                work = ('交付到 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
                relative = write_task(project, words, words['facts'][-1], work)
                write(project, delivery, words['complete'] + '\n\nFinal draft.\n')
                review_name = 'final-v2-审核.md' if lang == 'zh' else 'final-v2-review.md'
                write(project, 'fleet/' + words['deliveries'] + '/' + review_name,
                      '# {}\n\n{}: 2026-11-17\n\n{}\n\n- {}: `{}`.\n'.format(
                          words['review_title'], words['date'], words['review'],
                          words['review_input'], delivery))
                page = self.render(project, lang)
                row = self.task_row(page, relative, 'done')
                self.assertIn(words['states'][4], row)
                self.assertIn(review_name, row)
                links = [unquote(node.attrs['href']) for node in self.task_node(page, relative).nodes()
                         if node.tag == 'a' and 'href' in node.attrs]
                self.assertIn(delivery.removeprefix('fleet/'), links)
                self.assertTrue(all(not re.match(r'^[a-z]+:|^/', item, re.I) for item in links))

    def test_only_the_deliverable_counts_as_received(self):
        for lang, words in LANGUAGES.items():
            base = 'fleet/' + words['deliveries'] + '/01'
            delivery = base + '.md'
            notes = base + ('-说明.md' if lang == 'zh' else '-notes.md')
            work = ('交付成品到 `{}`，另存说明到 `{}`。' if lang == 'zh' else
                    'Save the deliverable to `{}` and the notes to `{}`.').format(delivery, notes)
            incomplete, blocked = (('没完成：缺少第二页', '卡在哪：缺少原始数据') if lang == 'zh'
                                   else ('Incomplete: the second page is missing',
                                         'Blocked: the source data is missing'))
            for has_delivery, first_line in (
                    (False, incomplete), (False, blocked), (False, words['complete']),
                    (True, words['complete']), (True, None)):
                with self.subTest(lang=lang, delivery=has_delivery, notes=first_line), temporary_directory() as directory:
                    project = Path(directory)
                    relative = write_task(project, words, words['facts'][2], work)
                    if has_delivery:
                        write(project, delivery, '# Final report\n')
                    if first_line:
                        write(project, notes, '{}\n\n{}\n\n# {}\n\n{}\n\n{}: `{}`\n'.format(
                            first_line, blocked, words['review_title'], words['review'],
                            words['review_input'], delivery))
                    row = self.task_node(self.render(project, lang), relative, 'active')
                    if has_delivery:
                        self.assertEqual(row.attrs['data-status'], 'received')
                        self.assertEqual(row.attrs['data-blocked'], 'false')
                    else:
                        self.assertNotIn(row.attrs['data-status'], ('received', 'pending', 'passed'))
                        if first_line in (incomplete, blocked):
                            self.assertIn(first_line, row.text)
                    labels = board.LABELS[lang]
                    receipt = labels['yes'] if has_delivery else labels['no']
                    self.assertIn(labels['receipt'] + ': ' + receipt, row.text)

    def test_incomplete_note_overrides_passing_review_and_escapes_badge_text(self):
        for lang, words in LANGUAGES.items():
            incomplete = '没完成' if lang == 'zh' else 'Incomplete'
            first_line = '<b>{}</b>: draft & "proof"'.format(incomplete)
            for has_delivery in (False, True):
                with self.subTest(lang=lang, delivery=has_delivery), temporary_directory() as directory:
                    project = Path(directory)
                    relative, delivery = self.reviewed_task(project, words, 'draft', TODAY)
                    if not has_delivery:
                        (project / delivery).unlink()
                    suffix = '-说明.md' if lang == 'zh' else '-notes.md'
                    write(project, delivery[:-3] + suffix, first_line + '\n' + words['complete'])

                    page = self.render(project, lang)
                    row = self.task_node(page, relative, 'active')
                    self.assertEqual(row.attrs['data-blocked'], 'true')
                    self.assertNotEqual(row.attrs['data-status'], 'passed')
                    labels = board.LABELS[lang]
                    receipt = labels['yes'] if has_delivery else labels['no']
                    self.assertIn(labels['receipt'] + ': ' + receipt, row.text)
                    badge, = (node for node in row.nodes() if node.attrs.get('class') == 'badge')
                    self.assertEqual(badge.text, first_line)
                    self.assertIn(html.escape(first_line), page)
                    self.assertNotIn(first_line, page)
                    self.assertFalse(any(node.attrs.get('data-task') == relative
                                         for node in PageText(page).section('done').nodes()))

    def test_complete_note_without_deliverable_shows_missing_despite_passing_review(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                relative, delivery = self.reviewed_task(project, words, 'draft', TODAY)
                (project / delivery).unlink()
                suffix = '-说明.md' if lang == 'zh' else '-notes.md'
                write(project, delivery[:-3] + suffix, words['complete'] + '\nBlocked: SECOND_LINE')

                row = self.task_node(self.render(project, lang), relative, 'active')
                labels = board.LABELS[lang]
                self.assertIn(labels['receipt'] + ': ' + labels['no'], row.text)
                self.assertNotIn(row.attrs['data-status'], ('received', 'pending', 'passed'))
                self.assertEqual(row.attrs['data-blocked'], 'false')
                badge, = (node for node in row.nodes() if node.attrs.get('class') == 'badge')
                self.assertEqual(badge.text, '缺成品' if lang == 'zh' else 'Missing deliverable')
                self.assertNotIn('SECOND_LINE', row.text)

    def test_review_document_cannot_be_received_as_a_declared_or_legacy_deliverable(self):
        for lang, words in LANGUAGES.items():
            for legacy in (False, True):
                with self.subTest(lang=lang, legacy=legacy), temporary_directory() as directory:
                    project = Path(directory)
                    base = 'fleet/' + words['deliveries'] + '/preview'
                    if legacy:
                        report = base + '.md'
                        work = '整理草稿。' if lang == 'zh' else 'Prepare the draft.'
                    else:
                        report = 'fleet/' + words['deliveries'] + '/feedback.md'
                        work = ('保存成品到 `{}.pdf`，另存审核意见到 `{}`。' if lang == 'zh' else
                                'Save the product to `{}.pdf` and review feedback to `{}`.').format(base, report)
                    relative = write_task(project, words, words['facts'][2], work, 'preview.md')
                    write(project, report, '# {}\n\n{}\n'.format(words['review_title'], words['review']))
                    first_line = '没完成：缺一页' if lang == 'zh' else 'Incomplete: a page is missing'
                    write(project, base + ('-说明.md' if lang == 'zh' else '-notes.md'), first_line)

                    row = self.task_node(self.render(project, lang), relative, 'active')
                    labels = board.LABELS[lang]
                    self.assertIn(labels['receipt'] + ': ' + labels['no'], row.text)
                    self.assertEqual(row.attrs['data-blocked'], 'true')
                    self.assertIn(first_line, row.text)

                    write(project, base + ('.md' if legacy else '.pdf'), 'Final product.')
                    row = self.task_node(self.render(project, lang), relative, 'active')
                    self.assertIn(labels['receipt'] + ': ' + labels['yes'], row.text)

    def test_binary_deliverable_requires_the_exact_file_named_in_the_brief(self):
        for lang, words in LANGUAGES.items():
            base = 'fleet/' + words['deliveries'] + '/01'
            target = base + '.png'
            notes = base + ('-说明.md' if lang == 'zh' else '-notes.md')
            work = ('交付图像到 `{}`，另存说明到 `{}`。' if lang == 'zh' else
                    'Save the image to `{}` and the notes to `{}`.').format(target, notes)
            for has_image, has_notes in ((True, False), (True, True), (False, True)):
                with self.subTest(lang=lang, image=has_image, notes=has_notes), temporary_directory() as directory:
                    project = Path(directory)
                    write_task(project, words, words['facts'][-1], work, filename='01.md')
                    write(project, base + '.md', '# Old draft\n')
                    if has_image:
                        (project / target).write_bytes(b'\x89PNG\r\n\x1a\n')
                    if has_notes:
                        write(project, notes, words['complete'] + '\n')
                    task, = board.task_records(project, lang)
                    self.assertEqual(task['received'], has_image)
                    self.assertEqual(task['deliveries'], [target.removeprefix('fleet/')] if has_image else [])

    def test_preserved_old_delivery_and_its_review_do_not_complete_a_new_assignment(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                old = 'fleet/' + words['deliveries'] + '/v1.md'
                new = 'fleet/' + words['deliveries'] + '/v2.md'
                if lang == 'zh':
                    work = '另存新交付 `{}`；保留旧稿 `{}`。'.format(new, old)
                else:
                    work = 'Save new `{}`; preserve old `{}`.'.format(new, old)
                relative = write_task(project, words, words['facts'][-1], work)
                write(project, old, words['complete'] + '\n\nOld draft.\n')
                review_name = 'v1-审核.md' if lang == 'zh' else 'v1-review.md'
                write(project, 'fleet/' + words['deliveries'] + '/' + review_name,
                      '# {}\n\n{}\n\n- {}: `{}`.\n'.format(
                          words['review_title'], words['review'], words['review_input'], old))
                page = self.render(project, lang)
                row = self.task_row(page, relative, 'active')
                self.assertIn(words['states'][-1], row)
                self.assertEqual(self.task_node(page, relative).attrs['data-status'], 'unknown')

    def test_negated_status_and_an_unrelated_delivery_are_not_review_evidence(self):
        for lang, words in LANGUAGES.items():
            negatives = (('正在运行：无。', '当前任务未等待审核。') if lang == 'zh'
                         else ('Running: None.', 'The current task is not awaiting review.'))
            for current in negatives:
                with self.subTest(lang=lang, current=current), temporary_directory() as directory:
                    project = Path(directory)
                    relative = write_task(project, words, current, words['future'])
                    page = self.render(project, lang)
                    row = self.task_row(page, relative)
                    self.assertIn(words['states'][-1], row)
                    self.assertNotIn(words['states'][1], row)
                    self.assertNotIn(words['states'][3], row)
                    self.assertEqual(self.task_node(page, relative).attrs['data-status'], 'unknown')
            with self.subTest(lang=lang, unrelated_delivery=True), temporary_directory() as directory:
                project = Path(directory)
                delivery = 'fleet/' + words['deliveries'] + '/author.md'
                work = ('交付到 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
                relative = write_task(project, words, words['facts'][-1], work)
                write(project, delivery, words['complete'] + '\n\nAuthor draft.\n')
                write(project, 'fleet/' + words['deliveries'] + '/other.md',
                      '# Other delivery\n\nConclusion: passed\n\nSource: `{}`.\n'.format(delivery))
                page = self.render(project, lang)
                row = self.task_row(page, relative)
                self.assertIn(words['states'][2], row)
                self.assertEqual(self.task_node(page, relative).attrs['data-status'], 'received')

    def test_log_scope_failed_run_and_rejected_review_stay_distinct(self):
        for lang, words in LANGUAGES.items():
            for scenario in ('other_directory', 'blocked_after_success', 'rejected_review'):
                with self.subTest(lang=lang, scenario=scenario), temporary_directory() as directory:
                    project = Path(directory)
                    delivery = 'fleet/' + words['deliveries'] + '/01.md'
                    work = ('交付到 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
                    relative = write_task(project, words, words['facts'][-1], work, filename='01.md')
                    write(project, delivery, words['complete'] + '\n\nAuthor response.\n')
                    if scenario == 'other_directory':
                        other = 'fleet/' + words['deliveries'] + '/other/'
                        write(project, other + '01-review.md',
                              '# {}\n\n{}\n'.format(words['review_title'], words['review']))
                        write(project, other + '01.log', words['success'] + '\n')
                        expected = words['states'][2]
                    elif scenario == 'blocked_after_success':
                        write(project, 'fleet/' + words['deliveries'] + '/01.log',
                              words['success'] + '\nBlocked: API invocation timed out; '
                              'current output has not been accepted.\n')
                        expected = words['states'][-1]
                    else:
                        conclusion = (
                            '结论：未通过，退作者小修后复审。已收到完整回复；尚未形成最终交付。'
                            if lang == 'zh' else
                            'Conclusion: failed; return to the author for small fixes and re-review. '
                            'Full response received; final delivery not yet formed.')
                        review_name = '01-审核.md' if lang == 'zh' else '01-review.md'
                        write(project, 'fleet/' + words['deliveries'] + '/' + review_name,
                              '# {}\n\n{}: 2026-11-17\n\n{}\n\n- {}: `{}`; `fleet/{}`.\n'.format(
                                  words['review_title'], words['date'], conclusion, words['review_input'],
                                  delivery, relative))
                        expected = words['returned']
                    page = self.render(project, lang)
                    row = self.task_row(page, relative, 'active')
                    self.assertIn(expected, row)
                    if scenario != 'other_directory':
                        node = self.task_node(page, relative)
                        self.assertEqual(node.attrs.get('data-blocked'), 'true')
                        self.assertIn('blocked', node.attrs.get('class', '').split())

    def test_dynamic_text_is_escaped_and_machine_paths_are_not_exposed(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                payload = '<script>alert("member")</script> & local'
                roster_path = project / 'fleet' / words['roster']
                roster = roster_path.read_text(encoding='utf-8').replace('Model B', payload)
                roster = roster.replace('Verified local command', 'tool --project ' + str(project))
                write(project, 'fleet/' + words['roster'], roster)
                question = '<img src=x onerror="bad"> & approve'
                windows_path = 'C:\\sample\\restricted\\draft.md'
                unix_path = '/sample/restricted/draft.md'
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n- {}\n- {}\n- {}\n- {}\n'.format(
                    words['needed'], question, str(project), windows_path, unix_path))
                page = self.render(project, lang)
                self.assertIn(html.escape(payload), page)
                self.assertIn(html.escape(question), page)
                self.assertNotIn(payload, page)
                self.assertNotIn(question, page)
                for path in (str(project), project.as_posix(), windows_path, unix_path):
                    self.assertNotIn(path, page)
                    self.assertNotIn(html.escape(path), page)

    def test_cli_creates_default_local_filename_for_both_languages(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = make_project(project, lang)
                run = subprocess.run(
                    [sys.executable, '-I', '-B', str(SCRIPT), '--project', str(project), '--lang', lang,
                     '--today', TODAY.isoformat()],
                    capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr.decode('utf-8'))
                page = (project / 'fleet' / words['output']).read_text(encoding='utf-8')
                self.assertIn(words['question'], PageText(page).text)
                self.assertNotIn(str(project), page)

    def test_latest_review_alone_decides_returned_or_passed_and_the_weekly_count(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                returned, _ = self.reviewed_task(
                    project, words, 'returned', '2026-11-15', 1,
                    report_name='returned-first-review.md')
                self.reviewed_task(project, words, 'returned', '2026-11-17', 2,
                                   passed=False, report_name='returned-second-review.md')
                passed, _ = self.reviewed_task(
                    project, words, 'passed', '2026-11-15', 1, passed=False,
                    report_name='passed-first-review.md')
                self.reviewed_task(project, words, 'passed', '2026-11-17', 2,
                                   report_name='passed-second-review.md')
                page = self.render(project, lang)
                node = self.task_node(page, returned, 'active')
                self.assertEqual(node.attrs['data-status'], 'returned')
                self.assertEqual(node.attrs['data-blocked'], 'true')
                self.assertIn('blocked', node.attrs.get('class', '').split())
                self.assertIn(words['returned'], node.text)
                self.assertEqual(self.task_node(page, passed, 'done').attrs['data-status'], 'passed')
                done = PageText(page).section('done')
                rows = [node for node in done.nodes() if 'data-task' in node.attrs]
                self.assertEqual([node.attrs['data-task'] for node in rows], [passed])
                self.assertIn(words['states'][4], rows[0].text)
                self.assertIn('这周审过 1 单' if lang == 'zh' else
                              '1 passed review this week', done.text)

    def test_footer_uses_the_refresh_instruction(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                footers = [node for node in PageText(self.render(Path(directory), lang)).root.nodes()
                           if node.tag == 'footer']
                self.assertEqual([node.text for node in footers], [words['footer']])

    def test_old_passed_version_cannot_hide_a_returned_revision_of_the_same_task(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                old, old_delivery = self.reviewed_task(project, words, 'draft-v1', '2026-11-15', 1)
                current, current_delivery = self.reviewed_task(
                    project, words, 'draft-v2', '2026-11-17', 2, passed=False)
                for relative, delivery in ((old, old_delivery), (current, current_delivery)):
                    work = ('交付到 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
                    write_task(project, words, words['facts'][2], work,
                               Path(relative).name, '001 Annual draft ' + Path(delivery).stem)
                page = self.render(project, lang)
                node = self.task_node(page, current, 'active')
                self.assertEqual(node.attrs['data-status'], 'returned')
                self.assertEqual(node.attrs['data-blocked'], 'true')
                done = PageText(page).section('done')
                self.assertFalse(any('data-task' in node.attrs for node in done.nodes()))
                self.assertIn('这周审过 0 单' if lang == 'zh' else
                              '0 passed review this week', done.text)

    def test_omitted_language_detects_project_files_for_render_and_cli(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                page = board.render(project, today=TODAY)
                self.assertIn(words['footer'], PageText(page).text)
                self.assertIn(words['question'], PageText(page).text)
                run = subprocess.run(
                    [sys.executable, '-I', '-B', str(SCRIPT), '--project', str(project),
                     '--today', TODAY.isoformat()], capture_output=True,
                    encoding='utf-8', timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertTrue((project / 'fleet' / words['output']).is_file())

    def test_automatic_language_prefers_chinese_filenames_and_defaults_to_chinese(self):
        for mixed in (False, True):
            with self.subTest(mixed=mixed), temporary_directory() as directory:
                project = Path(directory)
                if mixed:
                    make_project(project, 'en')
                    write(project, 'fleet/成员.md', '# Members\n')
                page = board.render(project, today=TODAY)
                self.assertIn(LANGUAGES['zh']['footer'], PageText(page).text)
                self.assertIn('lang="zh-CN"', page)

    @staticmethod
    def tree_snapshot(project):
        return {str(path.relative_to(project)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in project.rglob('*') if path.is_file()}

    def run_status(self, project=None, lang=None, payload='', cwd=None):
        command = [sys.executable, '-I', '-B', str(SCRIPT), '--status-line']
        if project is not None:
            command.extend(('--project', str(project)))
        if lang is not None:
            command.extend(('--lang', lang))
        run = subprocess.run(command, input=payload, cwd=cwd, capture_output=True,
                             encoding='utf-8', timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, '')
        self.assertEqual(len(run.stdout.splitlines()), 1)
        self.assertNotIn(str(SCRIPT), run.stdout)
        if project is not None:
            self.assertNotIn(str(project), run.stdout)
            self.assertNotIn(project.as_posix(), run.stdout)
        return run.stdout.strip()

    def test_status_line_bilingual_counts_match_dispatched_running_and_waiting(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                before = self.tree_snapshot(project)
                self.assertEqual(self.run_status(project, lang),
                                 '舰队：2 在跑 · 1 等你' if lang == 'zh' else
                                 'Fleet: 2 running · 1 waiting for you')
                self.assertEqual(self.tree_snapshot(project), before)
                active = PageText(self.render(project, lang)).section('active')
                self.assertEqual(sum(node.attrs.get('data-status') in ('dispatched', 'running')
                                     for node in active.nodes()), 2)

    def test_status_line_reports_zero_counts_for_readable_records_without_pending_work(self):
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                write(project, 'AGENTS.md', '# Project card\n\n## {}\n\n'.format(words['needed']))
                for index in range(1, 7):
                    write_task(project, words, words['facts'][-1], words['future'],
                               '{:02d}.md'.format(index))
                self.assertEqual(self.run_status(project, lang),
                                 '舰队：0 在跑 · 0 等你' if lang == 'zh' else
                                 'Fleet: 0 running · 0 waiting for you')

    def test_status_line_missing_records_uses_the_short_message_without_writing(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                self.assertEqual(self.run_status(project, lang),
                                 '舰队：还没有记录' if lang == 'zh' else
                                 'Fleet: no records yet')
                self.assertEqual(self.tree_snapshot(project), {})

    def test_status_line_uses_json_project_dir_before_the_process_directory(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                root = Path(directory)
                project = root / 'project'
                make_project(project, lang)
                payload = json.dumps({'workspace': {'project_dir': str(project),
                                                     'current_dir': str(root / 'nested')},
                                      'cwd': str(root)})
                before = self.tree_snapshot(root)
                self.assertEqual(self.run_status(payload=payload, cwd=root),
                                 '舰队：2 在跑 · 1 等你' if lang == 'zh' else
                                 'Fleet: 2 running · 1 waiting for you')
                self.assertEqual(self.tree_snapshot(root), before)

    def test_status_line_explicit_project_overrides_json_project_and_language(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                root = Path(directory)
                project = root / 'selected'
                make_project(project, lang)
                other = root / 'other'
                write(other, 'fleet/' + LANGUAGES['en' if lang == 'zh' else 'zh']['roster'], '# Roster\n')
                payload = json.dumps({'workspace': {'project_dir': str(other)}})
                self.assertEqual(self.run_status(project, payload=payload, cwd=root),
                                 '舰队：2 在跑 · 1 等你' if lang == 'zh' else
                                 'Fleet: 2 running · 1 waiting for you')

    def test_status_line_empty_invalid_or_unusable_json_falls_back_to_process_directory(self):
        payloads = ['', 'not JSON', '{', 'null', '[]', '3', '"text"',
                    '{"workspace": []}', '{"workspace": {"project_dir": []}}',
                    '{"workspace": {"project_dir": {"value": "."}}}']
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                payloads_with_unused_dirs = payloads + [json.dumps({
                    'workspace': {'current_dir': str(project / 'nested')},
                    'cwd': str(project / 'nested')})]
                for payload in payloads_with_unused_dirs:
                    with self.subTest(payload=payload):
                        self.assertEqual(self.run_status(payload=payload, cwd=project),
                                         '舰队：2 在跑 · 1 等你' if lang == 'zh' else
                                         'Fleet: 2 running · 1 waiting for you')

    def test_status_line_explicit_language_overrides_automatic_detection(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                detected = 'en' if lang == 'zh' else 'zh'
                write(project, 'fleet/' + LANGUAGES[detected]['roster'], '# Roster\n')
                line = self.run_status(project, lang)
                self.assertTrue(line.startswith('舰队：' if lang == 'zh' else 'Fleet: '))
                page = board.render(project, lang=lang, today=TODAY)
                self.assertIn(LANGUAGES[lang]['footer'], PageText(page).text)

    def test_status_line_runtime_exception_is_silent_and_returns_zero(self):
        for lang in LANGUAGES:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                make_project(project, lang)
                stdout, stderr = io.StringIO(), io.StringIO()
                with mock.patch.object(board, 'task_records', side_effect=RuntimeError('test failure')):
                    with mock.patch.object(sys, 'stdin', io.StringIO('{}')), \
                            mock.patch.object(sys, 'stdout', stdout), \
                            mock.patch.object(sys, 'stderr', stderr):
                        result = board.main(['--status-line', '--project', str(project), '--lang', lang])
                self.assertEqual(result, 0)
                self.assertEqual(stderr.getvalue(), '')
                self.assertEqual(stdout.getvalue().strip(),
                                 '舰队：还没有记录' if lang == 'zh' else
                                 'Fleet: no records yet')

    def test_status_line_empty_or_unreadable_brief_is_not_a_record(self):
        for lang, words in LANGUAGES.items():
            for unreadable in (False, True):
                with self.subTest(lang=lang, unreadable=unreadable), temporary_directory() as directory:
                    project = Path(directory)
                    target = project / 'fleet' / words['briefs'] / 'unreadable.md'
                    write(project, str(target.relative_to(project)),
                          '# Task brief\n\nNo readable execution evidence.\n' if unreadable else '')
                    expected = '舰队：还没有记录' if lang == 'zh' else 'Fleet: no records yet'
                    if unreadable:
                        read_local = board.read
                        def unreadable_brief(path, boundary):
                            return '' if path == target else read_local(path, boundary)
                        with mock.patch.object(board, 'read', side_effect=unreadable_brief):
                            self.assertEqual(board.status_line(project, lang), expected)
                    else:
                        self.assertEqual(self.run_status(project, lang), expected)

    def test_same_day_natural_review_version_order_keeps_a_returned_task_active(self):
        with temporary_directory() as directory:
            project = Path(directory)
            words = LANGUAGES['en']
            relative, delivery = self.reviewed_task(
                project, words, 'same-day', TODAY.isoformat(), report_name='review-v2.md')
            write(project, 'fleet/deliveries/review-v10.md',
                  '# Independent review\n\nDate: 2026-11-17\n\nConclusion: Returned.\n\n'
                  '- Checked source materials and delivery: `{}`.\n'.format(delivery))
            page = self.render(project, 'en')
            node = self.task_node(page, relative, 'active')
            self.assertEqual(node.attrs['data-status'], 'returned')
            self.assertEqual(node.attrs['data-blocked'], 'true')
            self.assertIn('Returned', node.text)
            self.assertIn('blocked', node.attrs.get('class', '').split())
            done = PageText(page).section('done')
            self.assertFalse(any('data-task' in node.attrs for node in done.nodes()))
            self.assertIn('0 passed review this week', done.text)

    def test_status_line_invalid_argument_is_quiet_and_respects_equals_language(self):
        with temporary_directory() as directory:
            project = Path(directory)
            before = self.tree_snapshot(project)
            run = subprocess.run(
                [sys.executable, '-I', '-B', str(SCRIPT), '--status-line', '--lang=en', '--bad'],
                input='', cwd=project, capture_output=True, encoding='utf-8', timeout=10)
            self.assertEqual(run.returncode, 0)
            self.assertEqual(run.stderr, '')
            self.assertEqual(run.stdout.splitlines(), ['Fleet: no records yet'])
            self.assertEqual(self.tree_snapshot(project), before)


class BoardWordingTests(unittest.TestCase):
    def test_waiting_age_says_today_and_uses_singular_day(self):
        expected = {'zh': ('今天', '已等 1 天'), 'en': ('Today', 'Waiting 1 day')}
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                card = ('# Project card\n\n## {}\n\n'.format(words['needed']) +
                        '- {} TODAY_ITEM: choose a version.\n'.format(TODAY.isoformat()) +
                        '- {} YESTERDAY_ITEM: choose a version.\n'.format((TODAY - timedelta(days=1)).isoformat()))
                write(project, 'AGENTS.md', card)
                waiting = PageText(board.render(project, lang=lang, today=TODAY)).section('waiting').text
                today_label, one_day = expected[lang]
                self.assertIn(today_label, waiting)
                self.assertIn(one_day, waiting)
                self.assertNotIn('1 days', waiting)
                self.assertNotIn('已等 0 天', waiting)
                self.assertNotIn('Waiting 0 days', waiting)

    def test_done_block_says_nothing_passed_when_the_project_has_tasks(self):
        expected = {'zh': '最近 7 天还没有审核通过的单', 'en': 'Nothing passed review in the last 7 days.'}
        generic = {'zh': '还没有记录，开始用以后会出现在这里', 'en': 'No records yet. They will show up here once you start.'}
        for lang, words in LANGUAGES.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                FleetBoardTests.reviewed_task(self, project, words, 'only', TODAY.isoformat(), passed=False)
                page = PageText(board.render(project, lang=lang, today=TODAY))
                self.assertIn(expected[lang], page.section('done').text)
                self.assertNotIn(generic[lang], page.section('done').text)
                tasks = [n.attrs.get('data-task', '') for n in page.section('active').nodes()]
                self.assertTrue(any(t.endswith('only.md') for t in tasks), tasks)
            with self.subTest(lang=lang, empty=True), temporary_directory() as directory:
                empty = PageText(board.render(Path(directory), lang=lang, today=TODAY)).section('done').text
                self.assertIn(generic[lang], empty)
                self.assertNotIn(expected[lang], empty)

if __name__ == '__main__':
    unittest.main()
