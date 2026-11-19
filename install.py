#!/usr/bin/env python3
"""Copy the bundled skills into a project. Python 3.9+, standard library only."""
import argparse
from pathlib import Path
import sys


SKILLS = ('fleet-setup', 'fleet-chart', 'fleet-dispatch', 'fleet-taskbook',
          'fleet-rounds', 'fleet-issues', 'fleet-memory', 'fleet-precheck', 'fleet-values')
ENGLISH_PATHS = {
    '原则.md': 'principles.md', '价值观.md': 'values.md',
    '成员.md': 'members.md', '决定.md': 'decisions.md',
    '交接.md': 'handoff.md', '审批流.md': 'approvals.md',
    '岗位卡.md': 'role-card.md', '任务书.md': 'task-brief.md',
    '组织图.md': 'chart.md', '岗位卡/': 'role-cards/',
    '任务书/': 'task-briefs/', '交付/': 'deliveries/',
}


def message(lang, english, chinese):
    return chinese if lang == 'zh' else english


def english_template(payload):
    """Normalize legacy map paths when installing English template data."""
    for chinese, english in ENGLISH_PATHS.items():
        payload = payload.replace(chinese.encode('utf-8'), english.encode('utf-8'))
    return payload


def diagnostic(error, lang):
    if isinstance(error, OSError):
        path = str(error.filename or '')
        if isinstance(error, PermissionError):
            return message(lang, 'Permission denied: ', '没有文件访问权限：') + path
        if isinstance(error, FileNotFoundError):
            return message(lang, 'File not found: ', '文件不存在：') + path
        return message(lang, 'File operation failed: ', '文件操作失败：') + path
    return str(error)


def install(project, lang='en', host='all'):
    if lang not in ('en', 'zh') or host not in ('all', 'agents', 'claude'):
        raise ValueError(message(lang, 'Unsupported language or host.', '不支持的语言或宿主。'))
    source = Path(__file__).resolve().parent / 'skills'
    project = Path(project).resolve()
    hosts = ('agents', 'claude') if host == 'all' else (host,)
    planned = []
    for kind in hosts:
        root = project / ('.agents' if kind == 'agents' else '.claude') / 'skills'
        # Never follow an existing link into another project or user directory.
        for ancestor in (root.parent, root):
            if ancestor.is_symlink() or not ancestor.resolve().is_relative_to(project):
                raise ValueError(message(lang, 'Refusing linked install directory: ', '拒绝链接安装目录：') + str(ancestor))
        for name in SKILLS:
            folder = source / name
            entry = folder / ('SKILL.zh.md' if lang == 'zh' else 'SKILL.md')
            if not entry.is_file():
                raise ValueError(message(lang, 'Missing language entry: ', '缺少语言入口：') + str(entry))
            destination = root / name
            if destination.is_symlink():
                raise ValueError(message(lang, 'Refusing linked skill directory: ', '拒绝链接技能目录：') + str(destination))
            for path in sorted(folder.rglob('*')):
                if '__pycache__' in path.parts or path.suffix == '.pyc':
                    continue
                relative = path.relative_to(folder)
                # An English install must not bundle Chinese-named assets.
                # Chinese installs keep both sets for their existing entrypoints.
                if lang == 'en' and (relative.parts[:2] == ('templates', 'zh')
                                     or relative.as_posix() == 'SKILL.zh.md'):
                    continue
                if path.is_symlink():
                    raise ValueError(message(lang, 'Refusing linked source: ', '拒绝链接源文件：') + str(path))
                if not path.is_file():
                    continue
                target = destination / relative
                payload = entry.read_bytes() if relative.as_posix() == 'SKILL.md' else path.read_bytes()
                if lang == 'en' and relative.parts[:2] == ('templates', 'en') and path.suffix == '.md':
                    payload = english_template(payload)
                for ancestor in target.parents:
                    if ancestor == project:
                        break
                    if (ancestor.is_symlink() or not ancestor.resolve().is_relative_to(project)
                            or (ancestor.exists() and not ancestor.is_dir())):
                        raise ValueError(message(lang, 'Unsafe destination parent: ', '目标父目录不安全：') + str(ancestor))
                if target.is_symlink() or (target.exists() and (not target.is_file() or target.read_bytes() != payload)):
                    raise ValueError(message(lang, 'Existing file differs; preserve or move it before reinstalling: ', '已有文件内容不同；请保留或移动后再安装：') + str(target))
                planned.append((target, payload))
    # Complete preflight before writing: collisions never overwrite reader files.
    written = 0
    for target, payload in planned:
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(payload)
            written += 1
    return len(SKILLS) * len(hosts), written


def main():
    parser = argparse.ArgumentParser(description=__doc__ + ' / 将技能复制到项目；仅需 Python 标准库。')
    parser.add_argument('--lang', choices=('zh', 'en'), default='en', help='skill and diagnostic language / 技能及诊断语言')
    parser.add_argument('--host', choices=('all', 'claude', 'agents'), default='all', help='skill discovery location / 技能发现目录')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='destination project (default: current directory) / 目标项目（默认当前目录）')
    args = parser.parse_args()
    try:
        count, written = install(args.project, args.lang, args.host)
    except (OSError, ValueError) as error:
        print(message(args.lang, 'Install stopped: ', '安装停止：') + diagnostic(error, args.lang), file=sys.stderr)
        return 1
    print(message(args.lang, 'Installed {0} skill entries ({1} new files); language={2}; host={3}.',
                  '已安装 {0} 个技能入口（新增 {1} 个文件）；语言={2}；宿主={3}。').format(count, written, args.lang, args.host))
    print(message(args.lang, 'Start a new host session in your project to discover the skills.',
                  '请在项目里新开宿主会话，以发现这些技能。'))
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
