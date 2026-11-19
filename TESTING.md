# Test status

[简体中文](TESTING.zh-CN.md)

What was tested: only what the table below lists, all on Windows, each in a separate project. The task runs used synthetic annual-report material.

| Tool and configuration | Date | Observed work | Result |
|---|---|---|---|
| Codex · codex-cli 0.160.0; author: another provider's model via MetaCode 0.2.33 | 2026-11-15 | Built the project, drew the organization chart, wrote task briefs, dispatched work (on Windows, the human ran the project manager's command in their own terminal), completed two rounds of drafting and review, wrote a handoff, continued in a new session, and passed the second draft. | Ran end to end |
| MetaCode continuity | 2026-11-11 | Continued in a new session from the project card and handoff, checked facts against the source, preserved the existing delivery, and left human decisions to the human. | Ran end to end |
| Install by AI: Codex (once in Chinese, once in English); another provider's model via MetaCode | 2026-11-15 | Given one sentence and a local clone of this repository, each read the root `AGENTS.md`, installed the skills (seven at the time) into the human's empty project without changing the repository, then opened fleet-setup and asked its three questions. | Ran end to end |
| Dispatch through an API: via a chat-completions-compatible service | 2026-11-15 | Ran the API runner from fleet-dispatch unchanged: sent the brief, saved the reply unchanged as the delivery, and logged HTTP 200. The key was read only from the environment and appears in neither the delivery nor the log. Error, timeout and missing-variable cases were tested against a local mock service. | Ran end to end |
| Dispatch through an API (Anthropic format): via an Anthropic Messages-compatible service, with `FLEET_API_FORMAT=anthropic` | 2026-11-16 | Ran the same API runner unchanged: sent the brief to `/messages`, saved the reply's text blocks as the delivery, and logged HTTP 200 and the stop reason. The key was read only from the environment and appears in neither the delivery nor the log. Empty replies, malformed replies, an invalid format setting and dropped connections were tested against a local mock service. The official Anthropic address is taken from Anthropic's documentation; we have not run it yet. | Ran end to end |

The November 15 installation test covered only the seven skills available at the time, before the trial skills `fleet-rounds` and `fleet-issues` were added.

Other tools that use the Agent Skills format: format-compatible; feedback welcome.

## This run

Codex acted as project manager and reviewer; another provider's model, called through MetaCode, wrote the summary. The first review caught a recommendation labeled as source fact and a delivery mixed with task-brief commentary. A new session read the project card and handoff, prepared the revision task brief, and reviewed the returned second draft. The corrected evidence labels and standalone summary passed.

## Repeat a test

Use your own non-sensitive material or create synthetic material for the test, then follow [installation](install/README.md). Record the tool, version, model, date and completed work separately. To test continuity, write a handoff, give a new session only a brief request to continue, then check source facts, existing deliveries and decisions left to the human. Python unit tests check local files and scripts; they do not replace a live model workflow or continuity test.
