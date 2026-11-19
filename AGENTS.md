# AI Fleet Handbook

Nine skills and a handbook help a human build a fleet of models from different providers that divide work and review one another.

When someone asks to use or install the handbook, start with a decision in their project. Pick up from any steps they have already completed.

1. Ask what the project aims to achieve over time, then which decision is due next and whose work depends on it. Use any answers already given. If the decision is unclear, ask what someone on the project is waiting for this week.
2. Ask for the project directory and verify the confirmed path before installing. If the handbook has not been cloned, run `git clone https://github.com/chenyuwang166-oss/fleet-handbook.git ~/fleet-handbook`. From the clone, run `python install.py --lang en --host all --project /path/to/their-project`, replacing the path with the project directory outside the clone. Use `--lang zh` for Chinese.
3. Follow the project's `.claude/skills/fleet-setup/SKILL.md` or `.agents/skills/fleet-setup/SKILL.md` directly if the host has not loaded it. Check the project materials and existing constraints. Ask one question at a time about anything still missing.
4. Use fleet-setup to record who supplies the evidence, who checks it and who has authority over any unresolved decision. Keep the project's existing tools and workflows. Identify the roles this decision actually needs.
5. Use fleet-taskbook to brief just this piece of work. Point to the source materials, name one deliverable, and spell out the acceptance and return conditions. Show the first brief to the human and ask them to approve it or specify changes. Check their reply against the goal and revise the brief as needed before dispatch.
6. Ask in chat whether they have a second provider's command-line tool, only an API key, or neither. Follow fleet-dispatch to connect it one step at a time; request only environment variable names for API access. Before each method's first call, explain the small cost and wait for agreement; test with a harmless request such as “Reply OK”, then record the verified method and date in the roster. Neither available? Explain that cross-provider dispatch needs programmatic access to a second provider; continue with one.
7. Use fleet-dispatch to assign the brief to the author, collect the original deliverable and have a peer check it against the agreed conditions. For independent review, give a model from a different provider than the author the same source materials, deliverable and criteria. Return work that misses a condition to the author with the evidence. Record any disagreement and take the open question to the role authorized to decide. Report execution, receipt and review separately. With only one provider, continue the work and mark cross-provider review as pending.
8. Use fleet-memory to verify the handoff against the deliverable. Record the decision, its grounds and what still needs checking. When the next member takes over, have them use the project card, deliverable and handoff to explain what can continue, why, and what must wait. If the responsibilities are easier to see in a diagram, offer an org chart using fleet-chart.
9. Leave direction, external commitments, spending, and deletion to the human. When help is needed, explain what and why; give one step at a time with where to act, an exact command when applicable, and what to reply. Verify the reply, then continue or give the next fix without restarting the questions; never ask for keys or passwords, and never have them pasted into the chat.

10. For suggestions or problem reports about the AI Fleet Handbook, skip installation and follow [fleet-setup’s issue flow](skills/fleet-setup/SKILL.md#report-an-issue-to-the-ai-fleet-handbook). Draft in the human’s language, remove sensitive details, explain that issues are public, and show the exact title and body first; after edits, show them again. Ask “Submit this?” and wait for explicit approval; without approval, do not submit. After approval, use authenticated `gh` or give a prefilled link for the human to submit.

Skills: `skills/`; handbook: `handbook/`.

# AI 舰队手册

九个技能和一本手册，帮你搭一支多家模型分工、互相审的 AI 舰队。

人让你使用或安装这个包时，从项目里一个要做的决定入手。已有进度先核对，从那里续做。

1. 先问项目的长期目标，再问眼前要做哪个决定、它会影响谁的下一步。人已经说过的就沿用。还选不出这一关，就问项目里这周谁在等什么。
2. 问清项目目录，核对人已确认的路径再安装。还没克隆手册，就运行 `git clone https://github.com/chenyuwang166-oss/fleet-handbook.git ~/fleet-handbook`。从克隆目录运行 `python install.py --lang zh --host all --project /path/to/their-project`，把路径换成克隆目录以外的实际项目目录。英文项目用 `--lang en`。
3. 接着照项目里的 `.claude/skills/fleet-setup/SKILL.md` 或 `.agents/skills/fleet-setup/SKILL.md` 做。宿主还没载入就直接读文件。先核对原材料和沿用的约束，缺什么再问，一次问一件。
4. 用 fleet-setup 记清谁交证据、谁验收、未决事项由谁定。沿用项目里的工具和工作流，写明这一关需要哪些岗位。
5. 用 fleet-taskbook 只给这一关写任务书，指向原材料，写清一件交付、怎样算验收通过、什么情况要退回。首份任务书请人过目，回“照做”或指出要改哪里。对照目标核实答复，按需修改后再派活。
6. 问清第二家是有命令行工具、只有接口密钥，还是两样都没有。照 fleet-dispatch 一步步接上；接口只问环境变量名。每个调用方式第一次真调前说明会花一点钱，等人点头，用一条不伤东西的小请求（如只回“OK”）试通，再把方式和日期记进名册。两样都没有，说明跨厂商派活需要第二家能被程序调到，只用一家照样往下做。
7. 用 fleet-dispatch 把任务书派给作者，收回交付原件，请同伴按约定条件核对。跨厂商独审时，把同一份原材料、交付和验收条件交给与作者不同厂商的模型。没达到条件就附依据退给作者。意见有分歧，记录异议，把待决项交给有权限的岗位。分开报执行是否结束、交付是否收到、审核是否通过。只有一家就继续做，把跨厂商独审记为待办。
8. 用 fleet-memory 对着交付核实交接，写明决定、理由和待核事项。下一位接手时，请它只凭项目卡、交付和交接说出能继续什么、为什么、哪一步还得等。岗位关系需要画出来才看得清时，可以用 fleet-chart 出组织图。
9. 方向、对外承诺、花钱、删东西，留给人定。要人配合时说清做什么、为什么；一次只给一步，写明在哪做、可照抄的命令和做完回什么；人回了先核对，再继续或给下一步修正，不从头再问；不问密钥、密码的值，也不让人发来。

10. 人说“给舰队手册提个建议”或“给舰队手册报个问题”时，跳过安装，照 [fleet-setup 的提 issue 一节](skills/fleet-setup/SKILL.zh.md#给舰队手册提-issue)做。用人的语言起草、去掉敏感内容，说明 issue 是公开的，先把标题和正文原样给人看；人修改了就照改，再把标题和正文给人看。问“这样提吗”，等人点头；没点头，不提交。点头后用已登录的 `gh` 提交，或给预填链接由人提交。

技能在 `skills/`，手册在 `handbook/`。
