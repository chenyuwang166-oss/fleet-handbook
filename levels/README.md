# AI 舰队分级自测

9 道题，按近期真实工作作答。测的是做法，不是能力。中文、英文可以随时切换，已选答案保留。结果对照五级工作方式，并给出下一步的技能和手册章节。

## 本地打开

直接用浏览器打开 [index.html](index.html)。不用安装依赖，不用启动服务，断网也能作答、切换语言、下载卡片。页面的 HTML、样式、题库和计分代码都在这一个文件里。

答案仅保存在当前页面的内存里。刷新或关闭页面就清空。不上传，不写 cookie，不使用浏览器持久存储，也没有统计脚本。

结果页可下载两种 PNG：竖版 1080 × 1350，横版 1200 × 675。手机没有触发下载时，可以长按下载按钮下方生成的图片保存。

卡片还会从这九道题的答案中选出最多三项已有做法，再去掉等级标题或卡片陈述里已经写到的项，不另补位。例如 L5 只保留“写审分开”；全都重复时不显示特征行。没有对应答案的特征不会显示，不推算厂商或岗位数量，不加题。卡片随当前语言显示“九道题，看看你现在怎么分工”或“Nine questions on how you work”。

## 修改题目

[questions.json](questions.json) 是编辑源。每道题的 `id`、选项的 `id` 用于计分；`title` 和 `label` 的 `zh`、`en` 分别是中文和英文。只改文字时保留这些 ID。

`levels` 中的 `requires` 是每级必需的做法，`minScore` 是这些做法最低分的总和。高分不能补偿缺失的关键做法。L4 须有跨厂商分工和独立互审；L5 还须有常设部门、工作记忆、经两级审核并按审批表定下的行为条款，以及人在组织内的职责。全空、漏答或非法答案不判级。题目和规则用于自测，尚未经读者样本校准。

`summary` 只用于结果页，卡片不显示建议句。卡片的大字使用原有 `title`，另以 `card` 的中英文陈述说明这一级的工作方式。`next`、`skills`、`chapters` 对应下一步、技能链接和手册章节编号。L1、L2 对应第1章、第2章，L3 对应第2章，L4 对应第1章、第3章、第5章，L5 对应第3章、第4章、第5章。章节链接随当前语言指向 `handbook/zh/` 或 `handbook/en/`。

编辑后，在本目录运行：

```powershell
node tests/sync-data.mjs
node --test tests/*.test.cjs
```

同步脚本把题库和 [计分源文件](tests/scoring.cjs) 写回 `index.html`。浏览器不请求 JSON，因此单独复制 HTML 也能使用。测试比较内嵌内容与编辑源，防止改题后忘记同步。计分测试只用 Node 内置模块，无需安装包。

测试覆盖五级典型做法、四条阈值的两侧与恰好达线、门槛反例、空答案、缺答、非法答案、双语一致性和卡片特征的答案依据。另有离线浏览器检查；本机已有 Python、Playwright、Chromium 和 Pillow 时运行：

```powershell
python -X utf8 -B tests/browser-smoke.py
```

检查会实际操作页面、下载 PNG，并在 `tests/artifacts/d2/` 写入截图、五级中英文竖横版共二十张卡片和检查结果（`tests/artifacts/d2/browser-results.json`，跑完检查才生成，仓库里不带）。L5 样图为 `sample-L5-portrait-zh.png`、`sample-L5-landscape-zh.png`，英文对应文件名以 `en` 结尾。可用环境变量 `FLEET_LEVELS_ARTIFACTS` 指定其他输出目录。测试脚本会关闭浏览器，无需常驻服务。

## 上线

挂在主仓库的 GitHub Pages 上，地址是 https://chenyuwang166-oss.github.io/fleet-handbook/levels/ 。仓库转公开以后，在仓库设置里启用 Pages，站点来源选默认分支的根目录，再验证这个地址能打开本页。

页面与卡片使用 `../assets/src/metask-vi.css` 的官网配色和中英文字体栈；样式内嵌，不请求外部字体。卡片和页面页脚随语言显示“元任务实验室 MeTask AI Lab”或“MeTask AI Lab”。

卡片底部写仓库地址 `github.com/chenyuwang166-oss/fleet-handbook`，放不下时自动缩小字号。以后仓库地址要改，就改 `index.html` 里两处卡片绘制文本和 `tests/browser-smoke.py` 里的断言，再跑计分与浏览器检查，确认两种画幅、两种语言都没有溢出。卡片下载保留当前语言。

本目录完成本地交付；仓库创建、Pages 设置和对外发布由发布负责人执行。
