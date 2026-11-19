#!/usr/bin/env python3
"""Check explicit UTF-8 text files against a user-maintained TSV rule list."""
import argparse
from pathlib import Path
import re
import sys


def detect_language(paths):
    """Inspect documented project roster names, then the explicit input names."""
    paths = [Path(path) for path in paths]
    for path in paths:
        try:
            # Detect from lexical parents without following links.
            for directory in path.absolute().parents:
                en = (directory / 'fleet' / 'members.md').is_file()
                zh = (directory / 'fleet' / '成员.md').is_file()
                if en or zh:
                    if en != zh:
                        return 'en' if en else 'zh'
                    # Both roster names make this input's project ambiguous.
                    break
        except (OSError, RuntimeError, ValueError):
            # The actual read, rather than optional detection, reports failures.
            continue
    return 'zh' if any(re.search(r'[\u3400-\u9fff]', path.name) for path in paths) else 'en'


def load_rules(text, lang='zh'):
    """Parse rules; the default keeps the original Chinese Python API diagnostics."""
    if lang not in ('en', 'zh'):
        raise ValueError('lang must be en or zh')

    def fail(zh, en):
        raise ValueError(zh if lang == 'zh' else en)

    rules = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split('\t', 2)
        if len(parts) != 3:
            fail('词表第 {} 行需要三列，用制表符分隔。'.format(number),
                 'Rule list line {} must contain three tab-separated columns.'.format(number))
        level, pattern, description = (v.strip() for v in parts)
        if level not in ('ERROR', 'WARN') or not pattern or not description:
            fail('词表第 {} 行的级别、正则或说明不正确。'.format(number),
                 'Rule list line {} has an invalid severity, pattern or description.'.format(number))
        try:
            compiled = re.compile(pattern)
        except re.error:
            fail('词表第 {} 行的正则无效。'.format(number),
                 'Rule list line {} has an invalid regular expression.'.format(number))
        if compiled.search(''):
            fail('词表第 {} 行的正则会匹配空文本，请收紧。'.format(number),
                 'Rule list line {} matches empty text; make its pattern more specific.'.format(number))
        rules.append((level, compiled, description))
    if not rules:
        fail('词表没有有效规则。', 'Rule list contains no valid rules.')
    return rules


def check_text(text, rules):
    """Yield (severity, original line number, explanation); fenced examples are skipped."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        if fence:
            close = r' {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*'
            if re.fullmatch(close, line):
                fence = None
            continue
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if opening and (opening[1][0] != '`' or '`' not in opening[2]):
            fence = (opening[1][0], len(opening[1]))
            continue
        for level, pattern, description in rules:
            if pattern.search(line):
                yield level, number, description


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
        description='Check explicit files line by line with your own rule list; no directory scan. / 用自有词表逐行检查发前文字；不扫描文件夹。')
    parser.add_argument('--terms', type=Path, required=True, help='TSV rule list / 制表符分隔的词表')
    parser.add_argument('--lang', choices=('auto', 'en', 'zh'), default='auto',
                        help='Diagnostic language; auto: project roster, input names / 诊断语言；auto 按项目名册、输入名判断')
    parser.add_argument('files', nargs='+', type=Path, help='UTF-8 files to check / 要检查的 UTF-8 文件')
    args = parser.parse_args(argv)
    paths = [*args.files, args.terms]
    language = args.lang if args.lang != 'auto' else (
        'zh' if any(re.search(r'[\u3400-\u9fff]', path.name) for path in paths) else 'en')
    try:
        if args.lang == 'auto':
            language = detect_language(paths)
        rules = load_rules(args.terms.read_text(encoding='utf-8-sig'), language)
        # Read every input before announcing a result; a missing file is a failed check.
        inputs = [(p, p.read_text(encoding='utf-8-sig')) for p in args.files]
        errors = warnings = 0
        for path, text in inputs:
            for level, number, description in check_text(text, rules):
                print('{} {}:{} {}'.format(level, path, number, description))
                errors += level == 'ERROR'
                warnings += level == 'WARN'
        summary = ('检查完成：ERROR {}，WARN {}。' if language == 'zh'
                   else 'Check complete: ERROR {}, WARN {}.')
        print(summary.format(errors, warnings))
        return 1 if errors else 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(('ERROR：' if language == 'zh' else 'ERROR: ') + file_error(exc, language), file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
