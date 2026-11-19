"""Weekly metrics come from the existing fleet records, never invented counters."""
from datetime import date, timedelta
import html
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import unittest

from temp_support import temporary_directory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/fleet-chart/scripts/fleet_weekly.py'
spec = importlib.util.spec_from_file_location('fleet_weekly', SCRIPT)
weekly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weekly)
TODAY = date(2026, 11, 17)

WORDS = {
    'zh': dict(roster='成员.md', briefs='任务书', deliveries='交付', decisions='决定.md',
               waiting='等我定', current='现状', work='要做的',
               brief='任务书', review='独立审核', dated='日期', round='审核轮次',
               passed='结论：质量通过。', returned='结论：未通过，退回修改。',
               issues='问题', required='必修项', none='没有待定事项。', output='周报卡.html',
               maker='谁定', decision='定了什么', human='人',
               headers='岗位|部门|汇报给|派驻|怎么调用|做什么|交付写进',
               save='存成图片', empty='还没有记录'),
    'en': dict(roster='members.md', briefs='task-briefs', deliveries='deliveries', decisions='decisions.md',
               waiting='Decisions needed', current='Current state', work='Work required',
               brief='Task brief', review='Independent review', dated='Date', round='Review round',
               passed='Conclusion: Quality passed.', returned='Conclusion: Returned for changes.',
               issues='Issues', required='Required fixes', none='Nothing to decide.', output='weekly.html',
               maker='Decision maker', decision='Decision', human='Human',
               headers='Role|Department|Reports to|Assigned|How to call|Does|Delivers to',
               save='Save as image', empty='No records yet'),
}


def write(project, relative, text):
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))


def project_records(project, lang, waiting=None):
    words = WORDS[lang]
    header = '| ' + ' | '.join(words['headers'].split('|')) + ' |\n'
    roster = (header + '|---|---|---|---|---|---|---|\n'
              '| Manager | Project | Human | Model A | Local | Coordinate | fleet/handoff.md |\n'
              '| Writer | Project | Manager | Model B | Local | Draft | fleet/output.md |\n'
              '| Reviewer | Project | Manager | Model A | Local | Review | fleet/review.md |\n')
    write(project, 'fleet/' + words['roster'], roster)
    if waiting is not None:
        # Only these generated project cards are opened by the tests.
        write(project, 'AGENTS.md', '# Test project\n\n## {}\n\n{}\n'.format(
            words['waiting'], waiting))
    return words


def decision_log(project, lang, entries=()):
    """Use the existing heading-and-fields template, with no new status schema."""
    words = WORDS[lang]
    body = '# {}\n\n'.format('决定记录' if lang == 'zh' else 'Decision log')
    for index, (when, maker, decision) in enumerate(entries, 1):
        body += '## {}｜D{:03d}\n\n'.format(when, index)
        if maker is not None:
            body += '- {}: {}\n'.format(words['maker'], maker)
        if decision is not None:
            body += '- {}: {}\n'.format(words['decision'], decision)
        body += '\n'
    write(project, 'fleet/' + words['decisions'], body)


def issue_report(body, lang='en', passed=False):
    words = WORDS[lang]
    return '# {}\n\n{}\n\n{}'.format(words['review'],
        words['passed'] if passed else words['returned'], body)


def reviewed_task(project, lang, key, when, passed=True, round_number=1,
                  report_name=None, issue_body=None, title=None, issue_heading=None):
    words = WORDS[lang]
    delivery = 'fleet/{}/{}.md'.format(words['deliveries'], key)
    brief = 'fleet/{}/{}.md'.format(words['briefs'], key)
    title = title or key
    work = ('交付 `{}`。' if lang == 'zh' else 'Deliver to `{}`.').format(delivery)
    write(project, brief, '# {}: {}\n\n## {}\n\n{}\n\n## {}\n\n{}\n'.format(
        words['brief'], title, words['current'],
        '看到的：交付已收到。' if lang == 'zh' else 'Observed: delivery received.',
        words['work'], work))
    write(project, delivery, '完成\n\nDraft.\n')
    report = 'fleet/{}/{}'.format(words['deliveries'], report_name or key + '-review.md')
    text = '# {}\n\n{}: {}\n\n{}\n\n'.format(
        words['review'], words['dated'], when,
        words['passed'] if passed else words['returned'])
    if round_number is not None:
        text += '{}: {}\n\n'.format(words['round'], round_number)
    text += ('已对照原材料及交付：`{}`。\n' if lang == 'zh' else
             'Checked source materials and delivery: `{}`.\n').format(delivery)
    if issue_body is not None:
        text += '\n## {}\n\n{}\n'.format(issue_heading or words['required'], issue_body)
    write(project, report, text)
    return brief, delivery, report


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.texts = []
        self.stack = []
        self.regions = {}
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        region = attrs.get('id') or ('svg' if tag == 'svg' else None)
        if region:
            self.regions.setdefault(region, [])
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                       'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.stack.append((tag, region))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.texts.append(data)
        for _, region in self.stack:
            if region:
                self.regions[region].append(data)

    def text_in(self, name):
        return ' '.join(' '.join(self.regions.get(name, ())).split())


class WeeklyMetricTests(unittest.TestCase):
    def test_passing_review_requires_a_deliverable_and_no_blocking_note(self):
        for lang in WORDS:
            for has_delivery in (False, True):
                with self.subTest(lang=lang, delivery=has_delivery), temporary_directory() as directory:
                    project = Path(directory)
                    _, delivery, _ = reviewed_task(project, lang, 'draft', TODAY)
                    if has_delivery:
                        status = '卡住：等原稿' if lang == 'zh' else 'Blocked: waiting for the source'
                    else:
                        (project / delivery).unlink()
                        status = '完成' if lang == 'zh' else 'Complete'
                    suffix = '-说明.md' if lang == 'zh' else '-notes.md'
                    write(project, delivery[:-3] + suffix, status)

                    result = weekly.collect(project, lang=lang, today=TODAY)
                    self.assertIsNone(result['completed'])
                    self.assertIsNone(result['first_pass'])

    def test_missing_records_stay_unknown_in_both_languages(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['language'], lang)
                for metric in ('completed', 'first_pass', 'issues', 'questions', 'decided', 'pending', 'models'):
                    self.assertIsNone(result[metric], metric)
                page = weekly.render(project, lang=lang, today=TODAY)
                parsed = Page(page)
                self.assertIn('—', parsed.text_in('share-card'))
                for metric in ('completed', 'first-pass', 'issues', 'questions'):
                    text = parsed.text_in('metric-' + metric)
                    self.assertIn('—', text)
                    self.assertRegex(text, r'—\s+\S+')
                self.assertNotRegex(page, r'>\s*0%\s*<')

    def test_four_metrics_use_bilingual_records_and_distinct_models(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang,
                                '- 2026-11-11 Choose a version.\n- 2026-11-17 Approve the scope.')
                decision_log(project, lang, [('2026-11-15', WORDS[lang]['human'], 'Choose option one.'),
                                              ('2026-11-16', WORDS[lang]['human'], 'Approve the task.')])
                reviewed_task(project, lang, '001-first', '2026-11-11',
                              issue_body='1. Correct one missing source.\n2. Clarify one unit.')
                reviewed_task(project, lang, '002-revised', '2026-11-12', passed=False,
                              report_name='002-first-review.md', issue_body='- Correct a figure.')
                reviewed_task(project, lang, '002-revised', '2026-11-17', round_number=2,
                              report_name='002-second-review.md', issue_body='None.' if lang == 'en' else '无。')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 2)
                self.assertEqual(result['first_pass'], 50)
                self.assertEqual(result['issues'], 1)
                self.assertEqual(result['decided'], 2)
                self.assertEqual(result['pending'], 2)
                self.assertEqual(result['questions'], 4)
                self.assertEqual(result['models'], 2)

    def test_weekly_passed_review_requires_the_delivery_file(self):
        for lang, words in WORDS.items():
            delivery = f"fleet/{words['deliveries']}/01.md"
            notes = delivery[:-3] + ('-说明.md' if lang == 'zh' else '-notes.md')
            review = f"fleet/{words['deliveries']}/01-review.md"
            brief = f"fleet/{words['briefs']}/01.md"
            outputs = f'交付 `{delivery}`，保存说明到 `{notes}`。' if lang == 'zh' else (
                f'Deliver to `{delivery}` and save the notes to `{notes}`.')
            for has_delivery, has_notes in ((False, True), (True, True), (True, False)):
                with self.subTest(lang=lang, delivery=has_delivery, notes=has_notes), temporary_directory() as directory:
                    project = Path(directory)
                    write(project, brief, f"# 01\n\n## {words['work']}\n\n{outputs}\n")
                    if has_delivery:
                        write(project, delivery, 'Final draft.\n')
                    if has_notes:
                        write(project, notes, '完成\n' if lang == 'zh' else 'Complete\n')
                    write(project, review,
                          f"# {words['review']}\n\n{words['dated']}: {TODAY}\n\n{words['passed']}\n\n"
                          f"{words['round']}: 1\n\n`{delivery}` · `{notes}`\n")
                    result = weekly.collect(project, lang=lang, today=TODAY)
                    self.assertEqual(result['completed'], 1 if has_delivery else None)
                    self.assertEqual(result['first_pass'], 100 if has_delivery else None)

    def test_zero_denominator_does_not_produce_a_percentage(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, WORDS[lang]['none'])
                reviewed_task(project, lang, 'only-returned', '2026-11-17', passed=False,
                              issue_body='- Correct the source.')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertIsNone(result['completed'])
                self.assertIsNone(result['first_pass'])
                self.assertEqual(result['issues'], 1)
                self.assertEqual(result['questions'], 0)
                self.assertEqual(result['decided'], 0)
                self.assertEqual(result['pending'], 0)
                page = weekly.render(project, lang=lang, today=TODAY)
                self.assertNotRegex(page, r'>\s*(?:0|NaN|Infinity)%\s*<')

    def test_seven_day_window_includes_both_ends_and_excludes_future(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                dates = ('2026-11-10', '2026-11-11', '2026-11-17', '2026-11-18')
                project_records(project, lang, '\n'.join('- {} Question.'.format(d) for d in dates))
                decision_log(project, lang, [(dated, WORDS[lang]['human'], 'Choose a version.') for dated in dates])
                for index, dated in enumerate(dates):
                    reviewed_task(project, lang, 'task-{}'.format(index), dated)
                    reviewed_task(project, lang, 'returned-{}'.format(index), dated,
                                  passed=False, issue_body='- One required fix.')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 2)
                self.assertEqual(result['first_pass'], 100)
                self.assertEqual(result['issues'], 2)
                self.assertEqual(result['pending'], 2)
                self.assertEqual(result['decided'], 2)
                self.assertEqual(result['questions'], 4)
                page = weekly.render(project, lang=lang, today=TODAY)
                self.assertIn('2026-11-11', page)
                self.assertIn('2026-11-17', page)

    def test_unknown_first_review_does_not_guess_a_rate(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                reviewed_task(project, lang, 'known-first', '2026-11-15')
                reviewed_task(project, lang, 'round-not-recorded', '2026-11-16', round_number=None)
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 2)
                self.assertIsNone(result['first_pass'])

    def test_first_review_before_window_still_determines_first_pass_rate(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                reviewed_task(project, lang, 'revised', '2026-11-10', passed=False,
                              report_name='first-review.md', issue_body='- Old issue.')
                reviewed_task(project, lang, 'revised', '2026-11-17', round_number=2,
                              report_name='second-review.md',
                              issue_body='None.' if lang == 'en' else '无。')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 1)
                self.assertEqual(result['first_pass'], 0)
                self.assertEqual(result['issues'], 0)

    def test_returned_then_passed_without_a_first_review_declaration_stays_unknown(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                reviewed_task(project, lang, 'draft-v1', '2026-11-15', passed=False,
                              round_number=None, title='001 Draft v1', issue_body='- Correct the source.')
                reviewed_task(project, lang, 'draft-v2', '2026-11-17', round_number=None,
                              title='001 Draft v2')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 1)
                self.assertIsNone(result['first_pass'])

    def test_readme_first_review_link_establishes_failed_first_pass(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                _, _, first = reviewed_task(project, lang, 'draft-v1', '2026-11-15', passed=False,
                    round_number=None, title='001 Draft v1', issue_body='- Correct the source.')
                reviewed_task(project, lang, 'draft-v2', '2026-11-17', round_number=None,
                              title='001 Draft v2')
                label = '第一轮审核' if lang == 'zh' else 'first review'
                readme = 'README.zh-CN.md' if lang == 'zh' else 'README.md'
                write(project, readme, '# Example\n\n[{}]({})\n'.format(label, first))
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 1)
                self.assertEqual(result['first_pass'], 0)

    def test_conflicting_first_review_links_keep_the_rate_unknown(self):
        with temporary_directory() as directory:
            project = Path(directory)
            project_records(project, 'en')
            _, _, first = reviewed_task(project, 'en', 'draft-v1', '2026-11-15', passed=False,
                round_number=None, title='001 Draft v1', issue_body='- Correct the source.')
            _, _, second = reviewed_task(project, 'en', 'draft-v2', '2026-11-17', round_number=None,
                                        title='001 Draft v2')
            write(project, 'README.md', '# Example\n\n[first review]({})\n'.format(first))
            write(project, 'README.zh-CN.md', '# 示例\n\n[第一轮审核]({})\n'.format(second))
            self.assertIsNone(weekly.collect(project, lang='en', today=TODAY)['first_pass'])

    def test_code_images_and_escaped_readme_links_are_not_first_review_evidence(self):
        for lang in WORDS:
            label = '第一轮审核' if lang == 'zh' else 'first review'
            for form in ('inline-code', 'image', 'escaped'):
                with self.subTest(lang=lang, form=form), temporary_directory() as directory:
                    project = Path(directory)
                    project_records(project, lang)
                    _, _, first = reviewed_task(project, lang, 'draft-v1', '2026-11-15', passed=False,
                        round_number=None, title='001 Draft v1', issue_body='- Correct the source.')
                    reviewed_task(project, lang, 'draft-v2', '2026-11-17', round_number=None,
                                  title='001 Draft v2')
                    link = '[{}]({})'.format(label, first)
                    fake = '`' + link + '`' if form == 'inline-code' else ('!' if form == 'image' else '\\') + link
                    readme = 'README.zh-CN.md' if lang == 'zh' else 'README.md'
                    write(project, readme, '# Example\n\n{}\n'.format(fake))
                    self.assertIsNone(weekly.collect(project, lang=lang, today=TODAY)['first_pass'])

    def test_explicit_no_required_fixes_differs_from_missing_problem_records(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                _, _, report = reviewed_task(project, lang, 'task', '2026-11-17', passed=False, issue_body=None)
                self.assertIsNone(weekly.collect(project, lang=lang, today=TODAY)['issues'])
                path = project / report
                original = path.read_text(encoding='utf-8')
                suffix = '\n## {}\n\n{}\n'.format(WORDS[lang]['required'],
                    '无。' if lang == 'zh' else 'None.')
                write(project, report, original + suffix)
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['issues'], 0)

    def test_nested_lists_and_unrelated_sections_are_not_extra_issues(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                body = ('1. Incorrect unit.\n   - Evidence for the same issue.\n'
                        '   - One proposed correction.\n2. Missing source.\n\n'
                        '## 修订记录\n\n- Fixed a unit.\n- Added a source.\n\n'
                        '## Materials checked\n\n- Source one.\n- Source two.')
                reviewed_task(project, lang, 'task', '2026-11-17', passed=False, issue_body=body)
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['issues'], 2)

    def test_only_required_fixes_in_returned_reviews_count_as_caught_issues(self):
        cases = (
            ('## Required fixes\n\nNone.\n\n## Issues\n\n- Optional wording.\n', 0),
            ('## Required fixes\n\n- Correct the draft.\n\n## Issues\n\n'
             '- Wording could be clearer.\n- A suggestion.\n', 1),
            ('## 必修项\n\n无。\n\n## 问题\n\n- 可选措辞建议。\n', 0),
            ('## 必修项\n\n- 修改交付。\n\n## 问题\n\n- 一处可选建议。\n- 另一处建议。\n', 1),
        )
        for report, expected in cases:
            with self.subTest(report=report):
                lang = 'zh' if '必修项' in report else 'en'
                self.assertEqual(weekly.issue_count(issue_report(report, lang)), expected)

    def test_fenced_zero_issue_examples_do_not_establish_a_number(self):
        report = issue_report('```text\n## Required fixes\n\nNone.\n```\n')
        self.assertIsNone(weekly.issue_count(report))

    def test_passed_reviews_do_not_count_advisory_or_remaining_issue_lists(self):
        for body in ('## Issues\n\n- A factual error remains.\n',
                     '## Required fixes\n\n- Correct the source.\n'):
            with self.subTest(body=body):
                self.assertEqual(weekly.issue_count(issue_report(body, passed=True)), 0)

    def test_zero_issue_bullets_and_checked_boxes_are_not_counted_as_errors(self):
        cases = (('en', '## Required fixes\n\n- [x] No required fixes.\n'),
                 ('zh', '## 必修项\n\n- 无必修项。\n'))
        for lang, report in cases:
            with self.subTest(report=report):
                self.assertEqual(weekly.issue_count(issue_report(report, lang)), 0)

    def test_review_result_table_counts_only_explicitly_failed_rows(self):
        cases = (
            ('en', '| Item | Result | Evidence |\n|---|---|---|\n'
             '| Source | Failed | Incorrect quotation. |\n'
             '| Length | Needs work | Optional shortening. |\n'
             '| Format | Passed | Correct. |\n'),
            ('zh', '| 项目 | 结果 | 证据 |\n|---|---|---|\n'
             '| 出处 | 不通过 | 引文错误。 |\n'
             '| 篇幅 | 需修 | 可选压缩。 |\n'
             '| 格式 | 通过 | 正确。 |\n'),
        )
        for lang, table in cases:
            with self.subTest(lang=lang):
                # A generic corrective action can cover several failed checks.
                body = table + '\n## {}\n\n- Correct the draft.\n- Recheck it.\n'.format(WORDS[lang]['required'])
                self.assertEqual(weekly.issue_count(issue_report(body, lang)), 1)

    def test_unknown_review_table_columns_do_not_turn_failed_text_into_a_result(self):
        body = '| Field | Observation |\n|---|---|\n| Source | Failed |\n'
        self.assertIsNone(weekly.issue_count(issue_report(body)))

    def test_generic_findings_require_explicit_mandatory_markers(self):
        for lang, unmarked, marked in (
                ('en', '- The source is unclear.\n', '- Must correct the source.\n- Required: fix the unit.\n'),
                ('zh', '- 出处不够清楚。\n', '- 必改：修正出处。\n- 必须修正单位。\n')):
            with self.subTest(lang=lang):
                heading = '## {}\n\n'.format(WORDS[lang]['issues'])
                self.assertIsNone(weekly.issue_count(issue_report(heading + unmarked, lang)))
                self.assertEqual(weekly.issue_count(issue_report(heading + marked, lang)), 2)

    def test_optional_suggestions_in_required_fix_sections_do_not_count(self):
        for lang, body in (
                ('en', '- Correct the source.\n- Optional: shorten the introduction.\n'),
                ('zh', '- 修正出处。\n- 建议：缩短引言。\n')):
            with self.subTest(lang=lang):
                report = issue_report('## {}\n\n{}'.format(WORDS[lang]['required'], body), lang)
                self.assertEqual(weekly.issue_count(report), 1)

    def test_explicitly_nonmandatory_items_in_required_fix_sections_do_not_count(self):
        cases = (('zh', '- 不必改：保持现有标题。\n- 无需修改：当前段落正确。\n'),
                 ('en', '- Not required: change the title.\n- Optional: shorten the introduction.\n'))
        for lang, body in cases:
            with self.subTest(lang=lang):
                report = issue_report('## {}\n\n{}'.format(WORDS[lang]['required'], body), lang)
                self.assertEqual(weekly.issue_count(report), 0)

    def test_mandatory_items_can_quote_suggestions_without_becoming_optional(self):
        cases = (('zh', '- 必须修正出处；引述“作者的建议”只是本问题的证据。\n'),
                 ('en', '- Must correct the source; the quote "the writer suggested it" is evidence.\n'))
        for lang, body in cases:
            with self.subTest(lang=lang):
                report = issue_report('## {}\n\n{}'.format(WORDS[lang]['issues'], body), lang)
                self.assertEqual(weekly.issue_count(report), 1)

    def test_required_items_without_a_real_review_conclusion_stay_unknown(self):
        self.assertIsNone(weekly.issue_count('# Review template\n\n## Required fixes\n\n- Correct the source.\n'))

    def test_one_delivery_and_review_referenced_by_multiple_briefs_count_once(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                brief, delivery, _ = reviewed_task(project, lang, 'task', '2026-11-17',
                                                  issue_body='- One issue.')
                copy = 'fleet/{}/second-brief.md'.format(WORDS[lang]['briefs'])
                write(project, copy, (project / brief).read_text(encoding='utf-8'))
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['issues'], 0)
                self.assertEqual(result['completed'], 1)
                self.assertEqual(result['first_pass'], 100)
                # A repeated first-pass task must not overweight the numerator.
                reviewed_task(project, lang, 'other-task', '2026-11-15', passed=False,
                              report_name='other-first-review.md',
                              issue_body='None.' if lang == 'en' else '无。')
                reviewed_task(project, lang, 'other-task', '2026-11-17', round_number=2,
                              report_name='other-second-review.md',
                              issue_body='None.' if lang == 'en' else '无。')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['completed'], 2)
                self.assertEqual(result['first_pass'], 50)

    def test_missing_findings_in_any_in_window_report_keeps_total_unknown(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                reviewed_task(project, lang, 'recorded', '2026-11-17', passed=False, issue_body='- One required fix.')
                reviewed_task(project, lang, 'missing', '2026-11-17', passed=False, issue_body=None)
                self.assertIsNone(weekly.collect(project, lang=lang, today=TODAY)['issues'])

    def test_latest_review_can_return_an_earlier_passed_task(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                reviewed_task(project, lang, 'task', '2026-11-12',
                              report_name='task-first-review.md',
                              issue_body='None.' if lang == 'en' else '无。')
                reviewed_task(project, lang, 'task', '2026-11-17', passed=False, round_number=2,
                              report_name='task-second-review.md', issue_body='- New issue.')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertIsNone(result['completed'])
                self.assertIsNone(result['first_pass'])
                self.assertEqual(result['issues'], 1)

    def test_undated_waiting_entries_stay_unknown_and_do_not_enter_the_window(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = project_records(project, lang, '- Choose a version; mentioned 2026-11-15 later.')
                self.assertIsNone(weekly.collect(project, lang=lang, today=TODAY)['questions'])
                write(project, 'AGENTS.md', '# Test\n\n## {}\n\n'
                      '- 2026-11-17 Choose a version.\n- Undated question.\n'.format(words['waiting']))
                self.assertIsNone(weekly.collect(project, lang=lang, today=TODAY)['questions'])

    def test_dated_no_action_notes_are_not_questions_and_old_questions_are_zero(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                no_action = '当前没有待定事项。' if lang == 'zh' else 'Nothing pending.'
                words = project_records(project, lang,
                                        '- 2026-11-17 {}\n- 2026-11-17 Choose a version.'.format(no_action))
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['questions'], 1)
                write(project, 'AGENTS.md', '# Test\n\n## {}\n\n'
                      '- 2026-11-10 Old question.\n- 2026-11-18 Future question.\n'.format(words['waiting']))
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['questions'], 0)

    def test_explicitly_empty_waiting_is_zero_but_absent_section_is_unknown(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = project_records(project, lang, WORDS[lang]['none'])
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['questions'], 0)
                write(project, 'AGENTS.md', '# Test\n\n## Other section\n\nNo record here.\n')
                self.assertIsNone(weekly.collect(project, lang=lang, today=TODAY)['questions'])
                write(project, 'AGENTS.md', '# Test\n\n## {}\n\n'.format(words['waiting']))
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['questions'], 0)

    def test_only_a_decision_log_records_answered_questions_and_no_pending_items(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                decision_log(project, lang, [('2026-11-15', WORDS[lang]['human'], 'Choose option one.'),
                                              ('2026-11-17', WORDS[lang]['human'], 'Approve the task.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['decided'], 2)
                self.assertEqual(result['pending'], 0)
                self.assertEqual(result['questions'], 2)

    def test_only_a_waiting_section_records_pending_questions_and_no_decisions(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '- 2026-11-15 Choose a version.\n- 2026-11-17 Approve the scope.')
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['decided'], 0)
                self.assertEqual(result['pending'], 2)
                self.assertEqual(result['questions'], 2)

    def test_a_roster_alone_does_not_establish_question_history(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                result = weekly.collect(project, lang=lang, today=TODAY)
                for field in ('decided', 'pending', 'questions'):
                    self.assertIsNone(result[field], field)

    def test_readable_empty_decision_log_and_waiting_section_are_known_zero(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = project_records(project, lang, '')
                decision_log(project, lang)
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual((result['decided'], result['pending'], result['questions']), (0, 0, 0))
                # The existing setup template's placeholder is not a real entry.
                write(project, 'fleet/' + words['decisions'],
                      '# Decision log\n\n## 〔待定：Date and entry identifier〕\n\n'
                      '- {}: 〔待定：Owner〕\n- {}: 〔待定：Decision〕\n'.format(words['maker'], words['decision']))
                self.assertEqual(weekly.collect(project, lang=lang, today=TODAY)['decided'], 0)

    def test_human_and_model_decisions_are_separated_and_mixed_ownership_counts_once(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                makers = ('人。', '用户', 'Human', 'User', 'Manager',
                          '人（接入安排）；Manager（据此落实）。')
                decision_log(project, lang, [('2026-11-17', maker, 'A recorded decision.') for maker in makers])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['decided'], 5)
                self.assertEqual(result['questions'], 5)

    def test_only_explicit_human_assignment_makes_a_named_role_a_human_decider(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                words = project_records(project, lang)
                roster_path = 'fleet/' + words['roster']
                roster = (project / roster_path).read_text(encoding='utf-8')
                roster += '| Owner | Project | Human | Human | In person | Decide | fleet/decision.md |\n'
                write(project, roster_path, roster)
                decision_log(project, lang, [('2026-11-17', 'Owner', 'Approve the task.'),
                                              ('2026-11-17', 'Manager', 'Assign the writer.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['decided'], 1)

    def test_invalid_dates_and_missing_decision_maker_keep_the_total_unknown(self):
        cases = (('2026-11-99', 'Human', 'Approve the task.'),
                 ('2026-11-17', None, 'Approve the task.'))
        for lang in WORDS:
            for entry in cases:
                with self.subTest(lang=lang, entry=entry), temporary_directory() as directory:
                    project = Path(directory)
                    project_records(project, lang, '- 2026-11-17 Choose a version.')
                    decision_log(project, lang, [entry])
                    result = weekly.collect(project, lang=lang, today=TODAY)
                    self.assertIsNone(result['decided'])
                    self.assertEqual(result['pending'], 1)
                    self.assertIsNone(result['questions'])

    def test_unknown_decision_maker_identities_do_not_become_zero_human_decisions(self):
        for lang in WORDS:
            for maker in ('Unknown', 'TBD', '待确认'):
                with self.subTest(lang=lang, maker=maker), temporary_directory() as directory:
                    project = Path(directory)
                    project_records(project, lang, '')
                    decision_log(project, lang, [('2026-11-17', maker, 'Approve the task.')])
                    result = weekly.collect(project, lang=lang, today=TODAY)
                    self.assertIsNone(result['decided'])
                    self.assertEqual(result['pending'], 0)
                    self.assertIsNone(result['questions'])

    def test_empty_decision_maker_cannot_consume_the_next_field_as_its_value(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '')
                separator = '：' if lang == 'zh' else ':'
                write(project, 'fleet/' + words['decisions'],
                      '# Decision log\n\n## 2026-11-17 D001\n\n'
                      '- {}{}\n- {}{} Approve the task.\n'.format(
                          words['maker'], separator, words['decision'], separator))
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertIsNone(result['decided'])
                self.assertIsNone(result['questions'])
                question = Page(weekly.render(project, lang=lang, today=TODAY)).text_in('metric-questions')
                self.assertIn('—', question)
                self.assertIn('谁定' if lang == 'zh' else 'decision maker', question)

    def test_invalid_waiting_dates_do_not_turn_into_zero_questions(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '- 2026-11-99 Choose a version.')
                decision_log(project, lang, [('2026-11-17', WORDS[lang]['human'], 'Approve the task.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual(result['decided'], 1)
                self.assertIsNone(result['pending'])
                self.assertIsNone(result['questions'])

    def test_decision_dates_outside_the_window_establish_zero_in_window(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                decision_log(project, lang, [('2026-11-10', WORDS[lang]['human'], 'Old decision.'),
                                              ('2026-11-18', WORDS[lang]['human'], 'Future decision.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertEqual((result['decided'], result['pending'], result['questions']), (0, 0, 0))

    def test_language_is_detected_and_can_be_overridden(self):
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                self.assertEqual(weekly.collect(project, today=TODAY)['language'], lang)
                override = 'en' if lang == 'zh' else 'zh'
                self.assertEqual(weekly.collect(project, lang=override, today=TODAY)['language'], override)


class WeeklyPageTests(unittest.TestCase):
    def assert_question_display(self, project, lang, value, excluded=0):
        source = weekly.render(project, lang=lang, today=TODAY)
        metric = re.search(r'<g id="metric-questions">(.*?)</g>', source, re.S).group(1)
        self.assertRegex(metric, r'font-size="58"[^>]*>' + re.escape(value) + r'</text>')
        parsed = Page(source)
        if excluded:
            # The card line is plain words; the HTML notes keep the exact counting terms.
            words = {'metric-questions': {'zh': ('没算进来', '至少'), 'en': ('left out', 'at least')},
                     'calculation-notes': {'zh': ('未计入', '下限'), 'en': ('excluded', 'lower bound')}}
            for part, by_lang in words.items():
                text = parsed.text_in(part).casefold()
                omitted, bound = by_lang[lang]
                self.assertIn(str(excluded), text)
                self.assertRegex(text, '缺' if lang == 'zh' else r'lack|missing|unclear|no date')
                self.assertIn(omitted, text)
                if value.startswith('≥'):
                    self.assertIn(bound, text)
        return parsed

    def test_no_recognized_question_source_shows_no_lower_bound(self):
        # The board reads a waiting section at any heading level, but the count only recognizes a
        # level-2 heading or a decision log. Without either, keep "—" and "No records yet".
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                write(project, 'AGENTS.md', '# Test project\n\n### {}\n\n- 2026-11-16 A dated question.\n'.format(words['waiting']))
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertFalse(result['questions_available'])
                self.assertIsNone(result['questions'])
                self.assertEqual(result['questions_at_least'], 0)
                source = weekly.render(project, lang=lang, today=TODAY)
                metric = re.search(r'<g id="metric-questions">(.*?)</g>', source, re.S).group(1)
                self.assertRegex(metric, r'font-size="58"[^>]*>—</text>')
                self.assertIn('还没有记录' if lang == 'zh' else 'No records yet', Page(source).text_in('metric-questions'))

    def test_undated_pending_questions_show_only_the_confirmed_lower_bound(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang,
                                '- Undated question.\n- 2026-11-99 Invalid date.\n'
                                '- 2026-11-11 Start of window.\n- 2026-11-17 End of window.\n'
                                '- 2026-11-10 Old question.\n- 2026-11-18 Future question.')
                decision_log(project, lang, [('2026-11-17', words['human'], 'Approve the task.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertIsNone(result['questions'])
                self.assertIsNone(result['pending'])
                self.assertEqual(result['decided'], 1)
                self.assertEqual(result['questions_at_least'], 3)
                self.assertEqual(result['questions_excluded'], 2)
                parsed = self.assert_question_display(project, lang, '≥3', excluded=2)
                self.assertIn('日期' if lang == 'zh' else 'date', parsed.text_in('metric-questions'))

    def test_missing_decision_maker_keeps_the_complete_decision_as_a_lower_bound(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '')
                decision_log(project, lang, [('2026-11-17', None, 'Missing maker.'),
                                              ('2026-11-17', words['human'], 'Complete decision.'),
                                              ('2026-11-17', 'Manager', 'AI decision.'),
                                              ('2026-11-10', None, 'Old decision.'),
                                              ('2026-11-18', None, 'Future decision.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertIsNone(result['questions'])
                self.assertIsNone(result['decided'])
                self.assertEqual(result['questions_at_least'], 1)
                self.assertEqual(result['questions_excluded'], 1)
                parsed = self.assert_question_display(project, lang, '≥1', excluded=1)
                self.assertIn('谁定' if lang == 'zh' else 'decision maker', parsed.text_in('metric-questions'))

    def test_incomplete_decisions_are_excluded_once_and_never_inflate_the_lower_bound(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '- 2026-11-17 A dated pending question.')
                decision_log(project, lang, [('', words['human'], 'Missing date.'),
                                              ('2026-11-99', words['human'], 'Invalid date.'),
                                              ('', None, 'Missing both date and maker.'),
                                              ('2026-11-17', words['human'], 'Complete decision.')])
                result = weekly.collect(project, lang=lang, today=TODAY)
                self.assertIsNone(result['questions'])
                self.assertEqual(result['questions_at_least'], 2)
                self.assertEqual(result['questions_excluded'], 3)
                self.assert_question_display(project, lang, '≥2', excluded=3)

    def test_only_incomplete_questions_keep_a_dash_in_both_languages(self):
        for lang, words in WORDS.items():
            cases = (('- Undated question.', (), 1),
                     ('- 2026-11-99 Invalid date.', (), 1),
                     ('', [('', words['human'], 'Missing date.')], 1),
                     ('', [('2026-11-17', None, 'Missing maker.')], 1),
                     ('- Undated question.', [('', None, 'Missing both fields.')], 2))
            for waiting, entries, excluded in cases:
                with self.subTest(lang=lang, waiting=waiting, entries=entries), temporary_directory() as directory:
                    project = Path(directory)
                    project_records(project, lang, waiting)
                    decision_log(project, lang, entries)
                    result = weekly.collect(project, lang=lang, today=TODAY)
                    self.assertIsNone(result['questions'])
                    self.assertEqual(result['questions_at_least'], 0)
                    self.assertEqual(result['questions_excluded'], excluded)
                    parsed = self.assert_question_display(project, lang, '—', excluded=excluded)
                    self.assertNotIn('≥0', parsed.text_in('metric-questions'))

    def test_known_question_totals_use_the_exact_number_including_zero(self):
        for lang, words in WORDS.items():
            for count in (0, 1):
                with self.subTest(lang=lang, count=count), temporary_directory() as directory:
                    project = Path(directory)
                    project_records(project, lang, '')
                    decision_log(project, lang, [('2026-11-17', words['human'], 'Complete decision.')] * count)
                    result = weekly.collect(project, lang=lang, today=TODAY)
                    self.assertEqual(result['questions'], count)
                    self.assertEqual(result['questions_at_least'], count)
                    self.assertEqual(result['questions_excluded'], 0)
                    self.assert_question_display(project, lang, str(count))

    def test_card_hides_source_paths_but_explains_calculation_below_it(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '- 2026-11-17 Choose a version.')
                decision_log(project, lang, [('2026-11-17', words['human'], 'Approve the task.')])
                reviewed_task(project, lang, 'task', '2026-11-17')
                page = weekly.render(project, lang=lang, today=TODAY)
                parsed = Page(page)
                card = parsed.text_in('share-card')
                self.assertNotIn('fleet/', card)
                self.assertNotIn('AGENTS.md', card)
                svg = re.search(r'<svg\b.*?</svg>', page, re.S).group(0)
                self.assertNotIn('fleet/', svg)
                self.assertNotIn('AGENTS.md', svg)
                self.assertNotIn(str(project), svg)
                notes = parsed.text_in('calculation-notes')
                self.assertIn('fleet/' + words['briefs'] + '/', notes)
                self.assertIn('fleet/' + words['deliveries'] + '/', notes)
                self.assertIn('fleet/' + words['decisions'], notes)
                self.assertIn('AGENTS.md', notes)
                self.assertIn(words['waiting'], notes)

    def test_question_card_shows_answered_and_pending_counts_and_a_clear_zero(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '- 2026-11-17 Choose a version.')
                decision_log(project, lang, [('2026-11-15', words['human'], 'Approve the task.'),
                                              ('2026-11-17', words['human'], 'Choose option one.')])
                text = Page(weekly.render(project, lang=lang, today=TODAY)).text_in('metric-questions')
                self.assertEqual(re.findall(r'\d+', text), ['3', '2', '1'])
                if lang == 'zh':
                    self.assertIn('问了你', text)
                    self.assertIn('在等你', text)
                else:
                    self.assertIn('asked', text.casefold())
                    self.assertIn('decided', text.casefold())
                    self.assertIn('waiting', text.casefold())
                write(project, 'AGENTS.md', '# Test\n\n## {}\n\n'.format(words['waiting']))
                decision_log(project, lang)
                zero = Page(weekly.render(project, lang=lang, today=TODAY)).text_in('metric-questions')
                if lang == 'zh':
                    self.assertIn('这周没问你', zero)
                else:
                    self.assertRegex(zero.casefold(), r'no questions.*week|not asked.*week')

    def test_page_contains_save_button_and_offline_svg_to_png_script(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang)
                page = weekly.render(project, lang=lang, today=TODAY)
                parsed = Page(page)
                self.assertTrue(any(tag == 'button' for tag, _ in parsed.tags))
                self.assertIn(words['save'], ' '.join(parsed.texts))
                self.assertTrue(any(tag == 'svg' for tag, _ in parsed.tags))
                self.assertTrue(any(tag == 'script' for tag, _ in parsed.tags))
                for token in ('XMLSerializer', 'canvas', 'image/png', 'download'):
                    self.assertIn(token, page)
                self.assertNotIn('foreignObject', page)
                # This namespace identifies SVG syntax; it is never fetched.
                resources = page.replace('http://www.w3.org/2000/svg', '')
                self.assertNotRegex(resources, r'https?://')
                self.assertFalse(any(tag in ('script', 'link') and
                                     ('src' in attrs or 'href' in attrs)
                                     for tag, attrs in parsed.tags))

    def test_user_title_is_escaped_and_cannot_create_markup(self):
        payload = '<img src=x onerror=alert(1)> & "quoted"'
        for lang in WORDS:
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory) / 'Project & Company'
                words = project_records(project, lang, '- 2026-11-17 ' + payload)
                write(project, 'AGENTS.md', '# {}\n\n## {}\n\n- 2026-11-17 Decide.\n'.format(
                    payload, words['waiting']))
                page = weekly.render(project, lang=lang, today=TODAY)
                self.assertNotIn(payload, page)
                self.assertFalse(any(tag == 'img' or 'onerror' in attrs for tag, attrs in Page(page).tags))
                title = weekly.collect(project, lang=lang, today=TODAY)['project']
                self.assertIn(html.escape(title), page)

    def test_cli_writes_beside_board_with_bilingual_filenames(self):
        for lang, words in WORDS.items():
            with self.subTest(lang=lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, lang, '- 2026-11-17 Choose a version.')
                run = subprocess.run(
                    [sys.executable, '-I', '-B', str(SCRIPT), '--project', str(project),
                     '--today', TODAY.isoformat()], capture_output=True, encoding='utf-8', timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)
                output = project / 'fleet' / words['output']
                self.assertTrue(output.is_file())
                self.assertIn(words['save'], output.read_text(encoding='utf-8'))

    def test_cli_language_override_keeps_actual_source_paths_and_waiting_heading(self):
        for source_lang, words in WORDS.items():
            target_lang = 'en' if source_lang == 'zh' else 'zh'
            target_words = WORDS[target_lang]
            with self.subTest(source_lang=source_lang), temporary_directory() as directory:
                project = Path(directory)
                project_records(project, source_lang, '- 2026-11-17 Choose a version.')
                reviewed_task(project, source_lang, 'task', '2026-11-17',
                              issue_body='None.' if source_lang == 'en' else '无。')
                run = subprocess.run(
                    [sys.executable, '-I', '-B', str(SCRIPT), '--project', str(project),
                     '--lang', target_lang, '--today', TODAY.isoformat()],
                    capture_output=True, encoding='utf-8', timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)
                page = (project / 'fleet' / target_words['output']).read_text(encoding='utf-8')
                self.assertIn(target_words['save'], page)
                parsed = Page(page)
                # Calculation notes remain accurate when display language changes.
                text = re.sub(r'\s+', '', parsed.text_in('calculation-notes'))
                self.assertIn('fleet/' + words['briefs'] + '/', text)
                self.assertIn('fleet/' + words['deliveries'] + '/', text)
                self.assertIn(words['waiting'].replace(' ', ''), text)
                self.assertNotIn('fleet/' + target_words['briefs'] + '/', text)
                self.assertNotIn('fleet/' + target_words['deliveries'] + '/', text)
                self.assertNotIn(target_words['waiting'].replace(' ', ''), text)
                self.assertNotIn('fleet/', parsed.text_in('share-card'))


if __name__ == '__main__':
    unittest.main()
