---
name: cross-border-analysis
description: "分析跨境商品数据（FastMoss / TikTok Shop）：解析用户自然语言需求（榜单、时间、地区、品类），抓取或导入数据，按评分模型打分排名，输出分析报告、交互仪表盘和 CSV 排名表。用户要求分析美国时尚配饰等品类的 TikTok 爆品、榜单、选品机会时使用。"
---

# 跨境商品数据分析（总控）

本 skill 是插件的唯一入口。收到需求后按以下流程执行，产物写入 `output/` 下按榜单命名的目录。
执行前先读取插件根目录的 [rules.md](../../rules.md) 取默认值；**用户本次描述优先，
rules.md 只兜底未指定的参数**——国家、品类、榜单、时间、数量都可由用户临时指定，不写死。

> 注：详情页补充（成交渠道占比 / 带货达人数）暂缓，不纳入当前流程。

## 流程

0. **读取前置规则**：`rules.md` 提供默认值（筛选条件、抓取参数）；先用用户本次需求
   覆盖对应参数，再按剩余默认值执行。

1. **解析意图**：把用户描述翻译成结构化参数，再叠加 `rules.md` 的规则：

   ```text
   { 模块: products, 榜单: 销量榜, 地区: US, 品类: 时尚配件, 时间: 月榜, 数量: 100 }
   ```

   - 地区：中文名与 ISO 代码互认（美国 ↔ US，泰国 ↔ TH）；
   - 时间："近 7 天" → 日榜；"本周 / 周榜" → 周榜；"月榜" → 月榜；
   - 数量："Top 100" → 按榜单页实际行数（约 10 条/页）折算页数；
   - 品类：查 [references/categories.md](../../references/categories.md) 的映射，匹配不到时用模糊词搜索；
   - 用户没说的参数用默认值（rules.md）：平台=FastMoss、地区=美国、类目=时尚配件、
     时间=月榜、数量=50；用户说了任何参数（如"英国""美妆个护""达人榜"）都以用户为准。

2. **获取数据**：

   - 需要 FastMoss 榜单 → 调用 `fastmoss-fetch` skill 抓取（商品榜用 `scripts/fastmoss_filtered.py`，
     其余榜单复用社区 fastmoss_rpa.py；bsk 优先 → 内嵌浏览器 → 手动导入 `data/import/`）；
   - 用户直接给了 CSV/Excel → 跳过抓取，进入清洗；
   - 抓取或导入结果统一为 CSV（UTF-8 BOM），存到 `data/raw/`。

3. **清洗**：运行 `scripts/normalize.py`，把原始列映射为规范列（排名、商品名、价格、周期销量、周期GMV、总销量、佣金率、上架天数、店铺、品类、评分、评论数等）。字段别名表见 [references/fastmoss-fields.md](../../references/fastmoss-fields.md)。无法映射的列保留原样并提示。

4. **品类落地**：枚举数据中实际出现的品类（category 列去重值），后续分组、评分竞争度、仪表盘筛选一律以真实类目为准；种子映射表仅用于抓取前筛选参数。

5. **评分**：运行 `scripts/score.py`，默认权重见 [references/scoring.md](../../references/scoring.md)。每个商品输出市场热度分、可做性分、综合潜力分，并打异常标记（暴涨新星 / 价格战红海 / 高佣爆款）。

6. **输出**：

   - `scripts/report.py` → `report.md`（需求复述、市场概览、Top 榜单、选品建议、风险提示）；
   - `scripts/dashboard.py` → `dashboard.html`（交互图表 + 筛选器，纯本地可打开）；
   - 评分后的 CSV 排名表一并放入 `output/`；
   - 把报告要点和产物路径汇总给用户。

## Token 预算（强制，违反等于失败）

本插件的 CSV / HTML 产物体积很大（scored.csv 约 100–160K，dashboard.html 约
300K，读进对话一次就是数万 token）。必须遵守：

- **禁止读全文**：不得把 `data/raw/*.csv`、`normalized.csv`、`scored.csv` 整份
  读进对话。需要核对时只用 shell 命令取样本：`wc -l <文件>`、`head -n 5`、
  `tail -n 5`、`awk -F, 'NR==1{print}'`。
- **dashboard.html 只生成、不读取**：文件内嵌全量数据，任何情况下不得读入
  对话或把内容贴给用户。
- **汇报只出摘要**：对用户只给 report.md 的要点 + 产物路径 + Top 10 简表，
  禁止逐行搬运商品数据。
- **数据探查走脚本**：统计、Top 榜、品类分布一律由 normalize/score/report
  产出，禁止手工逐条翻 CSV。
- **详情页 / 逐条抓取默认禁止**（token 杀手）：仅当用户明确要求且数量
  ≤ 20 条时才做，且只保留必要字段。
- **排错一次到位**：按 fastmoss-fetch 的排错清单逐项检查后一次执行，
  禁止反复小步重试、逐页打印表格内容。
- 用户说"给我全部数据 / 前 500 条"时：产物落盘给路径，最多展示前 10 条样本，
  不把整份数据贴进对话。

## 约定

- 原始数据不改字段，可回溯；
- 分析以当前抓取/导入的数据为准，不编造指标；
- 用户要求"分析"但没提数据 → 先问数据来源（FastMoss 榜单 / 现有文件）；
- 输出目录：`output/<榜单>/`（如 `output/products_sales/`），同榜单重跑会覆盖，历史结果另存。
