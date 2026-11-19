#!/usr/bin/env python3
"""Build an offline fleet board from existing project records (Python 3.9+)."""
import argparse
from datetime import date, datetime, timedelta
from html import escape
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote

# File names and section headings follow fleet-setup/templates/{zh,en}.
MAPS = {
    'zh': ('成员.md', '任务书', '交付', '决定.md', '等我定', '看板.html'),
    'en': ('members.md', 'task-briefs', 'deliveries', 'decisions.md', 'Decisions needed', 'board.html'),
}
LABELS = {
    'zh': dict(title='舰队看板', waiting='等你', active='在干的活', done='做成了', people='谁在干活',
               none='现在没有要你做的', no_work='当前没有在干的活', empty='还没有记录，开始用以后会出现在这里', no_done='最近 7 天还没有审核通过的单', unknown='看不出', no='否',
               dispatched='派出', running='在跑', received='收到', pending='待审', passed='审过', returned='退回', missing='缺成品',
               human='人', human_role='定目标和边界', busy='忙', idle='闲', elapsed='用了', age='已等', days='天', day='天', today='今天',
               ended='跑完', receipt='收到', review='审过', yes='是', waiting_for='在等', assigned='派驻', notes='另有 {} 条说明写明当前不用你做',
               weekly='这周审过 {} 单', first='一次就过 {}%', file_time='按文件时间', chart='完整组织图',
               relative='[路径已隐藏]', details='依据', note='按 fleet/ 里的文件生成；文件变了，重新生成就更新。',
               flagged='调用超时或失败', unidentified='岗位看不出'),
    'en': dict(title='Fleet board', waiting='Needs you', active='Work in progress', done='Done', people='Who is working',
               none='Nothing needs you right now.', no_work='No work in progress.', empty='No records yet. They will show up here once you start.', no_done='Nothing passed review in the last 7 days.', unknown='Unknown', no='No',
               dispatched='Dispatched', running='Running', received='Received', pending='Awaiting review', passed='Review passed', returned='Returned', missing='Missing deliverable',
               human='Human', human_role='Sets goals and boundaries', busy='Busy', idle='Idle', elapsed='Elapsed', age='Waiting', days='days', day='day', today='Today',
               ended='Run ended', receipt='Received', review='Review passed', yes='Yes', waiting_for='Waiting', assigned='Assigned', notes='{} more notes say nothing is needed from you now',
               weekly='{} passed review this week', first='First-pass rate {}%', file_time='By file time', chart='Full organization chart',
               relative='[path hidden]', details='Evidence', note='Built from the files in fleet/. Run it again to refresh.',
               flagged='Call timed out or failed', unidentified='Role unknown'),
}
STATES = ('dispatched', 'running', 'received', 'pending', 'passed', 'returned', 'missing', 'unknown')
NOTES_SUFFIXES = ('-notes.md', '-说明.md')
_chart = None


def roster_rows(text, language):
    global _chart
    if _chart is None:
        spec = importlib.util.spec_from_file_location('_fleet_board_chart', Path(__file__).with_name('fleet_chart.py'))
        module = importlib.util.module_from_spec(spec)
        bytecode = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = bytecode
        _chart = module
    return _chart.read_roster(text, lang=language)


def project_language(project, language=None):
    if language is not None:
        if language not in MAPS:
            raise ValueError('lang must be zh or en')
        return language
    fleet = Path(project) / 'fleet'
    for lang, chart in (('zh', '组织图.md'), ('en', 'chart.md')):
        names = MAPS[lang]
        if any((fleet / name).exists() for name in (names[0], names[1], names[2], names[3], chart)):
            return lang
    return 'zh'


def read(path, boundary):
    """Read only within the intended project, including when files are symlinks."""
    try:
        path.resolve().relative_to(boundary.resolve())
        return path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError, ValueError, RuntimeError):
        return ''


def section(text, headings):
    """Extract a Markdown section, respecting headings and fenced examples."""
    out, active, level, fenced = [], False, 0, False
    for line in text.splitlines():
        if re.match(r'^\s*(```|~~~)', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r'^(#{1,6})\s+(.+?)\s*#*$', line)
        if match:
            if active and len(match[1]) <= level:
                break
            if match[2].strip().casefold() in {h.casefold() for h in headings}:
                active, level = True, len(match[1])
                continue
        if active:
            out.append(line)
    return '\n'.join(out).strip()


def as_today(value=None):
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError('Use YYYY-MM-DD')
    return date.fromisoformat(value)


def written_date(text):
    patterns = (
        r'(?im)^\s*[-*]?\s*(?:日期|审核日期|报告日期|交付日期|Date|Review date|Reviewed(?: at)?|Delivered(?: at)?|Timestamp)\s*[:：]\s*(\d{4}-\d{2}-\d{2})',
        r'(?m)^#{1,6}[^\n]*(\d{4}-\d{2}-\d{2})',
        r'(?im)^\s*(?:On\s+)?(\d{4}-\d{2}-\d{2})(?:[ T]|$)',
        r'(?:审核于|交付于|Reviewed on|Delivered on)\s*(\d{4}-\d{2}-\d{2})',
        r'^(\d{4}-\d{2}-\d{2})$',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            try:
                return date.fromisoformat(match[1])
            except ValueError:
                continue
    return None


def waiting_entries(card, today):
    body = section(card, ('等我定', 'Decisions needed'))
    items = []
    for line in body.splitlines():
        match = re.match(r'^\s*(?:[-*+] |\d+[.)] )(.+)', line)
        if match:
            items.append(match[1].strip())
        elif line.strip() and items:
            items[-1] += ' ' + line.strip()
    if not items and body:
        items = [body]
    result = []
    for index, text in enumerate(items):
        if '〔待定' in text:
            continue
        match = re.match(r'^[\[（(]?(\d{4}-\d{2}-\d{2})[\]）)]?\s*[:：|—-]?\s*', text)
        dated = written_date(match[1]) if match else None
        days = (today - dated).days if dated and dated <= today else None
        body_text = text[match.end():] if match else text
        owner = re.search(r'(?:谁在等|谁提的|提出人|提议人|等待方|Waiting(?: for)?|Requested by|Proposed by|Raised by)\s*[:：]\s*([^；;，,。|]+)', body_text, re.I)
        who = owner[1].strip() if owner else ''
        if owner:
            body_text = (body_text[:owner.start()] + body_text[owner.end():]).strip(' ;；,，')
        result.append(dict(text=body_text, raw=text, who=who, days=days, has_date=bool(match), order=index))
    return sorted(result, key=lambda item: (item['days'] is None, -(item['days'] or 0), item['order']))


def no_action_needed(text):
    """Recognize explicit statements, not an absence inferred from context."""
    if re.fullmatch(r'(?:无|暂无|没有|None|None yet)[.。!！ ]*', text.strip(), re.I):
        return True
    patterns = (
        r'当前没有|暂无|没有待|无待|不再需要|已不需要|不再视为|不再将[^；;。!?？！\n]*视为',
        r'\b(?:nothing|none)\s+pending\b|\bno\s+pending\b|\bnothing\s+to\s+decide\b',
        r'\bno\s+longer\s+(?:needed|required|(?:(?:a|an|the)\s+)?prerequisite)\b',
        r'\bcurrently\s+no\b',
        r'\bno\s+[^.;!?\n]{1,80}?\s+(?:is|are)\s+currently\s+in\s+effect\b',
    )
    # Keep questions and conditional statements; a later explicit clause can
    # still state that no action is currently pending.
    clauses = re.findall(r'[^；;。.!?？！]+[。.!?？！]?', text)
    statements = [clause for clause in clauses if not re.search(
        r'[?？]|是否|是不是|如果|假如|若|并非|并不是|不是|不能说|不能认为|不能认定|'
        r"\b(?:if|whether|perhaps|maybe|not true|not the case|not accurate|incorrect|false|cannot say|can't say|cannot claim|cannot assume)\b|"
        r'\bnot\s+(?:nothing|none|no pending)\b', clause, re.I)]
    if any(re.search(r'请(?:人)?(?:确认|决定|批准|选择)|\bplease\s+(?:confirm|decide|approve|choose)\b', clause, re.I) for clause in clauses):
        return False
    return any(re.search(pattern, clause, re.I) for clause in statements for pattern in patterns)


def waiting_partition(card, today):
    waiting, notes = [], []
    for item in waiting_entries(card, today):
        (notes if no_action_needed(item['text']) else waiting).append(item)
    return waiting, notes


def waiting_records(card, today):
    return waiting_partition(card, today)[0]


def outcome(conclusion):
    if re.search(r'未通过|不通过|退回|退作者|fail|reject|return|changes required|(?:not|no) (?:yet )?(?:pass(?:ed)?|approved|accepted|successful)|needs? changes|requires? changes', conclusion, re.I):
        return 'returned'
    return 'passed'


def role_for(text, roster):
    current = section(text, ('现状', 'Current state'))
    for row in roster:
        if re.search(r'(?im)^\s*[-*]?\s*(?:派给|执行岗位|负责岗位|Assigned to|Assignee)\s*[:：]\s*' + re.escape(row['Role']) + r'(?![A-Za-z])', text):
            return row['Role'], row['Assigned']
    for row in roster:
        role = re.escape(row['Role'])
        if re.search(r'(?:已派发给|已派出给|派给|dispatched to)\s*' + role + r'(?![A-Za-z])', current, re.I) or re.search(role + r'\s*(?:正在运行|正在执行|is running|is working)', current, re.I):
            return row['Role'], row['Assigned']
    for row in roster:
        if row['Role'].casefold() in ('作者', 'writer', 'author') and re.search(r'作者交回|作者修订|由原作者|original (?:writer|author)|(?:writer|author) returns|(?:writer|author) revises', text, re.I):
            return row['Role'], row['Assigned']
    return '', ''


def elapsed_record(text):
    stamps = {'start': [], 'end': []}
    for line in text.splitlines():
        kind = None
        if re.search(r'开始时间|启动时间|派出时间|派发时间|Started(?: at)?|Start time|Dispatched at', line, re.I):
            kind = 'start'
        elif re.search(r'结束时间|完成时间|收到时间|Finished(?: at)?|Ended(?: at)?|End time|Completed at|Received at', line, re.I):
            kind = 'end'
        if not kind:
            continue
        match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?', line)
        if match:
            try:
                moment = datetime.fromisoformat(match[0].replace('Z', '+00:00'))
                stamps[kind].append(moment)
            except ValueError:
                pass
    if not all(stamps.values()):
        return None
    try:
        seconds = (max(stamps['end']) - min(stamps['start'])).total_seconds()
        return int(seconds) if seconds >= 0 else None
    except TypeError:
        return None


def references(text, files, *, product_stems=False):
    """Match fleet-relative names without opening paths supplied by Markdown."""
    normalized = unquote(text).replace('\\', '/')
    found = set()
    # A reference to a run log does not declare a product with that stem.
    ending = r'(?i:\.(?!log\b)[\w-]+)' if product_stems else ''
    # Longest first prevents report.md from also matching old-report.md.
    for relative in sorted(files, key=len, reverse=True):
        name = relative.rsplit('/', 1)[-1]
        for candidate in ('fleet/' + relative, relative, name):
            if re.search(r'(?<![\w/.-])' + re.escape(candidate) + ending + r'(?![\w.-])', normalized):
                found.add(relative)
                break
    return found


def review_result(text):
    # Only an explicit conclusion in an actual report, never a checklist or goal.
    for line in text.splitlines():
        stripped = line.strip().lstrip('-* ').strip()
        if re.match(r'^(结论|审核结论|质量是否通过|Conclusion|Verdict|Review result|Result)\s*[:：]', stripped, re.I):
            value = re.split('[:：]', stripped, maxsplit=1)[1].strip()
            if re.search(r'尚未(?:审核|审过)|未审核|待审|暂无|not (?:yet )?reviewed|pending|no review|〔待定', value, re.I):
                continue
            if re.search(r'通过|未通过|退回|退作者|不通过|pass|fail|reject|returned|changes required|requires? changes|needs? changes|approved|审过', value, re.I):
                return stripped
    return ''


def recorded_state(text):
    # A brief's requirements/handback describe future work, not observed progress.
    current = section(text, ('现状', 'Current state'))
    facts = []
    for line in current.splitlines():
        value = line.strip().lstrip('-* ').strip()
        value = re.sub(r'`[^`]*`|(?:\S+/)\S+\.md', '', value)
        if not value or '〔待定' in value or re.match(r'^(推断的|猜的|Inferred|Guessed)', value, re.I):
            continue
        if re.search(r'完成后|收到后|审核后|将会|计划|\b(?:if|when|will|should|must)\b', value, re.I):
            continue
        facts.append(value)
    for state, positive, negative in (
        ('pending', r'等待审核|待审核|待审|尚未审核|awaiting review|pending review|not yet reviewed', r'未等待审核|未待审|无需审核|不需审核|no review needed|not (?:awaiting|pending) review'),
        ('received', r'已收到(?:交付|回复)|delivery received|received (?:the )?delivery', r'未收到|尚无|not received|no delivery'),
        ('running', r'正在运行|正在执行|在跑|\brunning\b|in progress', r'未运行|尚未(?:运行|执行|启动)|不在跑|未启动|已结束|not running|no .*running|stopped|has ended|(?:正在运行|正在执行|在跑)\s*[:：]\s*(?:无|没有)|running\s*:\s*(?:none|no|false)\b'),
        ('dispatched', r'已派发|已派出|\bdispatched\b', r'尚未(?:派发|派出)|未派|not dispatched|not yet dispatched'),
    ):
        for value in reversed(facts):
            if re.search(positive, value, re.I) and not re.search(negative, value, re.I):
                return state, value
    return 'unknown', ''


def output_instructions(text):
    # Current state and preserved inputs are not output declarations.
    output = '\n'.join(section(text, (heading,)) for heading in (
        '要做的', 'Work required', '边界', 'Boundaries', '交回', 'Handback'))
    lines = []
    for line in re.split(r'[\n；;。]|(?<=[.!?])\s+(?=[A-Z])', output):
        if re.search(r'保留|原稿|旧稿|旧交付|原交付|不要覆盖|不覆盖|preserve|old |original |input|do not overwrite', line, re.I):
            continue
        if re.match(r'^\s*[-*]?\s*(?:可读|Read(?:able)?\s*:)', line, re.I):
            continue
        if re.search(r'交付|成品|保存(?:到|为)|写(?:入|到|进)|deliver|save|write|output', line, re.I):
            lines.append(line)
    return '\n'.join(lines)


def unfinished_note(first_line):
    # Match the status even when formatted inline. Keep the original for display.
    status = re.sub(r'</?[A-Za-z][^<>]*>', '', first_line).lstrip()
    return bool(re.match(r'(?:(?:完成状态|状态|Status)\s*[:：]\s*)?'
                         r'(?:(?:Incomplete|Blocked|Not (?:yet )?(?:completed?|finished|done))\b|'
                         r'(?:尚未|未|没(?:有)?)完成|卡在|卡住)', status, re.I))


def task_records(project, language, with_roster=True):
    fleet = project / 'fleet'
    briefs, deliveries, logs, notes = {}, {}, {}, {}
    other_products = set()
    for names in MAPS.values():
        for path in sorted((fleet / names[1]).rglob('*.md')):
            briefs[path.relative_to(fleet).as_posix()] = read(path, fleet)
        for path in sorted((fleet / names[2]).rglob('*')):
            relative = path.relative_to(fleet).as_posix()
            if relative.casefold().endswith(NOTES_SUFFIXES):
                notes[relative] = read(path, fleet).partition('\n')[0].strip()
            elif path.suffix.lower() == '.log':
                logs[relative] = read(path, fleet)
            elif path.suffix.lower() == '.md':
                deliveries[relative] = read(path, fleet)
            else:
                # Non-Markdown products need only a nonempty, project-local file.
                try:
                    path.resolve().relative_to(fleet.resolve())
                    if path.is_file() and path.stat().st_size:
                        other_products.add(relative)
                except (OSError, ValueError, RuntimeError):
                    continue
    note_stems = {path: path.rsplit('-', 1)[0] for path in notes}
    report_conclusions = {}
    for path, content in deliveries.items():
        stem = Path(path).stem
        if re.search(r'清单|checklist', stem, re.I):
            continue
        if re.search(r'(?:审核|review)$', stem, re.I) or re.search(r'^# +.*(?:审核|\breview\b)', content, re.I | re.M):
            conclusion = review_result(content)
            if conclusion:
                report_conclusions[path] = conclusion
    # A review is evidence about a product, including for legacy same-name briefs.
    products = {p for p in deliveries.keys() | other_products
                if p not in report_conclusions and not re.search(r'审核|(?<![a-z])review|checklist', Path(p).stem, re.I)}
    results = []
    labels = LABELS[language]
    roster = []
    if with_roster:
        for names in MAPS.values():
            source = read(fleet / names[0], fleet)
            if source:
                try:
                    roster = roster_rows(source, language)
                except ValueError:
                    continue
                break
    for relative, text in sorted(briefs.items()):
        if not text.strip():
            continue
        stem = Path(relative).stem
        names = next(names for names in MAPS.values() if Path(relative).parts[0] == names[1])
        delivery_dir = Path(names[2]).joinpath(*Path(relative).parts[1:-1])
        output = output_instructions(text)
        targets = references(output, products)
        default_stems = {(delivery_dir / (stem + suffix)).as_posix() for suffix in ('', '-交付', '-delivery')}
        named_stems = references(output, default_stems | set(note_stems.values()), product_stems=True)
        named_notes = references(output, notes)
        if not (targets or named_stems or named_notes):
            # Older briefs can identify a Markdown delivery by the brief's filename.
            targets = {p for p in products if p in deliveries and Path(p).with_suffix('').as_posix() in default_stems}
            named_stems = default_stems
        nonempty = sorted(p for p in targets if p in other_products or deliveries[p].strip())
        task_notes = [(path, line) for path, line in notes.items()
                      if path in named_notes or note_stems[path] in named_stems]
        notes_only = bool(task_notes) and not nonempty
        note_problems = [(path, line) for path, line in task_notes if unfinished_note(line)]
        relevant_logs = []
        log_pairs = {(delivery_dir, stem)} | {(Path(p).parent, Path(p).stem) for p in targets}
        for path, content in logs.items():
            if (Path(path).parent, Path(path).stem) in log_pairs or references(content, (relative,)):
                relevant_logs.append((path, content))
        reviews = []
        if nonempty:
            for path, conclusion in report_conclusions.items():
                content = deliveries[path]
                same_name = any(Path(path).parent == Path(p).parent and Path(path).stem in
                                (Path(p).stem + '-审核', Path(p).stem + '-review') for p in nonempty)
                if same_name or references(content, nonempty) or references(content, (relative,)):
                    reviews.append((path, conclusion))
        state, detail = recorded_state(text)
        if not nonempty and state in ('received', 'pending'):
            state, detail = 'unknown', ''
        evidence = [(relative, detail)] if detail else []
        if nonempty:
            state = 'received'
            evidence = [(p, labels['receipt']) for p in nonempty]
        succeeded, failed, exit_codes = [], [], []
        for path, content in relevant_logs:
            codes = [int(code) for code in re.findall(r'(?:exit (?:code|status)|退出(?:码|状态|记录))\s*(?:[:：=]|为|是)?\s*(-?\d+)\b', content, re.I)]
            exit_codes.extend(codes)
            if any(code != 0 for code in codes):
                failed.append((path, labels['flagged']))
            success = ('状态：成功；已收到交付，尚未审核。' in content or
                       'Status: succeeded; delivery received, not yet reviewed.' in content)
            if success:
                succeeded.append((path, labels['pending']))
            if re.search(r'Blocked:|卡在哪：|错误：|Error:', content, re.I):
                failed.append((path, labels['flagged']))
        if succeeded and failed:
            state, evidence = 'unknown', succeeded + failed
        elif succeeded and nonempty:
            state, evidence = 'pending', succeeded
        elif failed:
            if not nonempty:
                state = 'unknown'
            evidence = failed
        title = next((re.sub(r'^#\s*(?:任务书|Task brief)\s*[:：]?\s*', '', line, flags=re.I)
                      for line in text.splitlines() if line.startswith('# ')), stem)
        role, assigned = role_for(text, roster)
        report_items = []
        for path, conclusion in reviews:
            content = deliveries[path]
            explicit_date = written_date(content)
            if not explicit_date:
                explicit_date = next((day for p in nonempty if (day := written_date(deliveries.get(p, '')))), None)
            if not explicit_date:
                explicit_date = next((written_date(c) for _, c in relevant_logs if written_date(c)), None)
            target = next((p for p in nonempty if references(content, (p,))), nonempty[0])
            fallback = False
            if not explicit_date:
                try:
                    explicit_date = datetime.fromtimestamp((fleet / target).stat().st_mtime).date()
                    fallback = True
                except OSError:
                    pass
            first = bool(re.search(r'(?im)^\s*[-*]?\s*(?:审核轮次|Review round)\s*[:：]\s*1\b|^#{1,6}\s*(?:首次审核|First review)\b', content))
            report_items.append(dict(file=path, delivery=target, conclusion=conclusion, outcome=outcome(conclusion),
                                     date=explicit_date, fallback=fallback, first=first))
        report_items.sort(key=lambda item: (item['date'] or date.min, natural_key(item['file'])))
        # Receipt and review require a nonempty product. A notes-only handback
        # is missing its product even if marked Complete. An Incomplete/Blocked
        # first line takes precedence over any review and keeps the task blocked.
        if note_problems:
            state, evidence = 'unknown', note_problems
        elif notes_only:
            state, evidence = 'missing', task_notes
        elif report_items:
            state, evidence = report_items[-1]['outcome'], reviews
        if not evidence:
            evidence = [(relative, labels['unknown'])]
        execution = '\n'.join(c for _, c in relevant_logs)
        ended = bool(succeeded or failed or exit_codes or re.search(r'退出(?:记录|码|状态)?(?:为|是|:|：)?\s*0|exit (?:code|record)[^\n]*\b0\b', '\n'.join(deliveries[p] for p, _ in reviews), re.I))
        current = section(text, ('现状', 'Current state'))
        bad_current = bool(re.search(r'调用(?:超时|失败)|当前.*卡住|\bBlocked:|invocation (?:failed|timed out)', current, re.I))
        blocked = bool(note_problems or state == 'returned' or (not report_items and (failed or bad_current)))
        identifier = re.match(r'^(\d{1,6})(?=[\s:：|｜-]|$)', title)
        group = Path(relative).parts[0] + ':' + identifier[1] if identifier else 'file:' + relative
        results.append(dict(file=relative, title=title, group=group, state=state, evidence=evidence, role=role, assigned=assigned,
                            blocked=blocked, outcome=state if state in ('passed', 'returned') else None,
                            ended=ended, received=bool(nonempty), notes_only=notes_only,
                            note_problem=' · '.join(line for _, line in note_problems), reports=report_items, deliveries=nonempty,
                            elapsed=elapsed_record(current + '\n' + execution) if with_roster else None, brief=text))
    return results


# Local color and font values retained from the package visual system.
CSS = """
:root{--deep:#3b2673;--primary:#8a4ed1;--accent:#b35be8;--soft:#e9e6ff;--text:#0f1115;--muted:#686a72;
--canvas:#f7f8fa;--line:#0f11151a;--red:#b64242;--font-zh:'Noto Sans SC','Source Han Sans SC','Microsoft YaHei',sans-serif;
--font-en:'Inter','Noto Sans','Segoe UI',sans-serif}
*{box-sizing:border-box}body{margin:0;color:var(--text);background:var(--canvas);font:14px/1.5 var(--font-zh)}
html[lang=en] body{font-family:var(--font-en),var(--font-zh)}main{max-width:1120px;margin:auto;padding:24px 32px 16px}
header{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin-bottom:16px}
h1{font-size:30px;line-height:1.2;color:var(--deep);margin:0;letter-spacing:-.03em}.stamp{font-size:12px;color:var(--muted)}
section{padding:16px 20px;border:1px solid var(--line);background:#fff;border-radius:16px;margin-bottom:12px;min-width:0}
.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:10px}
h2{margin:0;color:var(--deep);font-size:17px;letter-spacing:-.02em}.muted,.empty{color:var(--muted);font-size:12px}
.empty{margin:6px 0}.muted{margin:5px 0}.waiting{background:linear-gradient(115deg,var(--deep),var(--primary));color:#fff;border:0}
.waiting h2,.waiting .muted,.waiting .empty{color:#fff}.waiting .empty{font-size:16px;font-weight:600;margin:8px 0 2px}
.wait-item{display:grid;grid-template-columns:80px minmax(0,1fr);overflow-wrap:anywhere;gap:12px;padding:8px 0;border-top:1px solid #ffffff30}
.wait-item.undated{display:block}.wait-item>div{min-width:0}.waiting-notes{color:#ffffffb3;margin-top:10px;padding-top:6px;border-top:1px solid #ffffff30}.waiting-notes ul{margin:8px 0 0;padding-left:18px}.waiting-notes li{margin-top:6px;overflow-wrap:anywhere}.wait-age{font-weight:700}.wait-item p{margin:0}.wait-question{color:inherit;font-size:inherit}.wait-question summary{display:flex;gap:6px}.wait-question summary:after{content:"+";opacity:.6}.wait-question summary span{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}.wait-question[open] summary span{display:none}.wait-question[open] summary:after{content:"−"}.full-question{padding-top:4px}.who{font-size:11px;opacity:.8}
.work-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(150px,.8fr) auto;gap:8px 16px;
padding:10px 0;border-top:1px solid var(--line);align-items:center;overflow-wrap:anywhere}
.work-row:first-of-type{border-top:0}.title{font-size:14px;font-weight:650;margin:0;color:var(--deep)}
.meta{font-size:11px;color:var(--muted);margin-top:3px}.stage{text-align:right}.badge{display:inline-block;font-size:11px;
padding:3px 8px;border-radius:7px;background:var(--soft);color:var(--deep);font-weight:650;white-space:normal}
.blocked .badge{background:#b6424212;color:var(--red)}.blocked .title{color:var(--red)}.blocked{border-left:3px solid var(--red);padding-left:10px}
.checks{font-size:11px;color:var(--muted);margin-top:3px}.weekly-note{font-weight:400;font-size:11px;color:var(--muted)}.weekly{font-size:13px;font-weight:650;color:var(--deep)}
.done-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 16px;padding:9px 0;border-top:1px solid var(--line);overflow-wrap:anywhere}
.done-row:first-of-type{border-top:0}.done-row .stage{min-width:90px}.done-row details{grid-column:1/-1}
a{color:var(--deep);text-decoration:none}a:hover{text-decoration:underline}a:focus-visible{outline:2px solid var(--primary);outline-offset:3px}
.people-grid{display:flex;flex-wrap:wrap;gap:8px}.person{flex:1 1 160px;max-width:260px;min-width:0;border:1px solid var(--line);
border-radius:10px;padding:10px 12px;background:var(--canvas);overflow-wrap:anywhere}.person h3{font-size:13px;color:var(--deep);margin:0}
.person .meta{font-size:11px;margin:3px 0 0}.person.human{background:var(--soft)}.person-head{display:flex;justify-content:space-between;gap:8px}
.busy{color:var(--primary);font-weight:650}.idle{color:var(--muted)}details{font-size:11px;color:var(--muted)}summary{cursor:pointer}
.evidence{white-space:pre-wrap;overflow-wrap:anywhere;padding-top:6px}footer{font-size:10px;color:var(--muted);padding:0 3px}
@media(max-width:600px){main{padding:12px 12px 8px}h1{font-size:25px}header{margin-bottom:12px}section{padding:12px 14px;margin-bottom:10px}
h2{font-size:16px}.section-head{margin-bottom:7px;flex-wrap:wrap;gap:4px}.work-row{grid-template-columns:minmax(0,1fr) auto;gap:3px 8px;padding:8px 0}
.work-row .assignment{grid-column:1/-1;grid-row:2}.work-row .stage{grid-column:2;grid-row:1}.title{font-size:13px}
.checks{font-size:10px}.wait-item{grid-template-columns:66px minmax(0,1fr);gap:8px;font-size:12px}.wait-age{font-size:12px}
.waiting .empty{font-size:14px}.person{flex:1 1 calc(50% - 8px);max-width:none;padding:8px 10px}.person .meta{font-size:10px;line-height:1.35}.done-row{padding:8px 0}
.done-row .stage{min-width:74px}.weekly{font-size:12px}.stamp{font-size:10px}.badge{font-size:10px;padding:3px 6px}}
@media print{main{padding:10px}section{break-inside:avoid}details{display:none}}
"""


def natural_key(value):
    return tuple((1, int(part)) if part.isdigit() else (0, part.casefold())
                 for part in re.split(r'(\d+)', value))


def task_overview(tasks, today):
    """One current state per task, shared by the page and status line."""
    groups = {}
    for task in tasks:
        groups.setdefault(task['group'], []).append(task)
    active, done_items, firsts = [], [], []

    def version(task):
        versions = re.findall(r'(?i)(?:^|[\s_-])v(\d+)', task['title'] + ' ' + task['file'])
        return max(map(int, versions), default=1)

    def report_order(pair):
        return pair[1]['date'], natural_key(pair[1]['file'])

    for members in groups.values():
        latest_task = max(members, key=lambda task: (version(task), bool(task['note_problem']), bool(task['reports']),
                                                     task['state'] != 'unknown', task['file']))
        if latest_task['note_problem'] or not latest_task['reports']:
            active.append(latest_task)
            continue
        unique = {}
        for task in members:
            for report in task['reports']:
                if report['date'] and report['date'] <= today:
                    unique[(report['file'], report['delivery'])] = (task, report)
        reports = list(unique.values())
        current = [pair for pair in reports if version(pair[0]) == version(latest_task)]
        if not current:
            continue
        task, report = max(current, key=report_order)
        if report['outcome'] == 'returned':
            active.append(dict(task, state='returned', blocked=True,
                               evidence=[(report['file'], report['conclusion'])]))
            continue
        if report['date'] < today - timedelta(days=6):
            continue
        done_items.append((dict(task, state='passed', blocked=False), report))
        declared = [pair for pair in reports if pair[1]['first']]
        if len(declared) == 1 and not any(pair[1]['date'] < declared[0][1]['date'] for pair in reports):
            firsts.append(declared[0][1]['outcome'] == 'passed')
    done_items.sort(key=lambda pair: (pair[1]['date'], pair[1]['file']), reverse=True)
    ratio = round(100 * sum(firsts) / len(firsts)) if done_items and len(firsts) == len(done_items) else None
    return active, done_items, ratio


def render(project, lang=None, today=None):
    lang = project_language(project, lang)
    today = as_today(today)
    project = Path(project)
    fleet, labels = project / 'fleet', LABELS[lang]

    def clean(value):
        value = str(value)
        for path in (str(project.absolute()), str(project.absolute()).replace('\\', '/')):
            value = value.replace(path, labels['relative'])
        value = re.sub(r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\)[^\s`<>\"'|；，。)]+", labels['relative'], value)
        value = re.sub(r"(?<![\w:/<])/(?:[^/\s`<>\"'|；，。)]+/)*[^/\s`<>\"'|；，。)]+", labels['relative'], value)
        return value

    def h(value):
        return escape(clean(value), quote=True)

    def link(relative, label=None):
        return '<a href="{}">{}</a>'.format(escape(quote(relative, safe='/'), quote=True), h(relative if label is None else label))

    def preferred(index):
        for language in (lang, 'en' if lang == 'zh' else 'zh'):
            path = fleet / MAPS[language][index]
            if path.is_file():
                return path
        return fleet / MAPS[lang][index]

    def unknown(value):
        return labels['yes'] if value else labels['unknown']

    def duration(seconds):
        if seconds is None:
            return labels['unknown']
        minutes = seconds // 60
        if minutes < 60:
            return '{} {}'.format(minutes, '分钟' if lang == 'zh' else 'min')
        hours, minutes = divmod(minutes, 60)
        return '{} {} {} {}'.format(hours, '小时' if lang == 'zh' else 'h', minutes, '分钟' if lang == 'zh' else 'min')

    roster = []
    source = read(preferred(0), fleet)
    if source:
        try:
            roster = roster_rows(source, lang)
        except ValueError:
            pass
    tasks = task_records(project, lang)
    card = read(project / 'AGENTS.md', project)
    waiting, notes = waiting_partition(card, today)
    waiting_available = bool(card and re.search(r'^##\s+(?:等我定|Decisions needed)\s*$', card, re.M | re.I))
    active, done_items, ratio = task_overview(tasks, today)
    busy = {task['role'] for task in active if task['state'] in ('dispatched', 'running') and task['role']}
    out = ['<!doctype html>', '<html lang="{}"><head><meta charset="utf-8">'.format('zh-CN' if lang == 'zh' else 'en'),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
           '<title>{}</title><style>{}</style></head><body><main>'.format(h(labels['title']), CSS),
           '<header><h1>{}</h1><span class="stamp">{}</span></header>'.format(h(labels['title']), today.isoformat()),
           '<section id="waiting" class="waiting"><div class="section-head"><h2>{}</h2></div>'.format(h(labels['waiting']))]
    if waiting:
        for item in waiting:
            if item['days'] is None:
                age = labels['unknown']
            elif item['days'] == 0:
                age = labels['today']
            else:
                age = '{} {} {}'.format(labels['age'], item['days'], labels['day'] if item['days'] == 1 else labels['days'])
            date_cell = '<div class="wait-age">{}</div>'.format(h(age)) if item['has_date'] else ''
            out.append('<article class="wait-item{}">{}<div><details class="wait-question"><summary><span>{}</span></summary><p class="full-question">{}</p></details>{}</div></article>'.format(
                '' if item['has_date'] else ' undated', date_cell, h(item['text']), h(item['text']), '<p class="who">{} · {}</p>'.format(h(labels['waiting_for']), h(item['who'])) if item['who'] else ''))
    else:
        out.append('<p class="empty">{}</p>'.format(h(labels['none'] if waiting_available else labels['empty'])))
    if notes:
        out.append('<details class="waiting-notes"><summary>{}</summary><ul>{}</ul></details>'.format(
            h(labels['notes'].format(len(notes))), ''.join('<li>{}</li>'.format(h(item['raw'])) for item in notes)))
    out.append('</section><section id="active"><div class="section-head"><h2>{}</h2><span class="muted">{}</span></div>'.format(h(labels['active']), len(active)))
    for task in active:
        state = task['state']
        status = labels[state]
        if task['blocked'] and state not in ('returned', 'missing'):
            status = task['note_problem'] or labels['flagged']
        receipt = labels['no'] if task['notes_only'] else unknown(task['received'])
        review = labels['no'] if state == 'returned' or task['notes_only'] or task['note_problem'] else labels['unknown']
        out.append('<article class="work-row{}" data-task="{}" data-status="{}" data-blocked="{}"><div><p class="title">{}</p><div class="checks">{} · {} · {}</div></div>'.format(
            ' blocked' if task['blocked'] else '', h(task['file']), h(state), str(task['blocked']).lower(), h(task['title']),
            h(labels['ended'] + ': ' + unknown(task['ended'])), h(labels['receipt'] + ': ' + receipt), h(labels['review'] + ': ' + review)))
        out.append('<div class="assignment"><span>{}</span><div class="meta">{}: {}</div></div><div class="stage"><span class="badge">{}</span><div class="meta">{}: {}</div></div></article>'.format(
            h(task['role'] or labels['unidentified']), h(labels['assigned']), h(task['assigned'] or labels['unknown']), h(status), h(labels['elapsed']), h(duration(task['elapsed']))))
    if not active:
        out.append('<p class="empty">{}</p>'.format(h(labels['no_work'] if tasks else labels['empty'])))
    weekly = labels['weekly'].format(len(done_items))
    file_note = (' · ' + labels['file_time']) if any(report['fallback'] for _, report in done_items) else ''
    out.append('</section><section id="done"><div class="section-head"><h2>{}</h2><span class="weekly">{}<small class="weekly-note">{}</small></span></div>'.format(h(labels['done']), h(weekly), h(file_note)))
    if ratio is not None:
        out.append('<p class="muted">{}</p>'.format(h(labels['first'].format(ratio))))
    for task, report in done_items:
        returned = report['outcome'] == 'returned'
        out.append('<article class="done-row{}" data-task="{}" data-status="{}" data-blocked="{}"><div><p class="title">{}</p><div class="meta">{} · {}</div></div><div class="stage"><span class="badge">{}</span><div class="meta">{}</div></div><details><summary>{}</summary><div class="evidence">{}<br>{}</div></details></article>'.format(
            ' blocked' if returned else '', h(task['file']), 'returned' if returned else 'passed', str(returned).lower(), link(report['delivery'], task['title']),
            h(task['role'] or labels['unidentified']), h(task['assigned'] or labels['unknown']), h(labels['returned'] if returned else labels['passed']), h(report['date'].isoformat()), h(labels['details']), h(report['conclusion']), link(report['file'])))
    if not done_items:
        out.append('<p class="empty">{}</p>'.format(h(labels['no_done'] if tasks else labels['empty'])))
    out.append('</section><section id="people"><div class="section-head"><h2>{}</h2>'.format(h(labels['people'])))
    chart = '组织图.md' if lang == 'zh' else 'chart.md'
    if read(fleet / chart, fleet):
        out.append(link(chart, labels['chart']))
    out.append('</div>')
    if roster:
        out.append('<div class="people-grid"><article class="person human"><h3>{}</h3><p class="meta">{}</p></article>'.format(h(labels['human']), h(labels['human_role'])))
        for row in roster:
            working = row['Role'] in busy
            out.append('<article class="person" data-role="{}" data-busy="{}"><div class="person-head"><h3>{}</h3><span class="{}">{}</span></div><p class="meta" title="{}">{}</p><p class="meta">→ {}</p></article>'.format(
                h(row['Role']), str(working).lower(), h(row['Role']), 'busy' if working else 'idle', h(labels['busy'] if working else labels['idle']), h(row['Assigned']), h(re.split(r'[；;]', row['Assigned'], maxsplit=1)[0].strip()), h(row['Reports to'])))
        out.append('</div>')
    else:
        out.append('<p class="empty">{}</p>'.format(h(labels['empty'])))
    out.append('</section><footer>{}</footer></main></body></html>'.format(h(labels['note'])))
    return '\n'.join(out) + '\n'


def status_line(project, lang=None, today=None):
    language = lang if lang in MAPS else 'zh'
    try:
        project = Path(project)
        language = project_language(project, lang)
        today = as_today(today)
        card = read(project / 'AGENTS.md', project)
        tasks = task_records(project, language, with_roster=False)
        available = bool(tasks or re.search(r'^##\s+(?:等我定|Decisions needed)\s*$', card, re.M | re.I))
        if not available:
            return no_records_line(language)
        active, _, _ = task_overview(tasks, today)
        running = sum(task['state'] in ('dispatched', 'running') for task in active)
        waiting = len(waiting_records(card, today))
        if language == 'en':
            return 'Fleet: {} running · {} waiting for you'.format(running, waiting)
        return '舰队：{} 在跑 · {} 等你'.format(running, waiting)
    except BaseException:
        return no_records_line(language)


def no_records_line(language):
    return 'Fleet: no records yet' if language == 'en' else '舰队：还没有记录'


def stdin_project():
    try:
        if sys.stdin.isatty():
            return Path('.')
        payload = json.load(sys.stdin)
        workspace = payload.get('workspace') if isinstance(payload, dict) else None
        project = workspace.get('project_dir') if isinstance(workspace, dict) else None
        if isinstance(project, str) and project.strip():
            return Path(project)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return Path('.')


class StatusParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    quiet = any(arg == '--status-line' or arg.startswith('--status-line=') for arg in argv)
    language = 'en' if '--lang=en' in argv or any(argv[i:i + 2] == ['--lang', 'en'] for i in range(len(argv))) else 'zh'
    parser_type = StatusParser if quiet else argparse.ArgumentParser
    parser = parser_type(description='Generate an offline fleet board. / 生成离线舰队看板。', add_help=not quiet)
    parser.add_argument('--project', type=Path, help='Project root / 项目根目录')
    parser.add_argument('--lang', choices=('zh', 'en'), help='Page language; default: project files / 页面语言；默认按项目文件判断')
    parser.add_argument('--today', help='Window end date, YYYY-MM-DD / 七天窗口的最后日期')
    parser.add_argument('--status-line', action='store_true', help='Print one status line only / 只打印一行状态')
    if quiet:
        try:
            args = parser.parse_args(argv)
            project = args.project if args.project is not None else stdin_project()
            language = project_language(project, args.lang)
            result = status_line(project, language, args.today)
        except BaseException:
            result = no_records_line(language)
        print(result)
        return 0
    args = parser.parse_args(argv)
    project = args.project if args.project is not None else Path('.')
    language = project_language(project, args.lang)
    try:
        today = as_today(args.today)
    except (TypeError, ValueError):
        parser.error('--today requires YYYY-MM-DD')
    output = project / 'fleet' / MAPS[language][5]
    try:
        page = render(project, language, today)
        output.resolve().relative_to(project.resolve())
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(page)
    except (OSError, UnicodeError, ValueError, RuntimeError):
        print('ERROR：看板写入失败，请核对项目目录。' if language == 'zh' else
              'ERROR: Could not write board; check the project directory.', file=sys.stderr)
        return 2
    print('fleet/' + MAPS[language][5])
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
