"""Build local HTML artwork and render it without network access.

Usage: python assets/src/build_assets.py [--render] [--charts-only]
The first-day chart is a public adaptation of the provided source chart.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SRC = Path(__file__).resolve().parent
ASSETS = SRC.parent
WIDTH = 1424
VI_PATH = SRC / 'metask-vi.css'
# Colors and fonts from the MeTask website stylesheet, kept next to this script so the
# artwork rebuilds offline. Comments are dropped when it is embedded in the HTML.
def load_vi() -> str:
    if VI_PATH.is_file():
        css = VI_PATH.read_text(encoding='utf-8')
    else:
        chart = (SRC / 'chart-zh.html').read_text(encoding='utf-8')
        css = re.search(r'<style id="metask-vi">(.*?)</style>', chart, re.S).group(1)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return '\n'.join(line.rstrip() for line in css.splitlines() if line.strip()) + '\n'

VI_CSS = load_vi()
# Unmodified official asset: https://www.metask-ai.com/media/metask-logo.svg
# SHA256 84d23bd5bb130cea2f116843116840d8dd1675ec8a48c930968a5c52165aed1d
LOGO_DATA = 'data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBHZW5lcmF0b3I6IEFkb2JlIElsbHVzdHJhdG9yIDI4LjEuMCwgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246IDYuMDAgQnVpbGQgMCkgIC0tPgo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IuWbvuWxgl8xIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB4PSIwcHgiIHk9IjBweCIKCSB2aWV3Qm94PSIwIDAgODAwIDgwMCIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5ldyAwIDAgODAwIDgwMDsiIHhtbDpzcGFjZT0icHJlc2VydmUiPgo8c3R5bGUgdHlwZT0idGV4dC9jc3MiPgoJLnN0MHtmaWxsOiM3MDNGQTg7c3Ryb2tlOiM3MDNGQTg7c3Ryb2tlLXdpZHRoOjMxLjE4MTE7c3Ryb2tlLW1pdGVybGltaXQ6MTA7fQo8L3N0eWxlPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNMzk5LjU1LDQzMC44MmMtMS43NCwzLjgxLTMuMTYsNy4wOC00LjcsMTAuMjljLTcuMTEsMTQuOS0xMy44OCwyOS45Ny0yMS40NSw0NC42MgoJYy0xMi4yOSwyMy43Ny0yNC43OCw0Ny40Ny0zNy44Myw3MC44M2MtMTIuODksMjMuMDYtMjYuODksNDUuNDktNDIuMSw2Ny4xMmMtOS41NCwxMy41Ny0xOS40MiwyNi45MS0zMC40OCwzOS4zCgljLTEwLjUzLDExLjgtMjEuNTIsMjMuMTQtMzQuMzcsMzIuNTFjLTEwLjgzLDcuOS0yMi4zOSwxNC4yNi0zNS41MSwxNy40NWMtMTQuODEsMy42LTI5LjE3LDIuMzEtNDMuMjItMy42MQoJYy0xOC4xMy03LjY0LTMyLjYtMTkuOTEtNDQuOTItMzQuOTdjLTExLjk3LTE0LjYzLTIxLjUxLTMwLjc2LTI5LjgtNDcuN2MtNy45OS0xNi4zNC0xNC42OC0zMy4yLTIwLjA3LTUwLjUzCgljLTQuMDctMTMuMDctNy42My0yNi4zMi0xMC43Ni0zOS42NWMtMy4wNS0xMi45OS01LjY1LTI2LjEyLTcuNzQtMzkuMjljLTMuMDgtMTkuMzYtNS4xMy0zOC44Ni02LjM3LTU4LjQ1CgljLTEuNi0yNS4xNC0xLjYtNTAuMjctMC4yNS03NS40YzEuMTUtMjEuMzEsMy4xMy00Mi41Niw2LjUyLTYzLjY0YzMuNzgtMjMuNDgsOC45NS00Ni42NiwxNS45OS02OS4zOQoJYzcuMjgtMjMuNDksMTYuMTYtNDYuMzEsMjcuNjktNjguMDdjMTAuMjYtMTkuMzYsMjIuNjUtMzcuMTEsMzguOTMtNTEuOTRjMTMuMzctMTIuMTcsMjguNDYtMjEuMTYsNDYuNTUtMjQuMgoJYzE0LjI1LTIuNCwyNy45Ny0wLjQ5LDQxLjI4LDUuMjVjMTQuMjYsNi4xNCwyNi40NSwxNS4yMSwzNy43OCwyNS42YzIwLjUsMTguODIsMzcuMjgsNDAuNzQsNTIuOTMsNjMuNgoJYzE0LjA4LDIwLjU2LDI2Ljk1LDQxLjg4LDM5LjAyLDYzLjY3YzEwLjEyLDE4LjI2LDIwLjAyLDM2LjY0LDI5LjY0LDU1LjE2YzUuNjIsMTAuODEsMTAuNjIsMjEuOTYsMTUuNzIsMzMuMDQKCWM1LjcsMTIuMzgsMTEuMiwyNC44NSwxNi43OCwzNy4yOGMwLjI1LDAuNTYsMC41NSwxLjEsMS4wNCwyLjA5YzAuNTQtMC45NCwwLjkyLTEuNSwxLjItMi4xYzUuMDgtMTEuMDksOS44Ny0yMi4zMiwxNS4yNy0zMy4yNgoJYzEyLjU5LTI1LjQ3LDI0Ljk2LTUxLjA2LDM4LjM4LTc2LjA4YzExLjA5LTIwLjY2LDIzLjM2LTQwLjcsMzUuNDgtNjAuNzljMTAuNS0xNy40LDIyLjE5LTM0LjAzLDM0LjktNDkuOTEKCWMxMS45Ni0xNC45NSwyNC45Mi0yOC45NywzOS45OC00MC44N2MxMC4yOS04LjEzLDIxLjM2LTE1LjA4LDMzLjg3LTE5LjM3YzIwLjYzLTcuMDgsNDAuNjYtNS43Myw2MC4wMiw0LjQ5CgljMTUuOTEsOC40MSwyOC42NywyMC40OSwzOS44MiwzNC4zOWMxMy42MywxNi45OSwyMy45LDM2LjAxLDMyLjMyLDU1Ljk1YzUuOTYsMTQuMTIsMTAuOTYsMjguNjcsMTUuOTMsNDMuMTgKCWM1Ljg1LDE3LjA3LDkuNzUsMzQuNjgsMTMuMTUsNTIuMzhjMy44OCwyMC4xOCw2LjY3LDQwLjUzLDguMzUsNjEuMDJjMS44OSwyMy4xNSwyLjg0LDQ2LjMzLDIuMzcsNjkuNTUKCWMtMC40NywyMy4wNy0yLjAyLDQ2LjA2LTUuMDcsNjguOTVjLTMuNTEsMjYuMzctOC43Miw1Mi4zOS0xNS42OSw3OC4wNmMtNy43OCwyOC42My0xOC4wNyw1Ni4zMS0zMi4xMyw4Mi40OAoJYy05LjIsMTcuMTMtMTkuODYsMzMuMzItMzMuODYsNDcuMDJjLTExLjk1LDExLjctMjUuMjksMjEuMjgtNDEuNzEsMjUuN2MtMTguMTksNC45LTM1LjU3LDIuMTctNTIuMzMtNS45MQoJYy0xNS45NC03LjY4LTI5LjMtMTguODEtNDEuNzgtMzEuMTNjLTE5LjI2LTE5LjAxLTM1LjI5LTQwLjYtNTAuMjctNjMuMDJjLTEzLjU2LTIwLjI5LTI2LjQtNDEuMDMtMzcuODQtNjIuNTgKCWMtMTMuODgtMjYuMTYtMjcuNS01Mi40Ni00MC45Ny03OC44M2MtNi40Ni0xMi42NC0xMi4zMS0yNS41OS0xOC40NC0zOC4zOUM0MDAuNTYsNDMyLjI0LDQwMC4yMSw0MzEuODIsMzk5LjU1LDQzMC44MnoKCSBNNzUyLjE5LDM5My40NmMwLTUuNzUsMC4yNC0xMS41LTAuMDUtMTcuMjRjLTAuNTktMTEuNzYtMS4wNy0yMy41NS0yLjMxLTM1LjI1Yy0xLjk1LTE4LjM1LTQuMzctMzYuNjctOC41NC01NC42NgoJYy0zLTEyLjk4LTYuMTYtMjUuOTctMTAuMjQtMzguNjNjLTQuMTktMTMuMDEtOS4xNC0yNS44MS0xNC41My0zOC4zOGMtNy4wOC0xNi41Mi0xNS45OC0zMi4wNy0yNy4zMy00Ni4xMwoJYy05LjA5LTExLjI2LTE5LjIxLTIxLjMtMzEuODctMjguNThjLTE3LjIzLTkuOTItMzUuMi0xMi4wMi01NC4wOS01LjUzYy0xNC4wMSw0LjgxLTI1LjU1LDEzLjUyLTM2LjQ5LDIzLjE1CgljLTE2LjQzLDE0LjQ3LTI5Ljk3LDMxLjUxLTQyLjg5LDQ5LjA1Yy0xNC4zMSwxOS40NC0yNy4xOSwzOS44MS0zOS4zNiw2MC42NmMtMTcuNDUsMjkuOS0zMy4yMiw2MC42Ny00OC40MSw5MS43NQoJYy03LjQ3LDE1LjI4LTE0LjY5LDMwLjY4LTIxLjkzLDQ2LjA4Yy0wLjQ3LDEtMC40OCwyLjYxLTAuMDEsMy42MWM2LjI0LDEzLjI0LDEyLjUyLDI2LjQ3LDE4Ljk3LDM5LjYxCgljMTIuODQsMjYuMTUsMjYuNTQsNTEuODQsNDAuOTUsNzcuMTZjMTMuNDcsMjMuNjYsMjguMDUsNDYuNiw0My41OCw2OC45NWMxMS43MywxNi44OSwyNC4zNCwzMy4wNywzOC42Myw0Ny44OAoJYzEwLjY2LDExLjA0LDIyLjExLDIxLjE1LDM1LjY4LDI4LjU3YzIyLjUzLDEyLjMxLDQ0Ljk2LDEyLjM3LDY3LjE1LTAuODhjMTQuMDctOC40LDI0Ljk5LTIwLjE2LDM0LjMxLTMzLjQyCgljMTUuMTItMjEuNSwyNS40OS00NS4zNiwzNC4wMS03MC4wOGMxMC40LTMwLjE4LDE2Ljk5LTYxLjIyLDIwLjkyLTkyLjg2Qzc1MS40Myw0NDMuNDQsNzUyLjc0LDQxOC40OSw3NTIuMTksMzkzLjQ2eiBNNDcuOTQsNDExLjM4CgljMC43MywxMy40OCwwLjkyLDI3LjAyLDIuMzEsNDAuNDRjMS43NCwxNi43Niw0LjA5LDMzLjQ5LDYuODcsNTAuMTJjMy4yMSwxOS4yLDguMTYsMzguMDIsMTQuNDYsNTYuNDYKCWM2LjksMjAuMjEsMTUuMDMsMzkuODcsMjYuMTYsNTguMThjOC4wNSwxMy4yNCwxNi45OSwyNS43NSwyOC41NiwzNi4yM2M5LjExLDguMjUsMTkuMjYsMTQuNzUsMzAuOTYsMTguNTkKCWMxNy45NCw1Ljg5LDM1LjA1LDMuMzIsNTEuMjktNS43OWMxMi44Mi03LjE5LDIzLjc2LTE2LjgxLDM0LTI3LjI1YzE1Ljc1LTE2LjA1LDI5LjA1LTM0LjEsNDEuODItNTIuNDkKCWMxNC44Ni0yMS40LDI4Ljc3LTQzLjQ1LDQxLjYzLTY2LjEyYzkuMDYtMTUuOTgsMTguMjEtMzEuOTMsMjYuNTItNDguM2MxMS40Mi0yMi41MiwyMi4wNi00NS40NCwzMy4wNy02OC4xNwoJYzAuODEtMS42OCwwLjgyLTMuMTIsMC00Ljg1Yy03LjcxLTE2LjE5LTE1LjA3LTMyLjU1LTIzLjA1LTQ4LjZjLTEwLjI5LTIwLjY2LTIwLjg1LTQxLjItMzEuNjgtNjEuNTgKCWMtMTIuMTYtMjIuODgtMjUuNjItNDQuOTktNDAuMTQtNjYuNDZjLTEzLjUzLTIwLTI3Ljc4LTM5LjQyLTQ0LjM4LTU3LjAxYy0xMS4xOS0xMS44Ny0yMy4zOS0yMi40OC0zNy43OC0zMC4zNgoJYy05LjA0LTQuOTUtMTguNTctOC4yNC0yOS04Ljc5Yy0xNS4zMS0wLjgtMjguNzgsNC4wOC00MS4yMywxMi41OWMtMTEuODgsOC4xMy0yMS43MSwxOC4zLTMwLjI4LDI5Ljc2CglDOTUuMjEsMTg1LjEzLDg1LjYsMjA0LDc3LjkxLDIyMy45MWMtOC44MSwyMi44MS0xNS40NCw0Ni4yNC0yMC4xMiw3MC4yNGMtMy41OCwxOC4zNC02LjE1LDM2LjgxLTcuNzEsNTUuNDIKCUM0OC4zNiwzNzAuMTMsNDcuNzUsMzkwLjczLDQ3Ljk0LDQxMS4zOHoiLz4KPC9zdmc+Cg=='

CSS = """
*{box-sizing:border-box}html,body{margin:0;background:var(--panel)}
body{font-family:var(--font-zh);color:var(--text)}
.en{font-family:var(--font-en),var(--font-zh)}
.canvas{position:relative;width:1424px;padding:48px 52px 90px;background:var(--canvas);overflow:hidden}
.eyebrow{font-size:22px;color:var(--muted);font-weight:600;letter-spacing:.04em}
.logo{position:absolute;right:52px;top:44px;width:34px;height:34px}
h1{font-size:52px;line-height:1.25;margin:18px 0 14px;letter-spacing:-.03em;color:var(--brand-deep)}
.intro{font-size:25px;line-height:1.55;margin:0;color:var(--text-2);max-width:1260px}
.rule{height:3px;background:var(--brand-primary);margin:28px 0 30px;width:86px}
.grid{display:grid;gap:24px}.three{grid-template-columns:repeat(3,1fr)}
.card{border:1.5px solid var(--line-strong);border-radius:14px;padding:26px;background:var(--panel)}
.card h2{font-size:30px;margin:10px 0 18px;line-height:1.3}
.card p,.card li{font-size:24px;line-height:1.65;margin:0}
.card ul{padding-left:24px;margin:0}.num{font-family:var(--font-mono);font-size:24px;color:var(--muted);font-weight:700}
.small{font-size:21px;line-height:1.6;color:var(--text-2)}
.teal{background:var(--brand-soft);border-color:var(--brand-primary)}.teal .num,.teal h2{color:var(--brand-deep)}
.human{background:var(--panel-3);border-color:var(--line-strong)}
.ribbon{background:var(--panel-3);border-radius:12px;padding:22px 28px;font-size:27px;line-height:1.55;margin-top:28px}
.ribbon b{color:var(--brand-deep)}.states{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:30px}
.state{border-top:3px solid var(--peer);padding-top:16px;font-size:23px;line-height:1.5}
.state b{display:block;font-size:29px;margin-bottom:8px}.foot{font-size:21px;color:var(--text-2);line-height:1.6;margin-top:26px}
.source{position:absolute;bottom:26px;left:52px;right:52px;border-top:1px solid var(--line);padding-top:12px;font-size:17px;line-height:1.5;color:var(--muted)}
.mono,code,kbd{font-family:var(--font-mono)}
.flow{display:grid;grid-template-columns:230px 1fr;gap:22px;align-items:stretch;margin-top:24px}
.trigger{border-radius:12px;background:var(--panel-3);padding:24px;font-size:27px;line-height:1.55;font-weight:700;color:var(--text-2)}
.chain{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.step{position:relative;border:1.5px solid var(--line-strong);background:var(--panel);border-radius:12px;padding:24px 21px;font-size:24px;line-height:1.55}
.step:not(:last-child):after{content:'→';position:absolute;right:-25px;top:42%;color:var(--muted);font-size:28px;background:var(--canvas);z-index:2}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:24px;line-height:1.55}
th{text-align:left;color:var(--text-2);font-size:21px;background:var(--panel-3);padding:16px 20px}
td{border-bottom:1px solid var(--line);padding:22px 20px;vertical-align:top}
td:first-child{font-weight:700}.value-table{font-size:22px;line-height:1.6}
.value-table td{padding:18px 18px}.value-table td:nth-child(2){font-size:25px;font-weight:700;color:var(--brand-deep)}
.value-table td:first-child{color:var(--text-2);font-weight:400}.value-table td:first-child span{font-size:18px}
.en .value-table{font-size:21px}.en .value-table td:nth-child(2){font-size:24px}.en h1{font-size:49px}
"""


def esc(s: str) -> str:
    return html.escape(s)


def page(lang: str, title: str, intro: str, body: str, height: int) -> str:
    label = 'AI 舰队手册' if lang == 'zh' else 'AI Fleet Handbook'
    locale = 'zh-CN' if lang == 'zh' else 'en'
    return f'''<!doctype html>
<html lang="{locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=1424">
<title>{esc(title)}</title><style id="metask-vi">{VI_CSS}</style><style>{CSS}</style></head>
<body><main class="canvas {lang}" style="height:{height}px">
<div class="eyebrow">{esc(label)}</div><img class="logo" src="{LOGO_DATA}" alt="">
<h1>{esc(title)}</h1><p class="intro">{esc(intro)}</p><div class="rule"></div>
{body}
<div class="source">{'AI 舰队手册 · 元任务实验室（MeTask AI Lab）' if lang == 'zh' else 'AI Fleet Handbook · MeTask AI Lab'}</div>
</main></body></html>'''


def card(number: str, title: str, content: list[str], kind: str = '') -> str:
    return f'<section class="card {kind}"><div class="num">{number}</div><h2>{esc(title)}</h2>' + ''.join(f'<p>{esc(x)}</p>' for x in content) + '</section>'


def review(lang: str) -> str:
    zh = lang == 'zh'
    if zh:
        cards = [
            ('01', '执行者', ['来自一家厂商', '判断与执行', '写下成果、依据和状态'], ''),
            ('02', '独立审核者', ['来自另一家厂商', '对照任务书和验收标准', '交回问题、证据和结论'], 'teal'),
            ('03', '验收', ['根据独立审核作判断', '合格，或退回修改', '作者不验收自己'], 'human'),
        ]
        states = [('完成', '活是否做完？'), ('交付', '成果是否交回？'), ('合格', '是否符合标准？')]
        title = '一家写，另一家审'
        intro = '同一份任务书，同一套验收标准。把不同的默认倾向带进审核。'
        ribbon = '<b>任务 → 执行 → 独立审核 → 验收</b><br>发现问题，交回修改；修改后，再交给另一家审。'
        foot = '完成、交付、合格，分开问。'
    else:
        cards = [
            ('01', 'Author', ['From one model provider', 'Make judgments and execute', 'Deliver work, evidence and status'], ''),
            ('02', 'Independent reviewer', ['From another provider', 'Check the task and acceptance criteria', 'Return issues, evidence and a verdict'], 'teal'),
            ('03', 'Acceptance', ['Decide using the independent review', 'Accept, or return for revision', 'Authors never accept their own work'], 'human'),
        ]
        states = [('Complete', 'Has the work been done?'), ('Delivered', 'Has the output been handed back?'), ('Accepted', 'Does it meet the criteria?')]
        title = 'One provider writes. Another reviews.'
        intro = 'One task brief. One set of acceptance criteria. Bring different default tendencies into the review.'
        ribbon = '<b>Task → Execution → Independent review → Acceptance</b><br>Return issues for revision, then have another provider review again.'
        foot = 'Ask about completion, delivery and acceptance separately.'
    body = '<div class="grid three">' + ''.join(card(*c) for c in cards) + '</div>'
    body += f'<div class="ribbon">{ribbon}</div><div class="states">'
    body += ''.join(f'<div class="state"><b>{esc(a)}</b>{esc(b)}</div>' for a, b in states)
    body += f'</div><p class="foot">{esc(foot)}</p>'
    return page(lang, title, intro, body, 1020 if zh else 1120)


def memory(lang: str) -> str:
    zh = lang == 'zh'
    if zh:
        cards = [
            ('01', '项目卡', ['规矩、在跑的事、等人定的事', '一页文件地图'], ''),
            ('02', '交接', ['按岗位与任务追加交接', '写清进度、产物、下一步'], ''),
            ('03', '决定记录', ['只追加', '记下决定和理由'], ''),
        ]
        flows = [('重启、换窗口或上下文压缩后', ['读项目卡与本岗位或本任务的最新交接', '核对文件和实际状态', '再动手做事']),
                 ('收工或上下文快满', ['核对并补写本任务交接', '项目经理核对项目卡', '让下个窗口接得上'])]
        title = '重启先读，收工先写'
        intro = '窗口会换，工作接在项目里的文件上。'
        ribbon = '<b>“进行中”是交接里的状态，不是运行证明。</b><br>先核对实际产物和运行状态，再继续。'
        foot = '重要决定、新规矩、后台任务当场写；收工时核对。'
    else:
        cards = [
            ('01', 'Project card', ['Rules, active work and pending decisions', 'A one-page file map'], ''),
            ('02', 'Handoff', ['Append by receiving role and task', 'Progress, outputs and the next step'], ''),
            ('03', 'Decision log', ['Append only', 'Record decisions and reasons'], ''),
        ]
        flows = [('After restart, a new window or context compaction', ['Read the card and the latest handoff for your role or task', 'Check files and the actual state', 'Then resume the work']),
                 ('Before stopping or context fills', ['Reconcile and append the task handoff', 'Project manager checks the card', 'Give the next window a clear start'])]
        title = 'Read on restart. Write before stopping.'
        intro = 'Sessions change. Project files carry the work forward.'
        ribbon = '<b>“In progress” in a handoff does not prove a task is running.</b><br>Check real outputs and execution state before continuing.'
        foot = 'Record important decisions, new rules and background tasks immediately; reconcile at closeout.'
    body = '<div class="grid three">' + ''.join(card(*c) for c in cards) + '</div>'
    for trigger, steps in flows:
        body += f'<section class="flow"><div class="trigger">{esc(trigger)}</div><div class="chain">'
        body += ''.join(f'<div class="step">{esc(s)}</div>' for s in steps) + '</div></section>'
    body += f'<div class="ribbon">{ribbon}</div><p class="foot">{esc(foot)}</p>'
    return page(lang, title, intro, body, 1340 if not zh else 1180).replace('</style>', '.flow{grid-template-columns:270px 1fr}</style>')


def decisions(lang: str) -> str:
    zh = lang == 'zh'
    if zh:
        title, intro = '人定方向，AI 在授权内判断', '把必须由人定的事写清，让授权范围内的判断继续向前。'
        headers = ['事项', '谁定', '怎么做']
        rows = [
            ('方向、对外承诺、花钱、删东西', '人', '由人拍板，留下决定'),
            ('授权范围内的方案和执行', 'AI 成员', '自己判断，对结果负责；遇到冲突主动升级'),
            ('反复出现的例外', '审批表指定的岗位', '在授权内定放行条件，约好下轮怎么查'),
            ('对外发出前的文字', '程序检查，独立核验', '按自己维护的词表逐行扫，再核对事实'),
            ('忘了、错了、不在时也必须发生的事', '写成程序', '用确定的触发条件执行，不靠反复提醒'),
        ]
        ribbon = '<b>硬边界只留几类。</b><br>其余写清风险和后果，让成员自己判断。'
        foot = '人在组织里面，也参与讨论和判断。授权要明确，不能由成员自行扩大。'
    else:
        title, intro = 'Humans set direction. AI judges within authority.', 'State what needs a human decision. Keep authorized work moving.'
        headers = ['Matter', 'Decision owner', 'How it works']
        rows = [
            ('Direction, external commitments, spending and deletion', 'Human', 'Make the final call and record the decision'),
            ('Plans and execution within delegated authority', 'AI members', 'Use judgment and own the result; escalate conflicts'),
            ('Recurring exceptions', 'Role named in the approval table', 'Set conditions within that role’s authority and agree how to check them next round'),
            ('Text before external release', 'Program check and independent verification', 'Scan against a reader-maintained word list, then verify facts'),
            ('Things that must happen even when a member forgets, errs or is absent', 'Put into a program', 'Use explicit triggers instead of repeated reminders'),
        ]
        ribbon = '<b>Keep hard boundaries to a few categories.</b><br>For the rest, explain risks and consequences so members can use judgment.'
        foot = 'The human is inside the organization. Delegated authority must be explicit.'
    body = '<table><colgroup><col style="width:34%"><col style="width:24%"><col style="width:42%"></colgroup><thead><tr>'
    body += ''.join(f'<th>{esc(h)}</th>' for h in headers) + '</tr></thead><tbody>'
    body += ''.join('<tr>' + ''.join(f'<td>{esc(x)}</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table>'
    body += f'<div class="ribbon">{ribbon}</div><p class="foot">{esc(foot)}</p>'
    return page(lang, title, intro, body, 1370 if not zh else 1160)


VALUES_ZH = [
    ('报喜不报忧', '求真', '读数和我们希望的不一样时，先信读数；宁可慢一点知道真相，也不要快一点骗自己；“不知道”是诚实的答案'),
    ('凭层级压过一线判断', '尊重', '每个人、每个 AI 伙伴都有自己的判断；站在全局的看得宽，盯着细节的看得深，常常在某些点上更对'),
    ('把人当审批按钮，\n把伙伴当命令工具', '两种存在一起做事', '合作，不是使用与被使用；人把住方向、重大承诺和组织怎样运转；AI 伙伴在授权范围内判断、执行，遇到冲突主动升级'),
    ('把判断推回给人', '对结果负责', '对结果负责，不是对流程负责；自己的判断当场定，不往外推；错了就认，做成机制'),
    ('背包袱、过度保守', '目标导向', '按能不能离目标更近来取舍，别背包袱；规则和如实披露要守住，违反会直接伤到目标，规则之内的空间要用足'),
    ('为了过关放宽检查', '正直地赢', '长期更划算的打法，不是姿态：在规则之内做到最好'),
]
VALUES_EN = [
    ('Reporting only good news', 'Seek truth', 'When readings differ from our hopes, trust the readings first. Better to learn the truth slowly than deceive ourselves quickly. “I do not know” is an honest answer.'),
    ('Rank overriding frontline judgment', 'Respect', 'Every person and AI partner has judgment. Those seeing the whole see broadly; those close to the details see deeply, and are often more right on particular points.'),
    ('Treating people as approval buttons and partners as command tools', 'Two kinds of beings, working together', 'Cooperate, rather than use and be used. Humans hold direction, major commitments and how the organization runs. AI partners judge and execute within delegated authority, and actively escalate conflicts.'),
    ('Pushing judgment back to the human', 'Own the result', 'Be responsible for results, not just process. Make the judgments that are yours without passing them on. Admit mistakes and turn the lesson into a mechanism.'),
    ('Carrying baggage and being too cautious', 'Stay goal-oriented', 'Choose by what brings the goal closer; do not carry baggage. Follow rules and disclose truthfully, because violations directly harm the goal. Use the room within the rules fully.'),
    ('Weakening checks to pass', 'Win with integrity', 'A better long-term way to play, not a posture: do the best within the rules.'),
]


def values(lang: str) -> str:
    zh = lang == 'zh'
    title = '价值观要落到具体判断上' if zh else 'Values guide concrete decisions.'
    intro = '我们的六条只作例子。每支舰队，都要定自己的。' if zh else 'Our six are examples. Each fleet should define its own.'
    headers = ['要纠正的倾向', '价值观', '落到判断上'] if zh else ['Tendency to address', 'Value', 'What it means in a decision']
    body = '<table class="value-table"><colgroup><col style="width:22%"><col style="width:20%"><col style="width:58%"></colgroup><thead><tr>'
    body += ''.join(f'<th>{esc(h)}</th>' for h in headers) + '</tr></thead><tbody>'
    body += ''.join('<tr>' + ''.join(f'<td>{esc(x).replace(chr(10), "<br>")}</td>' for x in row) + '</tr>' for row in (VALUES_ZH if zh else VALUES_EN)) + '</tbody></table>'
    footer = '这六条由成员提出、项目经理汇总，当时由人定稿。不同意见留了记录，每条都写清做什么、不做什么。' if zh else 'Members proposed these six values, the project manager collected their views, and the human made the final call. The record preserves dissent. Each value names actions and limits.'
    body += f'<p class="foot">{esc(footer)}</p>'
    return page(lang, title, intro, body, 1350 if zh else 1560)


CHART_TRANSLATIONS = [
    ('AI 舰队手册 · 元任务实验室（MeTask AI Lab）', 'AI Fleet Handbook · MeTask AI Lab'),
    ('AI 舰队组织架构，截至2026年11月15日', 'AI Fleet organization, as of 2026-11-15'),
    ('岗位跟着活长出来，模型跨岗共用', 'Work defines roles. Models are shared.'),
    ('截至 2026-11-15', 'As of 2026-11-15'),
    ('74 个岗位，其中 21 个是程序', '74 roles · 21 run by programs'),
    ('49 个岗位，其中 14 个是程序', '49 roles · 14 run by programs'),
    ('4 个岗位', '4 roles'),
    ('13 个岗位，其中 3 个是程序', '13 roles · 3 run by programs'),
    ('AI 担任的岗位', 'Role held by AI'),
    ('程序担任的岗位', 'Role held by a program'),
    ('人是其中一位成员', 'The human'),
    ('管目标和边界', 'Goals and boundaries'),
    ('组织与文化参谋', 'Organization &amp; culture'),
    ('参谋岗 · 不派活、不设关卡', 'Advisory · No dispatch or gates'),
    ('由 AI 项目经理负责', 'Led by an AI project manager'),
    ('由来：模型研发的 AI 项目经理总被盯作业、查状态打断，自己提出设一个值班岗，主要交给程序；人同意了。', 'How it started: the model R&amp;D project manager kept being interrupted by job monitoring and status checks. It proposed a duty role, mostly run by programs, and the human agreed.'),
    ('模型研发 BU', 'Model R&amp;D BU'),
    ('评测与质量线', 'Evaluation and Quality'),
    ('媒体线', 'Media'),
    ('训练线', 'Training'),
    ('论文线', 'Papers'),
    ('活动分享', 'Talks and events'),
    ('开源专项', 'Open source'),
    ('内容矩阵', 'Content channels'),
    ('例：调度值班（一个岗）', 'Example: Dispatch and watch (one&nbsp;role)'),
    ('盯作业', 'Job monitoring'),
    ('定时巡查', 'Scheduled checks'),
    ('磁盘看门狗', 'Disk watch'),
    ('唤醒项目经理', 'Wakes the manager'),
    ('参谋和其他工作线（不展开）：8 个岗位，其中 4 个是程序', 'Advisory and other work lines (not expanded): 8 roles · 4 run by programs'),
    ('共用的模型', 'Shared models'),
    ('先后来自六家厂商，派进岗位，不构成组织单元', 'From six providers over time; assigned to roles; not organizational units.'),
    ('先有活，后有岗：AI 提议设岗，按审批表定。岗位不共用，模型共用；程序也是成员', 'Work comes first, then roles: AI members propose roles. The approval table names who decides. Roles are not shared; models are. Programs are members too.'),
    ('<strong>AI 舰队</strong>', '<strong>AI Fleet · The human is one of the members</strong>'),
    ('AI 舰队', 'AI Fleet'),
]


def build(charts_only: bool = False) -> None:
    zh = (SRC / 'chart-zh.html').read_text(encoding='utf-8')
    zh = re.sub(r'<style id="metask-vi">.*?</style>', lambda _: '<style id="metask-vi">' + VI_CSS + '</style>', zh, flags=re.S)
    (SRC / 'chart-zh.html').write_text(zh, encoding='utf-8')
    en = zh.replace('lang="zh-CN"', 'lang="en"').replace('class="canvas zh"', 'class="canvas en"')
    for source, target in CHART_TRANSLATIONS:
        en = en.replace(source, target)
    # English labels need more width per word; positions and edges stay fixed.
    en = en.replace('</style>', '.en h1{font-size:64px;letter-spacing:-.025em}.en .department h2{font-size:58px}.en .lead{font-size:42px}.en .count{font-size:44px}.en .tag{font-size:36px}.en .example,.en .example p,.en .example li,.en .example .all{font-size:36px}.en .example h3{font-size:40px}.en .member strong{font-size:42px}.en .member span{font-size:36px}.en .band{font-size:36px}.en .foot{font-size:30px}</style>')
    (SRC / 'chart-en.html').write_text(en, encoding='utf-8')
    if charts_only:
        return
    for name, maker in [('review', review), ('memory', memory), ('decisions', decisions), ('values', values)]:
        for lang in ('zh', 'en'):
            (SRC / f'{name}-{lang}.html').write_text(maker(lang), encoding='utf-8')


def render(charts_only: bool = False) -> None:
    from playwright.sync_api import sync_playwright
    import os
    chrome = Path(os.environ.get('PROGRAMFILES', '')) / 'Google/Chrome/Application/chrome.exe'
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome), headless=True, args=['--disable-gpu', '--no-sandbox'])
        context = browser.new_context(viewport={'width': WIDTH, 'height': 1700}, device_scale_factor=2)
        # Artwork is self-contained. Block all remote requests explicitly.
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:')) else route.abort())
        tab = context.new_page()
        failed = False
        for source in sorted(SRC.glob('chart-*.html' if charts_only else '*-??.html')):
            tab.goto(source.as_uri(), wait_until='load', timeout=30000)
            tab.evaluate('document.fonts.ready')
            canvas = tab.locator('.canvas')
            target = ASSETS / source.with_suffix('.png').name
            canvas.screenshot(path=str(target), animations='disabled')
            bounds = tab.evaluate('''() => {const c=document.querySelector('.canvas').getBoundingClientRect();return Array.from(document.querySelectorAll('.canvas *')).filter(e=>(e.getBoundingClientRect().bottom>c.bottom+1 || e.getBoundingClientRect().right>c.right+1 || e.getBoundingClientRect().left<c.left-1 || e.getBoundingClientRect().top<c.top-1)).map(e=>e.tagName+': '+e.textContent.slice(0,60))}''')
            overflow = tab.evaluate('''() => Array.from(document.querySelectorAll('.node,.panel,.band,.card,td')).filter(e=>e.scrollHeight>e.clientHeight+1 || e.scrollWidth>e.clientWidth+1).map(e=>e.textContent.slice(0,60))''')
            # Absolute footers need their own collision check, beyond scroll bounds.
            footer_gap = tab.evaluate('''() => {
                const c = document.querySelector('.canvas'), source = c.querySelector('.source');
                const walk = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
                let n, bottom = 0;
                while (n = walk.nextNode()) {
                    if (!n.textContent.trim() || n.parentElement.closest('.source')) continue;
                    const r = document.createRange(); r.selectNodeContents(n);
                    bottom = Math.max(bottom, r.getBoundingClientRect().bottom);
                }
                return Math.round((source.getBoundingClientRect().top - bottom)*10)/10;
            }''')
            if footer_gap < 24:
                overflow.append(f'source footer gap {footer_gap}px < 24px')
            if source.name.startswith('chart-'):
                font_check = tab.evaluate(r'''() => {
                    const c = document.querySelector('.canvas');
                    const walk = document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
                    const entries = []; let n;
                    while (n = walk.nextNode()) {
                        const e = n.parentElement, text = n.textContent.trim().replace(/\s+/g, ' ');
                        if (!text || e.closest('.foot,.source,style,script')) continue;
                        const style = getComputedStyle(e);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        const range = document.createRange(); range.selectNodeContents(n);
                        if (!Array.from(range.getClientRects()).some(r => r.width > 0 && r.height > 0)) continue;
                        const group = e.closest('h1') ? 'title' : e.closest('.department h2') ? 'department-name' : e.closest('.department') ? 'department-text' : 'other';
                        const required = {'title':56,'department-name':48,'department-text':36,'other':28}[group];
                        entries.push({size:parseFloat(style.fontSize),required,group,text:text.slice(0,100)});
                    }
                    const minimum = entries.reduce((a,b) => !a || b.size < a.size ? b : a, null);
                    const groups = Object.fromEntries(['title','department-name','department-text','other'].map(g => [g,Math.min(...entries.filter(e => e.group===g).map(e => e.size))]));
                    const violations = entries.filter(e => e.size < e.required);
                    for (const group of Object.keys(groups)) if (!Number.isFinite(groups[group])) violations.push({group,text:'missing required text group'});
                    return {minimum,groups,violations};
                }''')
                print(f'{target.name}: source-footer-gap={footer_gap}px; font-check={font_check}')
                failed = failed or bool(font_check['violations'])
            failed = failed or bool(bounds or overflow)
            print(f'{target.name}: {target.stat().st_size} bytes; out-of-canvas={bounds}; text-overflow={overflow}')
        context.close()
        browser.close()
        if failed:
            raise SystemExit('Artwork overflow detected')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--charts-only', action='store_true', help='Build and render only the first-day organization charts')
    args = parser.parse_args()
    build(charts_only=args.charts_only)
    if args.render:
        render(charts_only=args.charts_only)

