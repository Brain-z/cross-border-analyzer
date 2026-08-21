# 第三方组件说明

## fastmoss-rpa（社区技能）

- 来源：[liangdabiao/fastmoss-rpa-skills](https://github.com/liangdabiao/fastmoss-rpa-skills)
  （作者：liangdabiao，Linux.do 社区）
- 获取日期：2026-08-21
- 用途：FastMoss 全部 7 个模块的榜单抓取 / 筛选 / 市场 API 拉取，驱动用户已登录浏览器（BrowserSkill/bsk）
- 位置：`scripts/vendor/fastmoss-rpa/`（仅打包 scripts/ 与 references/，未含原仓库的 .claude 技能目录）
- 本地适配：仅修改 `bridge_browserskill.py` 中 bsk 可执行文件路径的查找方式（跨平台），
  其余抓取逻辑保持上游原样
- 许可证：**该仓库未标注明确的开源许可证（未发现 LICENSE 文件）**。
  当前仅限个人本地使用；若需公开发布、分发或商用，请先联系原作者获取授权。

## BrowserSkill（bsk）

- 来源：[Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill)
- 用途：浏览器桥接工具，复用用户已登录的 Chrome/Edge 登录态
- 安装方式见插件内 `skills/fastmoss-fetch/SKILL.md`
