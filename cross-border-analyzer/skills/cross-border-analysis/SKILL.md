---
name: cross-border-analysis
description: "分析跨境商品数据（FastMoss / TikTok Shop）：解析用户自然语言需求（榜单、时间、地区、品类），抓取或导入数据，按评分模型打分排名，输出分析报告、交互仪表盘和 Excel 排名表。用户要求分析美国时尚配饰等品类的 TikTok 爆品、榜单、选品机会时使用。"
---

# 跨境商品数据分析（总控）

本 skill 是插件的唯一入口。收到需求后按以下流程执行，产物统一写入 `output/<时间戳>/`。
执行前先读取插件根目录的 [rules.md](../../rules.md)，按其中的前置规则决定抓取范围、
筛选条件、详情页补充范围和输出；用户没改的项用默认值。

## 流程

0. **读取前置规则**：`rules.md` 中的筛选条件（价格/佣金/销量下限）、详情页补充 Top N、
   标签阈值、抓取参数在本轮分析中生效。

1. **解析意图**：把用户描述翻译成结构化参数，再叠加 `rules.md` 的规则：

   ```text
   { 模块: products, 榜单: 销量榜, 地区: US, 品类: 时尚配件, 时间: 月榜, 数量: 100 }
   ```

   - 地区：中文名与 ISO 代码互认（美国 ↔ US，泰国 ↔ TH）；
   - 时间："近 7 天" → 日榜；"本周 / 周榜" → 周榜；"月榜" → 月榜；
   - 数量："Top 100" → 按榜单页实际行数（约 10 条/页）折算页数；
   - 品类：查 [references/categories.md](../../references/categories.md) 的映射，匹配不到时用模糊词搜索；
   - 用户没说的参数用默认值：平台=FastMoss、时间=月榜、地区=美国、数量=50（可被 rules.md 覆盖）。

2. **获取数据**：

   - 需要 FastMoss 榜单 → 调用 `fastmoss-fetch` skill 抓取（复用社区 fastmoss_rpa.py；bsk 优先 → 内嵌浏览器 → 手动导入 `data/import/`）；
   - 用户直接给了 CSV/Excel → 跳过抓取，进入清洗；
   - 抓取或导入结果统一为 CSV（UTF-8 BOM），存到 `data/raw/`。

3. **清洗**：运行 `scripts/normalize.py`，把原始列映射为规范列（排名、商品名、价格、周期销量、周期GMV、总销量、佣金率、上架天数、店铺、品类、评分、评论数等）。字段别名表见 [references/fastmoss-fields.md](../../references/fastmoss-fields.md)。无法映射的列保留原样并提示。

4. **品类落地**：枚举数据中实际出现的品类（category 列去重值），后续分组、评分竞争度、仪表盘筛选一律以真实类目为准；种子映射表仅用于抓取前筛选参数。

5. **评分**：运行 `scripts/score.py`，默认权重见 [references/scoring.md](../../references/scoring.md)。每个商品输出市场热度分、可做性分、综合潜力分，并打异常标记（暴涨新星 / 价格战红海 / 高佣爆款）。

6. **输出**：

   - `scripts/report.py` → `report.md`（需求复述、市场概览、Top 榜单、选品建议、风险提示）；
   - `scripts/dashboard.py` → `dashboard.html`（交互图表 + 筛选器，纯本地可打开）；
   - 评分后的 CSV/XLSX 排名表一并放入 `output/`；
   - 把报告要点和产物路径汇总给用户。

7. **详情页补充**（`rules.md` 第 3 节，按需执行）：对每个榜单综合潜力 Top N 的商品，
   用 `browser-skill`（bsk）打开 FastMoss 商品详情页，提取成交渠道占比
   （商品卡 / 店铺自营号 / 达人带货）和带货达人数，按 `rules.md` 阈值打
   "达人依赖型 / 自然流量型"标签，写回评分表；然后重新生成报告与仪表盘
   （Top 榜增加占比列，报告增加"流量结构"小节）。此步骤不写自定义抓取脚本。

## 约定

- 原始数据不改字段，可回溯；
- 分析以当前抓取/导入的数据为准，不编造指标；
- 用户要求"分析"但没提数据 → 先问数据来源（FastMoss 榜单 / 现有文件）；
- 输出目录：`output/<yyyy-mm-dd_hhmm>/`，避免覆盖历史结果。
