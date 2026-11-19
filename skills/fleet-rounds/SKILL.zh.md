---
name: fleet-rounds
description: 试用。需要定时巡查项目，或在接到提醒后推进一轮已定工作时使用。区分宿主提醒、接单和实际进展，把反复停顿留作复盘依据。
---

# 醒来，把舰队往前推一轮

**试用。** 我们在自己的舰队里试用这套做法。每轮查清宿主是否发出提醒、谁接下了任务、文件或审核记录里能看到什么进展。把反复催问和停顿留给下次复盘。按时提醒得靠宿主提供调度。

分两层：值守按批准的间隔检查并提醒；被叫醒的项目经理按下面 0—7 步推进一轮。值守不代替项目经理干活，检查一次不等于已经叫醒、接单或完成。技能不自带定时器；两层都在指定项目的已有授权内运行。

以下按中文项目的文件名写；英文项目用英文文件名，以项目卡为准。恢复、交接、续接三行和“等我定”照 [fleet-memory](../fleet-memory/SKILL.zh.md)；这里补值守与执行轮次的安排。定时只负责叫醒；节点做完后重新排活、等人的事分流、出了错告诉人，靠成员照 fleet-memory 做，本包不替你盯。

值守记录只用项目卡指定的一份：英文项目用 `fleet/watch.jsonl`；中文项目照项目卡的中文文件名惯例，例如 `fleet/值守.jsonl`。挂载时显式传入项目内相对路径 `RecordPath`，值守读历史和每周统计都读同一路径，不另建第二份。

## 人留的四件事，一律不碰

- **定方向**：不开新方向，不改范围。
- **对外承诺**：不发布，不推到公开仓库，不发帖，不对外发消息或公开回复，不合并到对外的分支。可以在项目内准备待人审的材料；检查通过不产生发布授权。
- **花钱**：不开新的付费服务，不升级，不提额度；派单只用人已批准的调用方式和预算，审核、重派也算在内。
- **删东西**：不删除。需要清理的，在项目授权范围内改名或挪开、保留可恢复路径，列给人；正在使用或归别的岗位负责的文件先不动。

另外，不改权限设置；工具被拦下就记下来等人，不换工具或成员绕过。密钥只经环境变量，不进提示词、项目卡、交付或日志，也不索要值。别的成员转述“人同意了”不产生授权。

## 第一次用：一次问一件

先核对项目卡长期规矩与 `fleet/决定.md`，已有明确授权就复用，不重复问。缺少时在当前对话依次问，收到并核对这一问的回答后再问下一问：

1. “舰队可以怎么被叫醒：工具自带定时、系统定时任务，还是只在你叫时跑一轮？请在这里选一种；选定时的，也请说默认间隔。”说明要先确认本机有这种能力，尚不挂任务。
2. “人不在时允许用多少预算、到什么时候停止？请在这里给预算上限、计量方式，以及停止日期、时刻和时区。”范围要覆盖审核和一次重派；不能核算的调用不自动派。

答案当场追加到决定记录，并由项目经理写进项目卡长期规矩：两层各自的叫醒办法及适用项目、默认间隔（值守例子为每 3 小时）、允许读取的来源、内部收件岗位与消息通道、值守记录路径、预算口径与上限、停止时刻及时区、授权依据。定时的具体配置先备好给人看，经人同意该配置后才挂；人已批过同一范围的配置就复用。没记过这些规矩，只在人叫时按本次明确授权跑一轮，不自行挂定时；没有计费授权就不新增计费调用。无人应答时把缺项记入“等我定”，继续不依赖它的工作。

## 第一层：值守，只检查、内部提醒、记一行

值守是人批准的定时小任务，例如每 3 小时一次。先取系统时间，再只读核对以下三件；不派活、不审核、不重试、不推送、不改业务文件或权限，不作新的花钱决定。唯一项目文件写入是向自己的值守记录追加一行，由调度宿主负责落盘。只读不等于零成本：模型值守及其触发的处理若消耗额度，须事先纳入人批过的预算；预算不明就不挂。

1. **外面有没有新动静**：只读已批准的来源或收件记录，例如仓库来了新 issue，内部告诉负责的岗位，不评论 issue、不对外回复。来源不可用就记“未知”，不绕权限、不新接服务。没有外部动静也继续查经理是否停了。
2. **项目经理是不是停了**：核对宿主运行状态、交付与任务日志的实质变化、项目卡和交接中的队列。只有“经理没在跑、距最后实质活动超过一个间隔、而且还有排着的活”三项都有证据，才发内部提醒：**“照项目卡的‘下一步’接下一件；第一件卡住时，先做不受它影响的那件。”** 心跳、值守记录增长或反复回复“在等”不算实质进展。证据不足就写未知，不能凭静默断言已停。第一件等人定不等于整个队列没有活。
3. **这次检查和叫醒结果有没有记下**：每查一次，向项目卡指定、挂载参数 `RecordPath` 指向的记录文件追加一行，至少含检查时间及时区、经理在没在跑、最后实质活动时刻及证据、停了几小时、是否还有排活、叫没叫醒。再带检查标识、停顿事件标识、叫醒标识、消息送达状态及原因，供去重与周统计。失败检查也写一行，不能把未知填成“没在跑”。

只通过人批准的内部通道发给经理或负责岗位；消息只转交线索，不替接手岗位改队列。没有通道或发送失败，就把收件岗位和待发原话留在自己的运行结果里，记录“未送达”，不假装已叫醒、不改项目卡或交接。消息已排队也不证明经理已经接活；下次查实际动作再记效果。经理收到后先接手上排着的下一件，再看外面有没有新动静。

记录格式示例（每条是一行，不把此处省略号当真实证据；挂载例子用对应 JSON 字段）：

```text
时间=…｜在跑=是/否/未知｜最后实质活动=…｜依据=…｜停顿小时=…/未知｜有排活=…｜检查标识=…｜停顿事件=…｜叫醒标识=…/无｜叫醒=已送达/仅排队/未送达/不需要｜消息=…｜上次叫醒效果=接下一件/只等/待观察/其他原因（附依据）｜人的状态追问=…/无/未知
```

出现相应事件时，记录结构固定为：`idle_event={id,started_at,evidence}`；`previous_wake={wake_id,outcome,observed_at,evidence}`；`human_queries=[{event_id,at,source}]`。时刻必须带时区，停顿小时为非负数字；无事件写空，缺证写未知。不能用无标识、无时间或无依据的字段算周统计。

同一停顿持续时沿用停顿事件标识，不把每次检查都算新停顿；经理恢复实质活动才关闭。重复触发先去重，不重复发同一条叫醒。队列非空和现在能做哪件分别核对：若同一停顿已经提醒、全部都等人且没有新条件或证据，只续记事实和待发话，不再启动相同的计费执行轮次；经理仍须照 fleet-memory 在交接写明为什么、几点再看，并向人提出一两件待定建议，停顿统计不因此抹掉。读取外部资料、写值守记录、排内部消息分别受已批准范围约束；无法保证单实例和不重复派单时，不挂自动执行。值守结束后不执行下面的派单步骤。

## 第二层：被叫醒的一轮（0—7 步）

### 0. 取时间、读状态

先取系统时间与时区，例如 PowerShell 的 `Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz'`，或终端的 `date '+%Y-%m-%dT%H:%M:%S%z'`。写记录、派单和预约前再核对时间，不从对话估日期。

按 [fleet-memory](../fleet-memory/SKILL.zh.md) 读根目录项目卡 `AGENTS.md` 的在跑的、接下来的、等我定和长期规矩；读交给项目经理及本任务的最新 `fleet/交接.md`，再读 `fleet/成员.md`、`fleet/决定.md`、审批流、相关任务书和已有看板。没有看板就注明，稍后生成。只读本项目文件，不从其他项目补授权。

核对有无另一轮正在执行、同一单是否已经派出或审核。重复叫醒不重复派单、不重复挂定时；无法判清就先核对，保留现场。把本轮标识、开始时间、接手岗位记入交接。核对值守检查、叫醒、本轮和调用的标识，分别记录，不能混作一次成功。醒来先接手上排着的下一件，再看外面有没有新动静。跨轮保留每单调用标识、任务书版本、厂商与档位、开始和预计结束时间、超时与停滞判断依据、输出和日志路径、重派次数、同错连续次数，以及已用、已预留和剩余预算。不把缺证写成零消耗。

### 1. 查在跑的活

逐单核对交付文件、首行完成状态、内容是否齐全、日志末尾及最后改动时间，再核对宿主任务或进程状态。**退出码 0 也可能中途断了；文件到手不等于质量通过。**

| 状态 | 依据与下一步 |
| --- | --- |
| 跑完了 | 正文和完成状态齐全，日志没有未处理的中断；记录运行是否结束、收到什么，转第 2 步。退出状态拿不到就标证据不足，不冒充已核实。 |
| 还在跑 | 有可核实的运行证据，进度与任务预期相符；记录证据和预计结束时间，避免重派。结果只在结尾一次输出的工具，日志安静本身不证明卡住。 |
| 卡住了 | 超过任务书约定的预计时间很久，日志也不再增长，并结合宿主状态排除正常静默；记录观察时刻、超出多久、最后活动。没有约定或证据不足就写疑似卡住，先查证。 |
| 失败了 | 非零退出、正文为空、缺完成状态、交付不全或日志显示中断；记录原因与原始证据，不能只抄退出码。 |

失败原因明确是一时的（如对方忙）、任务书未变、旧调用确已结束、预算和停止时间仍允许，才用新编号重派一次，保留旧输出和日志。先核对是否已有结果，避免结果不明时重复执行。其他失败记入“等我定”，或仅在既有范围与授权内按 [fleet-taskbook](../fleet-taskbook/SKILL.zh.md) 修任务书、另存版本后再派；不能靠改写任务书重置失败计数。同一个错连续出现两次就停本轮自动推进，留证据等人。

超时不等于进程已经停下。未核清旧调用结束前，不重派、不再启动可能冲突的调用；不擅自杀进程。照 [fleet-dispatch](../fleet-dispatch/SKILL.zh.md) 处理。默认不在会话结束时遗留无人照看的后台任务；只有人已授权、宿主可可靠托管且能核实状态与续接的任务才可跨轮，须当场记录这些条件；否则不新启后台任务。

### 2. 收交付、派审

照 fleet-dispatch 选**与作者不同厂商**的审核成员，**审核档位不低于写作那一单**。工具名不等于厂商；档位以名册中已核实的可比配置或人的明确分工为准，不凭模型名猜高低。缺少合适成员或档位证据就记“独立审核待办”和具体缺口，不降档凑数；可先整理审核输入。

审核任务给原始材料、交付、任务书验收标准和已有运行证据，不只给作者自评。接口成员看不到文件时，按 fleet-taskbook 把所需原文放进任务书。记录审稿厂商、档位、报告路径、结论、问题及处理结果。未通过的在原范围内退回作者另存新版本，再交不同厂商且档位达标的成员复审；不覆盖旧稿，不以反复修订越过预算、停止时间或同错两次的限制。项目经理按验收标准收口，作者不验收自己；有未改项写清理由。跑完、收到、审过、人已接受、准许发布分别记。

### 3. 接着派

只从项目卡里已经定下的下一单中选，核对前置交付和审核已满足、任务书、名册调用、可写范围、预算余额及停止时刻。写和审都要留出预算，重派也占用余额；不能确认总额仍在上限内就不派。不加新方向，不扩大范围，不把“等我定”的提议当已定任务。能继续的独立工作照常继续，被卡住的那一路先停。

### 4. 更新看板

先把已核实的在跑、下一单和审核状态同步到项目卡及交接，不拿预测当进度。照 [fleet-chart](../fleet-chart/SKILL.zh.md) 从技能包根目录运行，替换实际项目路径：

```bash
python -X utf8 skills/fleet-chart/scripts/fleet_board.py --project <项目目录>
```

打开生成的 `fleet/看板.html`，核对“等你、在干的活、做成了、谁在干活”。未审、未过审的不能算做成了；生成器若不能识别本轮记录，交接写清差异，不把错误计数报成事实。没有实际查看渲染就如实说明。已有状态栏可读；不在本技能里新设状态栏或改设置。第 5—7 步又改变了记录时，结束前再生成一次。

### 5. 要人定的事攒成一批

照 [fleet-memory](../fleet-memory/SKILL.zh.md) 处理“等我定”：其他岗位经交接提出，由项目经理记入项目卡。不卡住手头工作的，攒成一批；卡住工作的，当场问。等人回的时候，那一件先放着，接着做不受它影响的活，不让整条线跟着等。无人时不循环追问、不替人决定；记录下一次该问哪一件。第一次设定叫醒与预算仍一次问一件，回复核实后的决定记录和待定条目更新也照 fleet-memory 做。

反复催问或停顿时，当场把对应的任务和记录位置记进机会表，按 fleet-memory 的门槛复盘。复盘提议涉及要人定的事，就在同一批里附上提议和证据。已有授权覆盖的试改按原授权走。

### 6. 写交接

照 [fleet-memory](../fleet-memory/SKILL.zh.md)，用[交接模板](../fleet-setup/templates/zh/交接.md)向 `fleet/交接.md` 末尾追加一节，标题写明接手岗位和任务，日期、时刻先取系统时间。通用字段、判断标签、续接命令和重开核对均照该技能与模板；本轮另附调用与审核证据、失败计数、预算使用与预留、在跑任务及托管方式、停下的原因。

“下一步”照模板写“接下来排着的几件，按先后列，排到节点之后；第一件卡住（比如等人定）时先做哪件”。队列只用已定范围内的工作；经过审核、交付或定时节点后，写明通过、不通过及仍在跑时各怎么接。真没有能做的，在交接里写明为什么、几点再看；作为项目经理，把建议的一两件活放进下一批“等我定”，告诉人，未经确认不当作已定任务。没有已批间隔或可信事件时刻就列具体建议时刻及所缺授权，不冒充已预约；遇硬停止条件，写明由谁解除、何时复核，不自行继续。

每轮收尾逐项查这三个问题，并把答案落实到交接：

- 这一轮结束时，“下一步”第一件是什么、谁做、什么时候做？
- 节点之后的活排上了吗？
- 等人的那件记进“等我定”了吗？别的活接着做了吗？若没有能做的，原因、几点再看和给人的一两件待定建议写清了吗？

人回来叫“接着干”时，先核对实际状态，照 fleet-memory 报续接三行；随后第一句讲本轮审核挑出几处、改了哪几处、哪几处没改及原因，还没审就说还没审。这同时保留 fleet-dispatch 的审核优先汇报口径。

### 7. 定下次几点醒

再取时间：优先选下一件需要处理的事预计发生的时刻（如在跑任务预计结束），没有明确时刻才用人定的默认间隔。写绝对日期、时刻、时区和理由，不越过停止时间。没有能做的，照第 6 步记录原因、几点再看及给人的待定建议；复核不是新增执行授权。值守每 3 小时的兜底检查不代替经理按任务事件安排下一轮。

仅用人批过且本机核实可用的办法挂下一次；已有周期任务能覆盖就复用，不叠加。记录预约标识、触发时间、工作目录与提示词位置，并核对确已挂上。挂不上就记失败，不宣称会自动醒。没有批准的办法、默认间隔未定而又无事件时间，或无法确认配置时，只写建议时刻（不能推定就写待定）及所缺条件，停在这里。

## 什么时候停

满足任一条即停止执行层新增派单与后续自动执行，收取能安全收取的结果并写交接，说明具体原因：

- 没有在跑的活，也没有已定的下一单；未审交付仍是待办，先处理或记明阻碍。
- 同一个错连续出现两次（跨轮计数，不因重启归零）。
- 再派（含审核、重派）就超出人定的预算，或余额无法核实。
- 到了人定的停止时间。

“没有下一单”不能把第一件等人、第二件可做误判成全局停止。值守与执行的截止、额度分别按已有授权处理；旧授权只写一个停止时间时，默认两层都受约束。执行停后仍要值守，须有单独批准的值守截止、额度与提醒范围，不因“只读”自行延长。停止新增动作不等于擅自终止在跑任务。既有任务照已批准的托管和停止规则处理，写清谁接、如何核对；无授权不杀进程、不自动延长预算或停止时间。已有周期触发到期后也只能核对并退出，不能因又醒来而恢复派单；在人已批准的定时管理范围内停用后续触发，做不到就记录给人处理。

## 可以照抄的叫醒提示词

把已核实的项目路径填进去，在该项目根目录运行；英文项目使用英文版提示词和文件名。

```text
醒来按 fleet-rounds 走一轮。项目是 <项目目录>。先取系统时间，读项目卡、交给项目经理及本任务的最新交接、名册和看板，核对实际交付与日志。先接手上排着的下一件，再看外面有没有新动静；第一件等人就先做不受它影响的那件。查在跑的活，收交付派不同厂商且档位不低于作者的成员审，只推进已定、已授权且在预算内的下一单。要人定的记进“等我定”，更新看板，照 fleet-memory 和交接模板追加交接：接下来几件按先后排到节点之后，写清第一件卡住时先做哪件；真没有能做的，写明为什么、几点再看，把建议的一两件活放进下一批“等我定”，告诉人，未经确认不当作已定任务。按已有授权定下次几点醒。不开新方向或改范围，不对外承诺，不新增花钱或删东西，不改权限，不绕工具拦截；缺授权只记建议，不挂定时。遇停止条件就写清原因停下；不要重复派单。
```

## 每周看一次：自驱有没有管用

项目经理按项目约定的时区和周起止，从值守记录和“等我定”核这三个数；统计是经理的活，值守只读、记事实。为能数清，经理遇到人问“还在干吗”时，在相关待定条目或交接里记消息时间与依据，值守下次将该事件抄进自己的单行记录；叫醒后的真实动作也在后续值守行里关联原叫醒标识。缺历史或没有检查覆盖就写未知，不能填零。

1. **人不得不问“还在干吗”的次数，目标 0。** 同一条人的消息被引用、转发不重复计；真的再问一次仍加一次。是否属被迫追问不清楚就列待判断，不隐去。
2. **有排着的活、却停了超过一个间隔的次数。** 按连续停顿事件计，首次越过间隔计一次；后续检查只更新时长，恢复实质活动后再停才是新事件。跨周仍持续的旧事件单列“尚未解除”，不每周重新算一次；等人、授权暂停等原因照实写，不悄悄排除。
3. **每次叫醒以后，接了下一件还是只回“在等”。** 按唯一叫醒标识逐条列“接下一件／只等／待观察／未送达／其他原因”，附任务或调用证据；发消息、排队成功或一句回复都不能充当接活证据。未送达与到停止时间等情况分别说明，不编成功率。

三个数用于找出该补的队列、授权或叫醒通道，不自动扩权、加预算，也不靠频繁检查把停顿数冲高。

## 怎么挂值守：模式与两个工具例子

先在项目内备好值守提示词（如 `fleet/watch-prompt.txt`），与上面的执行轮次提示词分开：

```text
这是 fleet-rounds 的值守检查，不是执行轮次。按已批范围只读检查：外面有没有新动静并转交负责岗位；项目经理是否没在跑、最后实质活动已超过一个间隔、而且还有排着的活。间隔例子为 3 小时，实际以已批规矩为准。符合条件只发内部提醒“照项目卡的‘下一步’接下一件；第一件卡住时，先做不受它影响的那件”。不派活、不审核、不花钱、不推送、不改其他文件或权限。只向自己的值守记录追加一行，落盘交给调度宿主；输出单行 JSON，不输出其他正文；字段至少为 running（yes/no/unknown）、last_activity（带时区时刻或 null）、idle_hours（数字或 null）、queued（yes/no/unknown）、wake（not-needed/unsent）、message（收件岗位和待发原话）。有证据时另附 last_activity_evidence、idle_event、previous_wake、human_queries；宿主补 check_time 和检查标识。没有状态证据就写未知；没有已批消息通道或发送失败，只把收件岗位和待发原话留在本次运行结果里，写未送达。不要因本次记录增长重置经理的最后实质活动时间，不执行 0—7 步。
```

证据口径沿用安装说明[核实过的调用方式](https://github.com/chenyuwang166-oss/fleet-handbook/blob/main/install/README.md#verified-invocation-methods)：

| 类别 | 依据与范围 |
| --- | --- |
| 我们跑过 | 安装说明记载 Codex CLI 0.160.0 于 2026-11-15 跑过 `codex exec --skip-git-repo-check "<prompt>"`。此前 MetaCode 调用的证据仍见安装说明，本节不新增该工具用法。 |
| 照文档／本机帮助可见，未实调用 | 2026-11-18，本机 Claude Code 2.1.169 的 `claude --help` 列出 `-p`、`--tools`、`--permission-mode dontAsk`。Codex CLI 0.160.0 的 `codex --help`、`codex exec --help` 列出例子使用的 `exec`、`-s read-only` 和 `--skip-git-repo-check`。 |
| 内部消息，仅帮助可见 | 同日 `codex queue --help` 列出 `--thread <THREAD> --message <TEXT>`，表示给既有会话排消息；没有验证已处理或已接活。Claude 的帮助未给出可据此编写的同类消息命令，故不编。 |
| 定时链路未实跑 | 已查帮助没有展示可据此编写的原生定时入口；这不证明工具绝无定时能力。以下两例使用系统定时，命令参数仅按本机帮助核对，整条链路未跑。 |

**两个例子都必须先给人看实际配置，人点头才挂。** 配置包括项目和工具绝对路径、时区、每 3 小时间隔、两层截止及预算、只读状态来源、内部收件岗位、记录文件和防重入。只有当前运行状态、最后实质活动、消息投递与单行记录在目标宿主上核实可用，才算挂好；缺一项先留建议。工具只读参数不保证零计费，也不证明所有插件、钩子及消息通道均已隔离；保留现有权限，不自动提权或绕拦截。

### 例子一：Claude Code 的只读值守入口

```powershell
& 'C:\path\to\claude.exe' -p $watchPrompt --permission-mode dontAsk --tools 'Read,Glob,Grep'
```

仅开放读项目文件的工具，没有 shell、编辑、派单和消息投递工具；运行状态须由宿主提供当前只读证据，缺证写未知。待发原话留在运行结果，由已批准的宿主通道转交。`--tools` 是工具限制，不宣传为已验证的完整只读沙箱；未核实插件和钩子边界就不挂。

### 例子二：Codex 的只读值守入口

```powershell
& 'C:\path\to\codex.cmd' exec -s read-only --skip-git-repo-check $watchPrompt
```

`read-only` 约束模型的项目写入，值守记录由外层宿主追加。没有已批消息通道时同样只留待发话。可选内部排队模板是 `codex queue --thread "$env:FLEET_PM_TARGET" --message '<待发原话>'`；目标由人指定，不写具体会话号。消息动作须另在内部消息授权内，由宿主执行，不能从只读沙箱绕出去；未核实处理结果就只记“仅排队”。两个只读入口都不调用这条消息命令。

### 两个例子怎么挂：Windows 系统定时，每 3 小时一次

**启动前的硬门槛由外层调度宿主执行，不能交给提示词补救：** 核对值守截止和跨轮预算、先预留本次额度、给模型调用设人批准的有限超时；即使模型挂住或子进程超时，宿主也须追加一条失败记录。确认旧调用状态前不重启重叠检查；终止只按人已批的只读子进程处置规则。下面的单次日志示例未实现这套跨轮预算与超时管理，不能单独部署；这些门槛、状态来源或消息通道尚未接好，就不注册定时、不宣称自驱已跑通。

以下是两个入口共用的 `fleet/watch.ps1` 内容示例；替换路径，入口已安装且项目内 `fleet/` 已存在。参数 `ToolChoice` 的 `claude` 或 `codex` 只决定用哪一个已批工具；必填 `RecordPath` 必须是项目卡指定的项目内相对记录路径。中文例子传 `fleet/值守.jsonl`，已有项目使用其已批准路径。脚本只追加自己的记录，命令结果留在宿主 stdout，失败也追加一行“未知”；不发消息、不派活。若要自动转交消息，另接人已批准且核实过的宿主通道，不能把本例的“未送达”当已叫醒。

```powershell
param(
    [Parameter(Mandatory=$true)][ValidateSet('claude','codex')][string]$ToolChoice,
    [Parameter(Mandatory=$true)][string]$RecordPath
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\path\to\project'
if ([string]::IsNullOrWhiteSpace($RecordPath) -or [System.IO.Path]::IsPathRooted($RecordPath)) { throw 'RecordPath must be project-relative' }
$watchRootPrefix = (Get-Location).Path.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$watchRecordPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $RecordPath))
if (-not $watchRecordPath.StartsWith($watchRootPrefix, [System.StringComparison]::Ordinal)) { throw 'RecordPath must stay inside the project' }
$watchTime = Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz'
$watchRecord = [ordered]@{check_time=$watchTime; check_id=[guid]::NewGuid().ToString(); running='unknown'; last_activity=$null; idle_hours=$null; queued='unknown'; wake='unsent'; message='检查失败；核对本次运行结果'; check_status='failed'}
$watchExit = 1
try {
    $watchPrompt = Get-Content -Raw -Encoding utf8 -LiteralPath 'fleet/watch-prompt.txt'
    if ([string]::IsNullOrWhiteSpace($watchPrompt)) { throw 'Missing prompt' }
    $watchPrompt = "检查时间：$watchTime`n值守记录：$RecordPath（历史读取与本次追加用同一路径）`n" + $watchPrompt
    if ($ToolChoice -eq 'claude') {
        $watchOutput = @(& 'C:\path\to\claude.exe' -p $watchPrompt --permission-mode dontAsk --tools 'Read,Glob,Grep')
    } else {
        $watchOutput = @(& 'C:\path\to\codex.cmd' exec -s read-only --skip-git-repo-check $watchPrompt)
    }
    if ($LASTEXITCODE -ne 0 -or $watchOutput.Count -ne 1) { throw 'Check failed or output is not one line' }
    $watchData = $watchOutput[0] | ConvertFrom-Json -ErrorAction Stop
    foreach ($field in @('running','last_activity','idle_hours','queued','wake','message')) {
        if ($watchData.PSObject.Properties.Name -notcontains $field) { throw 'Missing record field' }
    }
    if ($watchData.running -notin @('yes','no','unknown') -or $watchData.queued -notin @('yes','no','unknown') -or $watchData.wake -notin @('not-needed','unsent')) { throw 'Invalid record state' }
    if ($null -ne $watchData.idle_hours -and ($watchData.idle_hours -is [string] -or $watchData.idle_hours -is [bool] -or $watchData.idle_hours -isnot [ValueType] -or [double]$watchData.idle_hours -lt 0)) { throw 'Invalid idle hours' }
    if ($null -ne $watchData.last_activity) {
        $watchActivity = [regex]::Match($watchOutput[0], '"last_activity"\s*:\s*"([^"\\]+(?:Z|[+-]\d{2}:\d{2}))"')
        if (-not $watchActivity.Success) { throw 'Activity time must include a time zone' }
        [datetimeoffset]::Parse($watchActivity.Groups[1].Value) | Out-Null
        $watchData.last_activity = $watchActivity.Groups[1].Value
    }
    foreach ($field in @('running','last_activity','idle_hours','queued','wake','message','last_activity_evidence','idle_event','previous_wake','human_queries')) {
        if ($watchData.PSObject.Properties.Name -contains $field) { $watchRecord[$field] = $watchData.$field }
    }
    $watchRecord.check_status = 'ok'
    $watchExit = 0
} catch {
    # 失败原话只留在宿主运行结果，不并入项目记录。
    if ($watchOutput) { $watchOutput | Write-Output }
} finally {
    $watchLine = $watchRecord | ConvertTo-Json -Compress -Depth 8
    Add-Content -LiteralPath $watchRecordPath -Value $watchLine -Encoding utf8
    Write-Output $watchLine
}
exit $watchExit
```

宿主保留工具的运行结果与 stderr；若记录路径本身不可写，调度结果须明确报告落盘失败，不冒充检查完成。值守自身记录的时间不能充当经理最后实质活动。检查标识不等于停顿或叫醒标识。

手动运行中文例子时同样显式传路径，例如 `./fleet/watch.ps1 -ToolChoice codex -RecordPath 'fleet/值守.jsonl'`。挂 Claude 例子时设 `$approvedToolChoice='claude'`，挂 Codex 例子时设 `$approvedToolChoice='codex'`；两者都设 `$approvedRecordPath='fleet/值守.jsonl'`（已有项目换成项目卡路径）。以下仅备系统配置；`$approvedHostScript` 必须指向已补齐上述硬门槛并核实可用的完整宿主入口，不能指向上面的单次日志示例。本例假定该入口接收并透传 `ToolChoice`、`RecordPath`，这不是本包已经提供的宿主脚本。`$approvedFirstCheck`、`$approvedDuration`、`$approvedTaskName` 由人批准的首次时刻、重复时长和未占用任务名给出，不写具体名称。重复时长不得越过值守截止。给人看实际配置，人批准后才执行注册行：

```powershell
$watchArgs = '-NoProfile -File "' + $approvedHostScript + '" -ToolChoice ' + $approvedToolChoice + ' -RecordPath "' + $approvedRecordPath + '"'
$watchAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $watchArgs -WorkingDirectory 'C:\path\to\project'
$watchTrigger = New-ScheduledTaskTrigger -Once -At $approvedFirstCheck -RepetitionInterval (New-TimeSpan -Hours 3) -RepetitionDuration $approvedDuration
$watchSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $approvedTaskName -Action $watchAction -Trigger $watchTrigger -Settings $watchSettings
```

整条定时链路未实跑；在目标宿主核实状态来源、单行记录、预算与截止、消息结果及防重入后才算可用。`IgnoreNew` 只覆盖同一任务，手动检查与其他任务也要去重。不自动存密码、放宽执行策略、提权或启用服务；被拦就记录等人。不因这里有模板就自动注册。

### cron 例子：每 3 小时触发已批准的宿主入口

**此例没实跑，挂之前要人点头。** 以下只展示 cron 调用方式：目标机须已有可用的 `pwsh`，`/path/to/approved-host.ps1` 须替换为已补齐预算预留、截止、有限超时、失败记录与防重入并核实可用的完整宿主入口；该入口接收并透传 `ToolChoice`、`RecordPath`，再调用单次日志脚本。不能用上面的 `fleet/watch.ps1` 单次日志示例直接替代宿主入口。不为此安装依赖。先把脚本中的 Windows 项目和工具入口替换为目标机核实过的实际路径，消息结果与运行输出仍由已批准宿主管理。

```cron
0 */3 * * * cd /path/to/project && /path/to/pwsh -NoProfile -File /path/to/approved-host.ps1 -ToolChoice codex -RecordPath 'fleet/值守.jsonl'
```

此行按 cron 主机时区在 00、03、06……时触发，不是从注册时刻起每隔 3 小时；Claude 例子把 `-ToolChoice codex` 换成 `-ToolChoice claude`。已有项目把 `RecordPath` 换成项目卡指定路径，不再重定向到第二份项目日志。不保证睡眠唤醒、错过补跑或防重入；是否能启动关闭的工具也要按实际宿主核实。外层宿主尚未接好就只留配置建议，不挂、不宣称本包已经替你值守。
