[English](README.md) | 简体中文

# 安装

## 把技能装进项目

先备好 Python 3.9 以上和 Git。在你自己的项目目录里，用 Git Bash、macOS 或 Linux 终端运行：

```bash
git clone https://github.com/chenyuwang166-oss/fleet-handbook.git ~/fleet-handbook && python ~/fleet-handbook/install.py --lang zh --host all --project .
```

手册会下载到主目录，技能装进当前项目。以后给别的项目装，在那个项目目录里只跑 `&&` 后半句。英文入口用 `--lang en`。`--host all` 同时复制到 `.agents/skills/` 和 `.claude/skills/`；`--host agents` 只复制到 `.agents/skills/`；`--host claude` 只复制到 `.claude/skills/`。用 `--project /path/to/my-project` 可以指定另一个项目，默认目标是当前目录。安装后重新开一个宿主会话。

安装器只写技能文件，不修改项目说明。同名且内容相同的技能文件保持原样；遇到不同内容，安装器会在写入前停止。切换语言或更新前，先自行保留或移走现有技能目录。安装器不删除读者文件。

在新会话里，告诉 AI 你的长期目标、眼前要做的一个决定，以及它可以核对的项目材料。`fleet-setup` 会据此创建或补充项目卡，记下谁交证据、谁验收、什么情况退回，以及哪件事由你定。先做这一关，把原件、结论和未决事项交给下一位。需要看清岗位关系时，再画组织图。

实测流程和结果见 [TESTING.zh-CN.md](../TESTING.zh-CN.md)。

## 两种语言，一个技能入口

每个源技能都有英文 `SKILL.md` 和中文 `SKILL.zh.md`。宿主发现的是 `SKILL.md`；`SKILL.zh.md` 是语言源文件，不是第二个技能目录。`--lang zh` 会把中文源文件的内容复制成安装后的 `SKILL.md`。插件使用英文入口。英文安装只包含英文模板，因此装好的技能目录里没有中文文件名。中文安装保留两套模板，供现有中文入口使用。英文项目采用 `fleet/members.md`、`fleet/handoff.md`、`fleet/role-cards/`、`fleet/task-briefs/` 等英文工作文件名；中文项目沿用现有中文文件名。脚本会识别项目是中文还是英文。组织图和发前检查脚本也接受 `--lang auto`、`--lang en` 或 `--lang zh`；看板脚本接受 `--lang en` 或 `--lang zh`。帮助信息包含两种语言。

项目卡放在项目根目录的 `AGENTS.md`。新建的根目录 `CLAUDE.md` 只有 `@AGENTS.md`，原有说明要保留。MetaCode 通过 `CLAUDE.md` 的导入读项目卡，照模板准备项目文件即可。MetaCode 和开源的 metacodes 是两个程序。

## 派给第二家：Windows 上的 Codex

Windows 上 Codex 当项目经理时，它的沙箱里跑不了另一家的命令行，常报“未登录”，其实是沙箱读不到那边的登录。请项目经理把派单命令写好，你在自己的终端里跑；交付回来，它照常审。

## 核实过的调用方式

### 命令行：我们跑通过的

- Codex，codex-cli 0.160.0，2026-11-15：`codex exec --skip-git-repo-check "<提示>"`。
- MetaCode 0.2.33 调另一家厂商的模型，2026-11-15：`metacode exec -m <模型名> -s read-only --skip-git-repo-check -C <项目目录> -o <交付文件> -`。任务书从标准输入给，EOF 关闭；末条回复为交付。[2026-11-15 那次测试](../TESTING.zh-CN.md)用的就是这条命令。

### 命令行：照各工具自己的文档写的，我们还没跑过

欢迎反馈。

- Claude Code：`claude -p "<提示>"`。
- metacodes：`metacodes -p "<提示>"`。用之前先看版本：0.12.0 及更早的发布版，默认会把当前请求（最多 400 字节）和最多八段脱敏的记忆摘录，用明文 HTTP 发到 Metask 的服务器，先设 `METACODES_JEV_URL=off`（或在配置里写 `"jev": false`）再用。它的主线 2026-11-18 已经改成不指定服务器地址就不发；写这句话时（2026-11-19），这个改动还没进发布版。详见 [metacodes README](https://github.com/metask-ai/metacodes) 的隐私说明。

### 接口

第二家只有接口密钥时，用 [fleet-dispatch 里的接口运行片段](../skills/fleet-dispatch/SKILL.zh.md#第二家只有接口密钥)。需要第二家的接口地址（到 `/v1` 这一级）、模型名和密钥，运行片段从 `FLEET_API_BASE`、`FLEET_API_MODEL`、`FLEET_API_KEY` 读取这三样。片段默认发 OpenAI 格式，多数厂商都有。只给 Anthropic 格式的：`FLEET_API_BASE` 填它的地址，比如 Anthropic 官方的 `https://api.anthropic.com/v1`；厂商另给 Claude Code 用的地址，后面加上 `/v1` 再填；同时设 `FLEET_API_FORMAT=anthropic`。名册“怎么调用”只写“接口：FLEET_API_BASE、FLEET_API_MODEL、FLEET_API_KEY（环境变量）”。接另一个接口成员时换一组变量名，也只记名字。

项目经理带着人做，一次只给一步，每一步写明在哪做、做什么、做完回它什么。先请人在自己的终端里设这三个环境变量，按所用终端选择下方示例。占位值由人在本地替换；密钥不贴进对话，不写进项目文件、名册、交付或日志。项目经理也不问变量的值。

密钥用不回显的方式读入，不写进命令行：写在命令行里的密钥会存进终端的历史记录。

Bash 或 zsh：

```bash
export FLEET_API_BASE='<接口地址，到 /v1>' FLEET_API_MODEL='<模型名>'
# 第二家只给 Anthropic 格式时再加：export FLEET_API_FORMAT=anthropic
printf '密钥：'; read -rs FLEET_API_KEY; echo; export FLEET_API_KEY
```

PowerShell：

```powershell
$env:FLEET_API_BASE='<接口地址，到 /v1>'; $env:FLEET_API_MODEL='<模型名>'
# 第二家只给 Anthropic 格式时再加：$env:FLEET_API_FORMAT='anthropic'
$env:FLEET_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host '密钥' -AsSecureString)).Password
```

人在另一个终端里设的变量，AI 工具里已经打开的会话看不见。接着让人选一条路：

1. 在设好变量的那个终端里重新打开 AI 工具。
2. 项目经理把运行片段写好，人在自己设好变量的终端里跑。项目经理所在的沙箱连不了网时，也走这一条。

选好并完成那条路以后，只在将要发起调用的进程里核对变量在不在：

```bash
python -c "import os; print(all(k in os.environ for k in ('FLEET_API_BASE','FLEET_API_MODEL','FLEET_API_KEY')))"
```

请人只回 `True` 或 `False`，不回变量值。第一次真调之前，告诉人：“接口按用量收费，这一下是很小的一次调用。”人点头同意花钱，再调。跑完照常看交付和日志，照常审；运行结束、收到交付、审核通过分别报。

2026-11-15 对一个兼容通用对话接口的服务实测跑通；出错、超时、缺变量这几种情况，对着本地模拟服务测过。2026-11-16 设了 `FLEET_API_FORMAT=anthropic`，对一个兼容 Anthropic 格式的服务实测跑通。Anthropic 官方地址照其文档写，我们还没跑过。

没有命令行也没有接口的，见 [fleet-dispatch 里“两样都没有”](../skills/fleet-dispatch/SKILL.zh.md#两样都没有)那一句。

## 插件方式

包内按各宿主公开的格式提供以下文件，欢迎反馈。同时使用插件和复制的技能时，先查看宿主的命名空间和优先级规则。

- Claude Code：`.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json`。在本地克隆目录里，先用 `/plugin marketplace add .`，再用 `/plugin install fleet-handbook@fleet-handbook`；本地开发也可以用 `claude --plugin-dir .`。
- metacodes：`.metacodes-plugin/plugin.json` 只声明 `skill_bundle`。本地清单检查用 `metacodes --plugin-dir . --dump-plugins`。
- Codex：`.codex-plugin/plugin.json` 声明技能目录，按宿主支持的本地插件测试或市场流程使用。
- Cursor：`.cursor-plugin/plugin.json` 声明 `./skills/`。
- Kimi Code CLI：`kimi.plugin.json`；在本地克隆目录里用 `/plugins install .`。

## 格式来源

- [Claude 插件清单](https://code.claude.com/docs/en/plugins-reference)和[插件市场](https://code.claude.com/docs/en/plugin-marketplaces)。
- [metacodes 插件约定](https://github.com/metask-ai/metacodes/blob/main/doc/PLUGIN_ARCHITECTURE.md)、[技能发现](https://github.com/metask-ai/metacodes/blob/main/src/skills/runtime/catalog.zig)和[项目说明](https://github.com/metask-ai/metacodes/blob/main/src/core/memory/claudemd.zig)。
- [OpenAI 技能格式](https://learn.chatgpt.com/docs/build-skills)、[兼容性清单](https://developers.openai.com/plugins/deploy/submission)和[非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)。
- [Cursor 参考包](https://github.com/cursor/plugins/blob/main/pstack/.cursor-plugin/plugin.json)。
- [Kimi Code CLI 插件](https://moonshotai.github.io/kimi-code/en/customization/plugins)。
