# Contributing

Contributions to skills, templates and scripts are welcome. Please describe the problem, the behavior after your change and the commands used to verify it. Do not submit personal information, credentials, internal material or real business material without authorization.

Ideas and suggestions are welcome too: open an Issue and describe what you were trying to do.

The installer and the skills' scripts use only the Python standard library. Keep them compatible with Python 3.9 and later. The self-check page's optional browser check also needs Playwright and Pillow; see [levels/README.md](levels/README.md). After making changes, run this command from the repository root:

```bash
python -m unittest discover -s tests
```

For changes to organizational principles or the division of responsibilities, also explain the use case and differing views.

# 参与贡献

欢迎改进技能、模板和脚本。请说明要解决的问题、改动后的行为和验证命令。不要提交个人信息、凭据、内部资料或未经授权的真实业务材料。

安装脚本和技能里的脚本只使用 Python 标准库，保持 Python 3.9 以上兼容。自测页那项可选的浏览器检查另需 Playwright 和 Pillow，见 [levels/README.md](levels/README.md)。修改后在仓库根目录运行：

```bash
python -m unittest discover -s tests
```

涉及组织原则或分工的修改，请同时说明使用场景和不同意见。
