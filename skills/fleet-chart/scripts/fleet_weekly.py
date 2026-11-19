#!/usr/bin/env python3
"""Make a shareable, offline weekly card from the board's existing records."""
import argparse
from datetime import timedelta
from html import escape
import importlib.util
from pathlib import Path
import re
import sys
from urllib.parse import unquote


def sibling(name):
    spec = importlib.util.spec_from_file_location('_weekly_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = bytecode
    return module


board = sibling('fleet_board')
chart = sibling('fleet_chart')
OUTPUTS = {'zh': '周报卡.html', 'en': 'weekly.html'}


def project_name(project, card):
    name = next((line[2:].strip() for line in card.splitlines() if line.startswith('# ')), '')
    name = re.sub(r'^(?:AI\s*舰队项目卡|AI Fleet project card|Project card)\s*[:：—-]?\s*', '', name, flags=re.I)
    return name or project.name


def clean(value, project, language):
    """Hide machine paths as on the board; XML escaping happens at rendering."""
    value = str(value)
    hidden = board.LABELS[language]['relative']
    for path in (str(project.absolute()), str(project.absolute()).replace('\\', '/')):
        value = value.replace(path, hidden)
    value = re.sub(r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\)[^\s`<>\"'|；，。)]+", hidden, value)
    return re.sub(r"(?<![\w:/<])/(?:[^/\s`<>\"'|；，。)]+/)*[^/\s`<>\"'|；，。)]+", hidden, value)


def model_count(rows):
    models = set()
    for row in rows:
        main = re.split(r'[；;]', row['Assigned'], maxsplit=1)[0].strip()
        if not main or re.search(r'〔待定|^(?:待定|待确认|Unknown|TBD|Not assigned)$', main, re.I):
            return None
        alias = re.match(r'^(?:模型|Model)\s+([A-Za-z0-9]+)\s*[:：]', main, re.I)
        models.add(('alias:' + alias[1] if alias else main).casefold())
    return len(models) if models else None


def observed_text(text):
    """Exclude quoted records and fenced examples from factual fields."""
    lines, fenced = [], False
    for line in text.splitlines():
        if re.match(r'^\s*(```|~~~)', line):
            fenced = not fenced
            lines.append('')
        else:
            lines.append('' if fenced or line.lstrip().startswith('>') else line)
    return re.sub(r'<!--[\s\S]*?-->', '', '\n'.join(lines))


def issue_count(text):
    """Required changes in a rejected review; suggestions never count."""
    text = observed_text(text)
    conclusion = board.review_result(text)
    if not conclusion:
        return None
    if board.outcome(conclusion) != 'returned':
        return 0
    # Use the roster parser's escaped-pipe handling for Markdown review tables.
    # Only an explicit result column establishes which rows actually failed.
    result_names = {'结果', '审核结果', 'Result', 'Review result', 'Status'}
    table_counts = []
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if not line.strip().startswith('|'):
            continue
        header = chart.cells(line)
        columns = [i for i, value in enumerate(header) if value.casefold() in {h.casefold() for h in result_names}]
        separator = chart.cells(lines[index + 1])
        if len(columns) != 1 or len(separator) != len(header) or not all(re.fullmatch(r':?-{3,}:?', c) for c in separator):
            continue
        count, rows = 0, 0
        for row_line in lines[index + 2:]:
            if not row_line.strip().startswith('|'):
                break
            row = chart.cells(row_line)
            if len(row) != len(header):
                return None
            result = row[columns[0]].strip('* ')
            rows += 1
            if re.match(r'^(?:不通过|未通过|必改|必须修改|Failed?\b|Rejected?\b|Changes required\b|Required changes\b)', result, re.I):
                count += 1
        if rows:
            table_counts.append(count)
    if table_counts:
        return sum(table_counts)

    headings = re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M)
    findings, fixes = [], []
    for heading in headings:
        if re.match(r'^(?:问题(?:清单|列表|与建议)?|错误(?:清单|列表)?|发现的问题|审核问题|待修问题|'
                    r'Issues?|Problems?|Findings?|Errors?|Review findings)(?:\s*[:：].*|\s*\([^)]*\))?$', heading, re.I):
            findings.append(board.section(text, (heading,)))
        elif re.match(r'^(?:必修项(?:与复审条件)?|Required fixes|Required changes)$', heading, re.I):
            fixes.append(board.section(text, (heading,)))
    def count_list(body, required):
        if re.fullmatch(r'(?:无(?:必修项|必改问题)?|没有|暂无|None|No required fixes|No issues|No findings)[.。 ]*', body.strip(), re.I):
            return 0
        items = []
        for line in body.splitlines():
            match = re.match(r'^(\s*)(?:[-*+]\s+|\d+[.)]\s+)(.+)', line)
            if match:
                item = re.sub(r'^\[[ xX]\]\s*', '', match[2].strip())
                items.append((len(match[1].expandtabs(4)), item))
        if items:
            indent = min(item[0] for item in items)
            roots = [item[1] for item in items if item[0] == indent]
            count = 0
            for item in roots:
                if re.match(r'^(?:无(?:必修项|待修问题|问题|错误)?|None|No (?:required fixes|issues|findings))[.。 ]*$', item, re.I):
                    continue
                if re.search(r'不必改|非必改|无需(?:修改|更改)|不需(?:修改|更改)|\bnot required\b|\bno (?:change|fix) (?:is )?required\b', item, re.I):
                    continue
                if re.search(r'建议|可选|非阻断|\b(?:optional|suggestion|recommended?|non[- ]blocking|nice to have)\b', item, re.I) and not re.search(r'必须|必改|\bmust\b|\brequired\b', item, re.I):
                    continue
                if not required and not re.search(r'必须|必改|必修|\bmust\b|\brequired\b', item, re.I):
                    return None
                count += 1
            return count
        return None

    # Required-fixes lists define the blocking scope. A generic findings list
    # needs explicit mandatory wording on each included item.
    bodies = fixes or findings
    if bodies:
        counts = [count_list(body, bool(fixes)) for body in bodies]
        if len(counts) == 1:
            return counts[0]
        positive = [number for number in counts if number]
        if len(positive) == 1 and all(number is not None for number in counts):
            return positive[0]
        return 0 if all(number == 0 for number in counts) else None
    return None


def human_maker(value, roster):
    if not value or '〔待定' in value:
        return None
    humans = {'人', 'human', '用户', 'user', '使用者', '人类'}
    humans.update(row['Role'].casefold() for row in roster if row['Assigned'].strip().casefold() in humans)
    # Parenthesized scopes, as in Human (access); Manager (implementation),
    # do not change who made that decision. One mixed entry still counts once.
    value = re.sub(r'\([^)]*\)|（[^）]*）', '', value)
    names = re.split(r'[；;、,/&+]|\band\b|和|与', value, flags=re.I)
    if any(name.strip(' \t.*。:：').casefold() in humans for name in names):
        return True
    if re.search(r'待定|待确认|未知|\b(?:unknown|tbd|not recorded|unspecified)\b', value, re.I):
        return None
    return False


def decision_records(text, roster):
    result = []
    parts = re.split(r'(?m)^##\s+(.+?)\s*$', observed_text(text))
    for index in range(1, len(parts), 2):
        heading, body = parts[index:index + 2]
        maker = re.search(r'(?im)^[ \t]*[-*]?[ \t]*(?:谁定|Decision maker)[ \t]*[:：][ \t]*([^\r\n]*)$', body)
        if '〔待定' in heading and not re.search(r'\d{4}-\d{2}-\d{2}', heading):
            continue
        # A numbered/date-bearing entry with a missing maker is incomplete,
        # rather than an empty log or an AI decision.
        if not maker and not re.search(r'\d{4}-\d{2}-\d{2}|\bD\d+\b', heading, re.I):
            continue
        result.append(dict(date=board.written_date('## ' + heading), human=human_maker(maker[1], roster) if maker else None))
    return result


def first_review_hints(project, report_files):
    """Accept explicit first-review links, never infer a round from v1 names."""
    hints, sources = set(), []
    known = {'fleet/' + name: name for name in report_files}
    for name in ('README.md', 'README.zh-CN.md'):
        text = observed_text(board.read(project / name, project))
        text = re.sub(r'(`+).*?\1', '', text)
        found = set()
        for label, target in re.findall(r'(?<![!\\])\[([^\]\n]+)\]\(([^\s)]+)\)', text):
            if not re.fullmatch(r'第一轮审核|首次审核|第一次审核|first review|initial review', label.strip(), re.I):
                continue
            target = unquote(target).split('#', 1)[0]
            if target.startswith('./'):
                target = target[2:]
            if target in known:
                found.add(known[target])
        if found:
            sources.append(name)
            hints.update(found)
    return hints, sources


def collect(project, lang=None, today=None):
    project = Path(project)
    language = board.project_language(project, lang)
    end = board.as_today(today)
    start = end - timedelta(days=6)
    fleet = project / 'fleet'
    tasks = board.task_records(project, language)
    _, done, _ = board.task_overview(tasks, end)
    # Copied, unnumbered briefs may point at the very same reviewed delivery.
    # Preserve the board's per-task/version rules, then deduplicate that evidence.
    unique_done = {}
    for task, report in done:
        unique_done.setdefault((report['file'], report['delivery']), []).append((task, report))
    all_reports = {report['file']: report for task in tasks for report in task['reports']}
    hints, hint_sources = first_review_hints(project, all_reports)
    firsts = []
    for duplicates in unique_done.values():
        rates = set()
        for task, _ in duplicates:
            reports_for_task = {report['file']: report for member in tasks if member['group'] == task['group']
                                for report in member['reports'] if report['date'] and report['date'] <= end}
            declared = [report for report in reports_for_task.values() if report['first'] or report['file'] in hints]
            if len(declared) == 1 and not any(report['date'] < declared[0]['date'] for report in reports_for_task.values()):
                rates.add(100 if declared[0]['outcome'] == 'passed' else 0)
            else:
                rates.add(None)
        firsts.append(rates.pop() if len(rates) == 1 else None)
    done = [duplicates[0] for duplicates in unique_done.values()]
    ratio = round(sum(firsts) / len(firsts)) if firsts and all(rate is not None for rate in firsts) else None
    # The same report can be attached to several briefs/versions. Count it once.
    reports = {}
    for task in tasks:
        for report in task['reports']:
            if report['date'] and start <= report['date'] <= end:
                reports.setdefault(report['file'], report)
    issue_values = [issue_count(board.read(fleet / path, fleet)) for path in reports]
    issues = sum(issue_values) if issue_values and all(v is not None for v in issue_values) else None
    rows, roster_path = [], None
    for language_choice in (language, 'en' if language == 'zh' else 'zh'):
        candidate = fleet / board.MAPS[language_choice][0]
        content = board.read(candidate, fleet)
        if content:
            try:
                rows = board.roster_rows(content, language)
                roster_path = candidate.name
            except ValueError:
                continue
            break
    card = board.read(project / 'AGENTS.md', project)
    waiting, _ = board.waiting_partition(card, end)
    has_section = bool(re.search(r'^##\s+(?:等我定|Decisions needed)\s*$', observed_text(card), re.M | re.I))
    pending, undated_count = 0, 0
    for item in waiting:
        match = re.match(r'^[\[（(]?(\d{4}-\d{2}-\d{2})', item['raw'])
        if not match or board.written_date(match[1]) is None:
            undated_count += 1
        elif item['days'] is not None and 0 <= item['days'] <= 6:
            pending += 1
    # Keep confirmed contributions even when incomplete records make the exact
    # total unknown. Do not reinterpret the existing None/zero semantics.
    questions_at_least = pending
    undated = undated_count > 0
    if undated:
        pending = None
    decided, incomplete_count, decision_source = 0, 0, None
    for language_choice in (language, 'en' if language == 'zh' else 'zh'):
        candidate = fleet / board.MAPS[language_choice][3]
        content = board.read(candidate, fleet)
        try:
            candidate.resolve().relative_to(fleet.resolve())
            readable_empty = candidate.is_file() and candidate.stat().st_size == 0
        except (OSError, ValueError, RuntimeError):
            readable_empty = False
        if not content and not readable_empty:
            continue
        decision_source = candidate.name
        for entry in decision_records(content, rows):
            if entry['date'] and not start <= entry['date'] <= end:
                continue
            if entry['human'] is False:
                continue
            if entry['date'] is None or entry['human'] is None:
                incomplete_count += 1
            else:
                decided += 1
        break
    questions_at_least += decided
    incomplete = incomplete_count > 0
    if incomplete:
        decided = None
    questions_available = bool(decision_source or has_section)
    questions = decided + pending if questions_available and decided is not None and pending is not None else None
    if not questions_available:
        decided = pending = None
        questions_at_least = 0
    return dict(language=language, start=start, end=end, project=clean(project_name(project, card), project, language),
                completed=len(done) or None, first_pass=ratio, issues=issues, questions=questions,
                questions_at_least=questions_at_least, questions_excluded=undated_count + incomplete_count,
                decided=decided, pending=pending, questions_available=questions_available,
                decision_source=decision_source, incomplete_decisions=incomplete, first_sources=hint_sources,
                incomplete_decision_count=incomplete_count, undated_question_count=undated_count,
                models=model_count(rows), roster=roster_path, reports=reports,
                file_time=any(report['fallback'] for task in tasks for report in task['reports']),
                completed_files=[report['file'] for _, report in done],
                issue_unknown=sum(value is None for value in issue_values), undated_questions=undated,
                brief_dirs=sorted({Path(task['file']).parts[0] for task in tasks}),
                review_dirs=sorted({Path(report['file']).parts[0] for task in tasks for report in task['reports']}),
                waiting_heading=next((heading for heading in ('等我定', 'Decisions needed') if re.search(
                    r'^##\s+' + re.escape(heading) + r'\s*$', card, re.M | re.I)), board.MAPS[language][4]))


def render(project, lang=None, today=None):
    data = collect(project, lang, today)
    card = sibling('fleet_card')
    language = data['language']
    zh = language == 'zh'
    title = '舰队周报' if zh else 'Fleet weekly report'
    title_labels = ('做完几单', '一次过审的占几成', '审核抓到几处错', '问了你几次') if zh else (
        'Tasks completed', 'First-pass rate', 'Issues caught in review', 'Times you were asked')
    brief_dirs = data['brief_dirs'] or [board.MAPS[language][1]]
    review_dirs = data['review_dirs'] or [board.MAPS[language][2]]
    brief_source = ' + '.join('fleet/' + name + '/' for name in brief_dirs)
    review_source = ' + '.join('fleet/' + name + '/' for name in review_dirs)
    folder = brief_source + ' + ' + review_source
    if zh:
        sources = [folder + '。成品存在且最新审核在本周通过的任务，每单计一次。说明首行写明未完成或卡住的任务除外。',
                   folder + '。本周完成的单中，首审明确通过的单数 ÷ 完成单数。',
                   review_source + '：只数未通过审核的必改问题；优先结果表不通过行，否则数必修项，排除建议，每份报告只计一次。',
                   ('fleet/' + data['decision_source'] if data['decision_source'] else '决定记录（未找到）') +
                   '：本周“谁定”明确含人的条目；加 AGENTS.md「' + data['waiting_heading'] + '」本周新记、仍在等的条目。']
    else:
        sources = [folder + '. Count each task once if its deliverable exists and its latest review passed this week. Exclude tasks whose notes report incomplete or blocked work on the first line.',
                   folder + '. Of the tasks counted as complete this week, the percentage that explicitly passed on the first review.',
                   'Review reports in ' + review_source + ': required changes in rejected reviews only; use failed result rows, otherwise mandatory items; exclude suggestions and count each report once.',
                   ('fleet/' + data['decision_source'] if data['decision_source'] else 'Decision log (not found)') +
                   ': entries explicitly decided by a human this week, plus new requests still pending in AGENTS.md “' + data['waiting_heading'] + '”.']
    if data['first_sources']:
        sources[1] += (' 显式首审链接：' if zh else ' Explicit first-review links: ') + ', '.join(data['first_sources'])
    sources[1] += (' 首审声明冲突或缺失时留空，不凭曾退回或版本名推断首审。' if zh else
                   ' Conflicting or missing first-review declarations stay unknown; prior rejection or a version name alone is not evidence of the first round.')
    if data['file_time']:
        sources[0] += ' 无文内日期时按交付文件时间。' if zh else ' Undated records use delivery file time.'
        sources[2] += ' 无文内日期时按交付文件时间。' if zh else ' Undated records use delivery file time.'
    if data['undated_question_count']:
        sources[3] += (' {} 条仍在等的记录缺有效日期，未计入。'.format(data['undated_question_count']) if zh else
                       ' {} pending request{} excluded for a missing or invalid date.'.format(
                           data['undated_question_count'], 's' if data['undated_question_count'] != 1 else ''))
    if data['issue_unknown']:
        sources[2] += ' 有退回报告没有可数的必改问题清单。' if zh else ' Some rejected reports lack countable required changes.'
    if data['incomplete_decision_count']:
        sources[3] += (' {} 条决定缺有效日期或“谁定”不明确，未计入。'.format(data['incomplete_decision_count']) if zh else
                       ' {} decision{} excluded for a missing or invalid date or unclear decision maker.'.format(
                           data['incomplete_decision_count'], 's' if data['incomplete_decision_count'] != 1 else ''))
    if data['questions_excluded']:
        sources[3] += (' 共 {} 条不完整记录未计入；'.format(data['questions_excluded']) if zh else
                       ' {} incomplete record{} excluded in total; '.format(
                           data['questions_excluded'], 's' if data['questions_excluded'] != 1 else ''))
        if data['questions_at_least']:
            sources[3] += ('卡上显示 ≥{}，表示已确认的次数下限，总数仍未知。'.format(data['questions_at_least']) if zh else
                           'the card shows ≥{} as the confirmed lower bound; the total remains unknown.'.format(data['questions_at_least']))
        else:
            sources[3] += ('本周尚无可确认计入的记录，卡上显示“—”，总数未知。' if zh else
                           'no countable records are confirmed for this week, so the card shows “—”; the total is unknown.')
    unknown_questions_note = ('还没有记录' if zh else 'No records yet')
    if data['questions_available'] and data['questions'] is None:
        if zh:
            unknown_questions_note = ('至少这么多；{} 条缺有效日期或谁定，没算进来' if data['questions_at_least'] else
                                      '{} 条缺有效日期或谁定，没算进来，总数不知道').format(data['questions_excluded'])
        else:
            unknown_questions_note = ('At least this many; {} left out: no valid date or unclear decision maker' if data['questions_at_least'] else
                                      'Total unknown; {} left out: no valid date or unclear decision maker').format(data['questions_excluded'])
    if zh:
        notes = ['这周审核通过的单' if data['completed'] is not None else '这周还没有审核通过的单',
                 '第一次审核就通过的，占审核通过单的比例' if data['first_pass'] is not None else
                 ('还缺第一次审核的记录，暂算不了比例' if data['completed'] else '还没有审核通过的单，暂算不了比例'),
                 '这周审核退回时列出的必改问题条数' if data['issues'] is not None else
                 ('退回记录没写清哪些必须改，暂算不全' if data['reports'] else '这周还没有审核记录'),
                 ('这周没问你' if data['questions'] == 0 else '你定了 {} 件，还有 {} 件在等你'.format(data['decided'], data['pending']))
                 if data['questions'] is not None else unknown_questions_note]
    else:
        notes = ['Tasks that passed review this week' if data['completed'] is not None else 'No tasks passed review this week',
                 'First-review passes as a share of all tasks that passed review' if data['first_pass'] is not None else
                 ('The first review is not recorded, so the rate is unknown' if data['completed'] else 'No passed tasks yet, so there is no rate to show'),
                 'Required changes listed in rejected reviews this week' if data['issues'] is not None else
                 ('Rejected reviews do not clearly identify required changes' if data['reports'] else 'No review records for this week'),
                 ('No questions for you this week' if data['questions'] == 0 else 'You decided {}; {} still waiting for you'.format(data['decided'], data['pending']))
                 if data['questions'] is not None else unknown_questions_note]
    asked = str(data['questions']) if data['questions'] is not None else (
        '≥{}'.format(data['questions_at_least']) if data['questions_at_least'] else '—')
    values = [str(data['completed']) if data['completed'] is not None else '—',
              str(data['first_pass']) + '%' if data['first_pass'] is not None else '—',
              str(data['issues']) if data['issues'] is not None else '—', asked]
    # Native SVG text/geometry is both the screen card and the PNG source.
    # Width 1080 keeps 22px notes readable on a phone after scaling.
    out = ['<rect width="1080" height="100%" fill="#f7f8fa"/>',
           '<rect x="64" y="64" width="52" height="7" rx="3" fill="#8a4ed1"/>',
           card.svg_text(title, 64, 132, size=46, weight=700, fill='#3b2673')]
    y = 197
    project_lines = card.text_lines(data['project'], 952, size=34)
    out.append(card.wrapped_text(data['project'], 64, y, 952, size=34, line_height=44, weight=600))
    y += len(project_lines) * 44 + 8
    out.append(card.svg_text('{} — {}'.format(data['start'].isoformat(), data['end'].isoformat()), 64, y, size=26, fill='#686a72'))
    y += 44
    models = ('舰队里 {} 家模型' if zh else '{} models in the fleet').format(data['models']) if data['models'] is not None else (
        '模型数：—' if zh else 'Models: —')
    out.append(card.svg_text(models, 64, y, size=26, fill='#3b2673', weight=600))
    y += 42
    for key, label, value, note in zip(('completed', 'first-pass', 'issues', 'questions'), title_labels, values, notes):
        note_lines = card.text_lines(note, 872, size=26)
        height = 182 + 32 * (len(note_lines) - 1)
        out.append('<g id="metric-{}"><rect x="64" y="{}" width="952" height="{}" rx="24" fill="#fff"/>'.format(key, y, height))
        out.append(card.svg_text(label, 104, y + 48, size=29, fill='#3b2673', weight=600))
        out.append(card.svg_text(value, 104, y + 113, size=58, fill='#3b2673', weight=700))
        out.append(card.wrapped_text(note, 104, y + 153, 872, size=26, line_height=32, fill='#686a72'))
        out.append('</g>')
        y += height + 20
    footer = '按现有记录生成 · 文件变了，重新生成就更新' if zh else 'Built from existing records · Run again to refresh'
    out.append(card.svg_text(footer, 64, y + 22, size=23, fill='#686a72'))
    height = max(1350, y + 66)
    svg = '<svg xmlns="http://www.w3.org/2000/svg" id="share-card" width="1080" height="{}" viewBox="0 0 1080 {}" role="img" aria-label="{}" font-family="Noto Sans SC, Source Han Sans SC, Microsoft YaHei, Segoe UI, sans-serif">{}</svg>'.format(
        height, height, title, '\n'.join(out))
    details = '<section id="calculation-notes" style="font-size:14px;line-height:1.6;overflow-wrap:anywhere"><h2>{}</h2><ul>{}</ul></section>'.format(
        '这些数怎么算' if zh else 'How these numbers are calculated',
        ''.join('<li><strong>{}</strong> {}</li>'.format(escape(label), escape(source)) for label, source in zip(title_labels, sources)))
    return card.document(svg, language, title, 'fleet-weekly-{}-{}.png'.format(data['end'].isoformat(), language), details_html=details)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate an offline weekly card. / 生成离线周报卡。')
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--lang', choices=('zh', 'en'))
    parser.add_argument('--today', help='Window end date, YYYY-MM-DD / 七天窗口的最后日期')
    args = parser.parse_args(argv)
    language = board.project_language(args.project, args.lang)
    try:
        today = board.as_today(args.today)
    except (TypeError, ValueError):
        parser.error('--today requires YYYY-MM-DD')
    output = args.project / 'fleet' / OUTPUTS[language]
    try:
        page = render(args.project, language, today)
        output.resolve().relative_to(args.project.resolve())
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(page)
    except (OSError, UnicodeError, ValueError, RuntimeError):
        print('ERROR：周报卡写入失败，请核对项目目录。' if language == 'zh' else
              'ERROR: Could not write weekly card; check the project directory.', file=sys.stderr)
        return 2
    print('fleet/' + OUTPUTS[language])
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
