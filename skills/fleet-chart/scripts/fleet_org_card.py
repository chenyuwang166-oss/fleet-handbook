#!/usr/bin/env python3
"""Render a roster as an offline SVG organization card with PNG export."""
import argparse
import importlib.util
from pathlib import Path
import sys
import re


def _module(name):
    spec = importlib.util.spec_from_file_location('_org_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


board = _module('fleet_board')
card = _module('fleet_card')
OUTPUT = {'zh': '组织图.html', 'en': 'chart.html'}


def render(project, lang=None, today=None):
    project = Path(project)
    language = board.project_language(project, lang)
    today = board.as_today(today)
    zh = language == 'zh'
    title = '舰队组织图' if zh else 'Fleet organization chart'
    human = '人' if zh else 'Human'
    fleet = project / 'fleet'
    source, roster_path = '', fleet / board.MAPS[language][0]
    for candidate_language in (language, 'en' if zh else 'zh'):
        candidate = fleet / board.MAPS[candidate_language][0]
        if candidate.is_file():
            source = board.read(candidate, fleet)
            if not source:
                continue
            roster_path = candidate
            break
    def clean(value):
        value = str(value)
        hidden = '[路径已隐藏]' if zh else '[path hidden]'
        for path in (str(project.absolute()), str(project.absolute()).replace('\\', '/')):
            value = value.replace(path, hidden)
        value = re.sub(r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\)[^\s`<>\"'|；，。)]+", hidden, value)
        return re.sub(r"(?<![\w:/<])/(?:[^/\s`<>\"'|；，。)]+/)*[^/\s`<>\"'|；，。)]+", hidden, value)

    rows = []
    if source:
        try:
            rows = board.roster_rows(source, language)
        except ValueError:
            pass

    # A vertical tree keeps sibling labels readable on a phone. Large/deep
    # rosters grow downward; depth indent is capped and every role names its
    # parent explicitly, so even very deep hierarchies retain their meaning.
    children = {human: []}
    for row in rows:
        parent = human if row['Reports to'] in ('人', 'Human') else row['Reports to']
        children.setdefault(parent, []).append(row)
    ordered = []
    pending = [(row, 1) for row in reversed(children[human])]
    while pending:
        row, depth = pending.pop()
        ordered.append((row, depth))
        pending.extend((child, depth + 1) for child in reversed(children.get(row['Role'], [])))

    project_lines = card.text_lines(project.name or '.', 920, 34)
    project_y = 148
    y = project_y + len(project_lines) * 48 + 64
    nodes = [(human, 64, y, 122, None, [('定目标、做决定' if zh else 'Sets goals and makes decisions', 24, '#686a72')])]
    y += 154
    for row, depth in ordered:
        x = 64 + min(depth, 5) * 36
        inner_width = 1080 - x - 112
        lines = []
        for value, size, color in ((row['Role'], 30, '#3b2673'),
                                   (('部门：' if zh else 'Department: ') + row['Department'], 23, '#686a72'),
                                   (('派驻：' if zh else 'Assigned: ') + row['Assigned'], 23, '#686a72'),
                                   (('汇报给：' if zh else 'Reports to: ') + row['Reports to'], 21, '#686a72')):
            for line in card.text_lines(clean(value), inner_width, size):
                lines.append((line, size, color))
        height = 36 + sum(size * 1.4 for _, size, _ in lines)
        parent = human if row['Reports to'] in ('人', 'Human') else row['Reports to']
        nodes.append((row['Role'], x, y, height, parent, lines))
        y += height + 30
    if not rows:
        y += 164
    height = int(y + 106)
    out = ['<svg id="fleet-card" xmlns="http://www.w3.org/2000/svg" width="1080" height="{}" viewBox="0 0 1080 {}" role="img" aria-labelledby="card-title" font-family="Inter, Noto Sans, Segoe UI, Noto Sans SC, Source Han Sans SC, Microsoft YaHei, sans-serif">'.format(height, height),
           '<title id="card-title">{}</title>'.format(card._xml(title)),
           '<rect width="1080" height="{}" fill="#f7f8fa"/>'.format(height),
           '<rect x="64" y="54" width="48" height="6" rx="3" fill="#8a4ed1"/>',
           card.svg_text(title, 64, 105, 28, '#3b2673', 700),
           card.wrapped_text(project.name or '.', 64, project_y + 24, 920, 34, 48, weight=700),
           card.svg_text(today.isoformat(), 64, project_y + len(project_lines) * 48 + 28, 22, '#686a72')]
    positions = {name: (x, top, node_height) for name, x, top, node_height, _, _ in nodes}
    for _, x, top, node_height, parent, _ in nodes[1:]:
        px, py, ph = positions[parent]
        rail = min(px, x) - 18
        out.append('<path d="M {} {} H {} V {} H {}" fill="none" stroke="#b7a3d8" stroke-width="3"/>'.format(px, py + ph / 2, rail, top + node_height / 2, x))
    for index, (name, x, top, node_height, _, lines) in enumerate(nodes):
        out.append('<g data-role="{}">'.format(card._xml(clean(name))))
        out.append('<rect x="{}" y="{}" width="{}" height="{}" rx="18" fill="{}" stroke="#dcd5e9" stroke-width="2"/>'.format(x, top, 1016 - x, node_height, '#e9e6ff' if index == 0 else '#ffffff'))
        text_y = top + 44
        if index == 0:
            out.append(card.svg_text(human, x + 24, text_y, 30, weight=700))
            text_y += 38
        for line, size, color in lines:
            out.append(card.svg_text(line, x + 24, text_y, size, color, 700 if size == 30 else 400))
            text_y += size * 1.4
        out.append('</g>')
    if not rows:
        empty = ('还没有可读取的成员名册。补好 ' if zh else 'No readable roster yet. Add ') + 'fleet/' + roster_path.name
        out.append(card.wrapped_text(empty, 64, y - 108, 920, 27, 38, '#686a72'))
    footer = '来自 fleet/' + roster_path.name if zh else 'From fleet/' + roster_path.name
    out += [card.svg_text(footer, 64, height - 58, 21, '#686a72'), '</svg>']
    return card.document('\n'.join(out), language, title, 'fleet-chart-{}-{}.png'.format(language, today.isoformat()))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate an offline organization card. / 生成离线组织图卡片。')
    parser.add_argument('--project', type=Path, default=Path('.'), help='Project root / 项目根目录')
    parser.add_argument('--lang', choices=('zh', 'en'), help='Page language; default: project files / 页面语言；默认按项目文件判断')
    parser.add_argument('--today', help='Card date, YYYY-MM-DD / 卡片日期')
    args = parser.parse_args(argv)
    language = board.project_language(args.project, args.lang)
    try:
        today = board.as_today(args.today)
    except (TypeError, ValueError):
        parser.error('--today requires YYYY-MM-DD')
    output = args.project / 'fleet' / OUTPUT[language]
    try:
        page = render(args.project, language, today)
        output.resolve().relative_to(args.project.resolve())
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(page)
    except (OSError, UnicodeError, ValueError, RuntimeError):
        print('ERROR：组织图写入失败，请核对项目目录。' if language == 'zh' else
              'ERROR: Could not write organization card; check the project directory.', file=sys.stderr)
        return 2
    print('fleet/' + OUTPUT[language])
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
