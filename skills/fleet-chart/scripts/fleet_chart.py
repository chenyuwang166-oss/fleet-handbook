#!/usr/bin/env python3
"""Read a Chinese or English Markdown roster and render a Mermaid chart."""
import argparse
from pathlib import Path
import re
import sys

ZH = ('岗位', '部门', '汇报给', '派驻', '怎么调用', '做什么', '交付写进')
EN = ('Role', 'Department', 'Reports to', 'Assigned', 'How to call', 'Does', 'Delivers to')


def cells(line):
    r"""A literal pipe in a cell must be written as \|."""
    line = line.strip().strip('|')
    return [c.strip().replace(r'\|', '|') for c in re.split(r'(?<!\\)\|', line)]


def project_language(source):
    """Check only the two documented roster paths, without listing directories."""
    if source is None:
        return None
    try:
        # Lexical parents are sufficient; do not resolve links during detection.
        directories = Path(source).absolute().parents
        for directory in directories:
            en = (directory / 'fleet' / 'members.md').is_file()
            zh = (directory / 'fleet' / '成员.md').is_file()
            if en or zh:
                # A bilingual project is ambiguous: fall back to the input.
                return ('en' if en else 'zh') if en != zh else None
    except (OSError, RuntimeError, ValueError):
        # Detection is best effort; the actual file read reports any failure.
        return None
    return None


def detect_language(text, source=None):
    rows = [cells(line) for line in text.splitlines() if line.strip().startswith('|')]
    # Match the same first primary header as the parser, before scoring partials.
    for row in rows:
        if '岗位' in row:
            return 'zh'
        if 'Role' in row:
            return 'en'
    # Partial headers still identify the language when the Role column is absent.
    scores = [(sum(field in row for field in ZH), sum(field in row for field in EN))
              for row in rows]
    if scores:
        zh, en = max(scores, key=lambda pair: max(pair))
        if zh != en:
            return 'zh' if zh > en else 'en'
    language = project_language(source)
    if language:
        return language
    if source is not None and re.search(r'[\u3400-\u9fff]', Path(source).name):
        return 'zh'
    # Without a source path, preserve the language of malformed Chinese input.
    return 'zh' if re.search(r'[\u3400-\u9fff]', text) else 'en'


def _read_roster(text, lang='auto', source=None):
    language = detect_language(text, source) if lang == 'auto' else lang
    if language not in ('en', 'zh'):
        raise ValueError('lang must be auto, en or zh')

    def fail(zh, en):
        raise ValueError(zh if language == 'zh' else en)

    lines = text.splitlines()
    header = None
    for i, line in enumerate(lines):
        if not line.strip().startswith('|'):
            continue
        row = cells(line)
        if '岗位' in row or 'Role' in row:
            header = row
            fields = ZH if '岗位' in row else EN
            break
    if header is None:
        fail('找不到成员表；请使用中文或英文的规定表头。',
             'Roster table not found; use the required Chinese or English column headings.')
    missing = [f for f in fields if f not in header]
    if missing:
        fail('成员表缺列：' + '、'.join(missing),
             'Roster table is missing columns: ' + ', '.join(missing))
    if len(set(header)) != len(header):
        fail('成员表的列名重复。', 'Roster table has duplicate column headings.')
    if i + 1 >= len(lines) or not all(re.fullmatch(r':?-{3,}:?', c) for c in cells(lines[i + 1])):
        fail('表头后需要 Markdown 分隔行。', 'The header must be followed by a Markdown separator row.')
    if len(cells(lines[i + 1])) != len(header):
        fail('表头和分隔行的列数不同。', 'The header and separator row have different column counts.')
    result = []
    for number, line in enumerate(lines[i + 2:], i + 3):
        if not line.strip().startswith('|'):
            break
        row = cells(line)
        if len(row) != len(header):
            fail('第 {} 行列数不对；单元格内的竖线请加反斜杠。'.format(number),
                 'Line {} has the wrong column count; escape pipes inside cells with a backslash.'.format(number))
        item = dict(zip(fields, (row[header.index(f)] for f in fields)))
        result.append(dict(zip(EN, (item[f] for f in fields))))
    if not result:
        fail('成员表没有岗位。', 'Roster table has no roles.')
    names = set()
    for row in result:
        name = row['Role']
        if not name or not row['Reports to']:
            fail('岗位和汇报给不能为空。', 'Role and Reports to must not be empty.')
        if name in ('人', 'Human'):
            fail('人是保留的组织成员，岗位请使用其他名称。',
                 'Human is a reserved organization member; use another role name.')
        if name in names:
            fail('岗位重名：' + name, 'Duplicate role name: ' + name)
        names.add(name)
    for row in result:
        target = row['Reports to']
        if target not in names and target not in ('人', 'Human'):
            fail('汇报对象不存在：' + target, 'Reporting target does not exist: ' + target)
    parent = {row['Role']: row['Reports to'] for row in result}
    # Iterative traversal also handles a deep, valid hierarchy.
    done = set()
    for name in parent:
        chain = set()
        current = name
        while current in parent and current not in done:
            if current in chain:
                fail('汇报关系成环：' + current, 'Reporting relationships contain a cycle: ' + current)
            chain.add(current)
            current = parent[current]
        done.update(chain)
    return result, language


def read_roster(text, lang='auto', source=None):
    return _read_roster(text, lang, source)[0]


def escape_label(value):
    # Mermaid decimal entities keep user content from becoming diagram syntax.
    special = set('&"<>[]{}()|`\\#;')
    return ''.join('#{};'.format(ord(c)) if c in special else c for c in value)


def render(text, lang='auto', source=None):
    rows, language = _read_roster(text, lang, source)
    title, human = ('AI 舰队', '人') if language == 'zh' else ('AI Fleet', 'Human')
    ids = {row['Role']: 'r{}'.format(i) for i, row in enumerate(rows, 1)}
    out = ['```mermaid', 'flowchart LR', '  subgraph fleet["{}"]'.format(title),
           '    human["{}"]'.format(human)]
    for row in rows:
        label = '<br/>'.join(escape_label(row[f]) for f in ('Role', 'Department', 'Assigned') if row[f])
        out.append('    {}["{}"]'.format(ids[row['Role']], label))
    for row in rows:
        parent = 'human' if row['Reports to'] in ('人', 'Human') else ids[row['Reports to']]
        out.append('    {} --> {}'.format(parent, ids[row['Role']]))
    out += ['  end', '```', '']
    return '\n'.join(out)


def file_error(exc, language):
    path = str(getattr(exc, 'filename', None) or '')
    if isinstance(exc, UnicodeError):
        return '文件不是有效的 UTF-8 文本。' if language == 'zh' else 'File is not valid UTF-8 text.'
    if isinstance(exc, OSError):
        if isinstance(exc, FileNotFoundError):
            return ('文件不存在：' if language == 'zh' else 'File not found: ') + path
        if isinstance(exc, PermissionError):
            return ('没有文件访问权限：' if language == 'zh' else 'Permission denied: ') + path
        return ('文件操作失败：' if language == 'zh' else 'File operation failed: ') + path
    return str(exc)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Render a Mermaid organization chart from a roster. / 从成员名册生成 Mermaid 组织图。')
    parser.add_argument('roster', type=Path, help='Markdown roster / Markdown 成员名册')
    parser.add_argument('-o', '--output', type=Path,
                        help='Write to this file; default: stdout / 输出文件；省略时写到标准输出')
    parser.add_argument('--lang', choices=('auto', 'en', 'zh'), default='auto',
                        help='Output language; auto: header, project roster, input name / 输出语言；auto 按表头、项目名册、输入名判断')
    args = parser.parse_args(argv)
    language = args.lang if args.lang != 'auto' else (
        'zh' if re.search(r'[\u3400-\u9fff]', args.roster.name) else 'en')
    try:
        if args.lang == 'auto':
            language = detect_language('', args.roster)
        text = args.roster.read_text(encoding='utf-8-sig')
        language = detect_language(text, args.roster) if args.lang == 'auto' else args.lang
        chart = render(text, language, args.roster)
        if args.output:
            with args.output.open('w', encoding='utf-8', newline='\n') as stream:
                stream.write(chart)
        else:
            sys.stdout.write(chart)
    except (OSError, UnicodeError, ValueError) as exc:
        print(('ERROR：' if language == 'zh' else 'ERROR: ') + file_error(exc, language), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
