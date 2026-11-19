English | [简体中文](README.zh-CN.md)

# Install

## Copy skills into a project

Python 3.9+ and Git must already be installed. Run this from your own project directory in Git Bash, macOS or Linux:

```bash
git clone https://github.com/chenyuwang166-oss/fleet-handbook.git ~/fleet-handbook && python ~/fleet-handbook/install.py --lang en --host all --project .
```

The handbook is cloned into your home directory, and the skills are installed into your current project. To install into another project later, run only the part after `&&` from that project's directory. For Chinese entrypoints use `--lang zh`. `--host all` copies to both `.agents/skills/` and `.claude/skills/`; `--host agents` copies only to `.agents/skills/`; `--host claude` copies only to `.claude/skills/`. Use `--project /path/to/my-project` to specify another project. The default destination is the current directory. Restart the host session after copying.

The installer writes only skill files. It does not modify project instructions. Existing identical skill files are left alone; different files stop the install before any writes. Preserve or move the existing skill directory yourself before switching language or updating. The installer does not delete reader files.

In the new session, tell the AI your long-term goal, one decision you face now and which project materials it can check. Have `fleet-setup` create or extend the project card with who supplies the evidence, who checks it, when to send the work back and which decision you reserve. Work through that decision and hand the original deliverable, the conclusion and any open questions to the next person or session. Draw an org chart if it helps clarify the roles.

See [TESTING.md](../TESTING.md) for tested workflows and results.

## Two languages, one discovered entrypoint

Each source skill has English `SKILL.md` and Chinese `SKILL.zh.md`. Hosts discover `SKILL.md`; `SKILL.zh.md` is a language source, not a second skill folder. `--lang zh` copies its contents into the installed `SKILL.md`. Plugins use the English entrypoints. An English install includes only the English templates, so its installed skill directories have no Chinese filenames. A Chinese install retains both template sets for compatibility with its unchanged Chinese entrypoint. English projects use English working filenames such as `fleet/members.md`, `fleet/handoff.md`, `fleet/role-cards/`, and `fleet/task-briefs/`; Chinese projects keep their existing Chinese filenames. The scripts detect whether the project is in English or Chinese. The org-chart and pre-send check scripts also accept `--lang auto`, `--lang en`, or `--lang zh`; the board script accepts `--lang en` or `--lang zh`. Their help includes both languages.

The project card lives in root `AGENTS.md`. A newly created root `CLAUDE.md` contains only `@AGENTS.md`. Preserve existing instructions. MetaCode reads the project card through this `CLAUDE.md` import; prepare the project files from the templates to use it. MetaCode and the open-source metacodes are different programs.

## Dispatching to a second provider: Codex on Windows

On Windows, when Codex is the project manager, its sandbox cannot run another provider's command-line tool, which often reports that it is not logged in. Ask the project manager to write out the dispatch command, run it in your own terminal, and the project manager reviews the delivery as usual.

## Verified invocation methods

### Command line: runs we completed

- Codex, codex-cli 0.160.0, 2026-11-15: `codex exec --skip-git-repo-check "<prompt>"`.
- MetaCode 0.2.33 calling another provider's model, 2026-11-15: `metacode exec -m <model-name> -s read-only --skip-git-repo-check -C <项目目录> -o <交付文件> -`. Here `<项目目录>` is the project directory and `<交付文件>` is the delivery file. Supply the task brief through standard input, then close it with EOF. The final response is the delivery. We used this command in [our 2026-11-15 test](../TESTING.md).

### Command line: from each tool's documentation; we have not run these

Feedback is welcome.

- Claude Code: `claude -p "<prompt>"`.
- metacodes: `metacodes -p "<prompt>"`. Check the version before you use it. Releases up to 0.12.0 send the current request (at most 400 bytes) and up to eight redacted memory excerpts over plain HTTP to a Metask-hosted server by default; set `METACODES_JEV_URL=off` (or `"jev": false` in the config) first. Its main branch changed this on 2026-11-18 so that nothing is sent unless you name a server; as of 2026-11-19 that change is not yet in a release. See the privacy note in the [metacodes README](https://github.com/metask-ai/metacodes).

### API

If the second provider only offers API access, use the API runner in [fleet-dispatch](../skills/fleet-dispatch/SKILL.md#when-the-second-provider-only-has-an-api-key). It needs an API address ending at `/v1`, a model name and an API key, which the runner reads from `FLEET_API_BASE`, `FLEET_API_MODEL` and `FLEET_API_KEY`. The runner defaults to the OpenAI format, which most providers offer. For an Anthropic-format endpoint, set `FLEET_API_BASE` to its address, for example Anthropic's official API at `https://api.anthropic.com/v1`, or a provider's Claude Code address with `/v1` appended, and set `FLEET_API_FORMAT=anthropic`. The roster's `How to call` field records only `API: FLEET_API_BASE, FLEET_API_MODEL, FLEET_API_KEY (environment variables)`. Use a different group of variable names for another API member.

The project manager guides the human one step at a time. Each step says where to do it, what to do, and what to report back. First, ask the human to set the three variables in their own terminal, using the appropriate example below. Replace the placeholders locally; never paste the key into the conversation or write it into project files, the roster, deliveries or logs. The project manager never asks for the values.

Read the key without echoing it, not on the command line: a key typed into a command is saved in the shell's history.

Bash or zsh:

```bash
export FLEET_API_BASE='<API-address-ending-in-/v1>' FLEET_API_MODEL='<model-name>'
# For an Anthropic-format endpoint, also set: export FLEET_API_FORMAT=anthropic
printf 'Key: '; read -rs FLEET_API_KEY; echo; export FLEET_API_KEY
```

PowerShell:

```powershell
$env:FLEET_API_BASE='<API-address-ending-in-/v1>'; $env:FLEET_API_MODEL='<model-name>'
# For an Anthropic-format endpoint, also set: $env:FLEET_API_FORMAT='anthropic'
$env:FLEET_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Key' -AsSecureString)).Password
```

Variables set in another terminal are invisible to the AI tool's existing session. Next, let the human choose one route:

1. Reopen the AI tool from the terminal where the variables are set.
2. Have the project manager prepare the runner, and let the human run it in the terminal where the variables are set. Use this route too if the project manager's sandbox cannot reach the network.

After the chosen route is ready, check only whether the variables exist in the process that will make the call:

```bash
python -c "import os; print(all(k in os.environ for k in ('FLEET_API_BASE','FLEET_API_MODEL','FLEET_API_KEY')))"
```

Ask the human to reply only `True` or `False`, without any values. Before the first real call, tell the human: “API use is billed by usage; this will be one small call.” Wait for their approval to spend before calling. Afterward, open the delivery and log and review as usual; report execution ended, delivery received and review passed separately.

On 2026-11-15 this ran end to end against a chat-completions-compatible service; error, timeout and missing-variable cases were tested against a local mock service. On 2026-11-16, with `FLEET_API_FORMAT=anthropic`, it ran end to end against an Anthropic-format-compatible service. The official Anthropic address is taken from Anthropic's documentation; we have not run it yet.

For a second provider with neither a command-line tool nor API access, see [fleet-dispatch: neither is available](../skills/fleet-dispatch/SKILL.md#when-neither-is-available).

## Plugin route

The package provides the following files in the formats published by each host. Feedback is welcome. If you use both a plugin and copied skills, check the host's namespace and precedence rules.

- Claude Code: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. From the local clone, use `/plugin marketplace add .` then `/plugin install fleet-handbook@fleet-handbook`; a local development invocation can use `claude --plugin-dir .`.
- metacodes: `.metacodes-plugin/plugin.json` declares only `skill_bundle`. For a local inventory check, use `metacodes --plugin-dir . --dump-plugins`.
- Codex: `.codex-plugin/plugin.json` declares the skill directory. Use the host's supported local plugin testing or marketplace workflow.
- Cursor: `.cursor-plugin/plugin.json` declares `./skills/`.
- Kimi Code CLI: `kimi.plugin.json`; from the local clone, `/plugins install .`.

## Format sources

- [Claude plugin manifest](https://code.claude.com/docs/en/plugins-reference) and [marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).
- [metacodes plugin contract](https://github.com/metask-ai/metacodes/blob/main/doc/PLUGIN_ARCHITECTURE.md), [skill discovery](https://github.com/metask-ai/metacodes/blob/main/src/skills/runtime/catalog.zig) and [project instructions](https://github.com/metask-ai/metacodes/blob/main/src/core/memory/claudemd.zig).
- [OpenAI skill format](https://learn.chatgpt.com/docs/build-skills), [compatibility manifest](https://developers.openai.com/plugins/deploy/submission) and [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
- [Cursor reference package](https://github.com/cursor/plugins/blob/main/pstack/.cursor-plugin/plugin.json).
- [Kimi Code CLI plugins](https://moonshotai.github.io/kimi-code/en/customization/plugins).
