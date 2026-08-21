# FastMoss 品类大盘多市场对比报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{top_per_region_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample} | **数据源**: `{source_files}`

---

## 一、各市场 Top 5 品类（按销售额）

| 市场 | Top 5 品类 (含销售额) |
|---|---|
{top_per_region_table}

**核心洞察**: _（看每个市场的"主战场"：哪些品类在该市场最热；不同市场的差异 = 选品/扩张机会）_

---

## 二、高增长品类排行（按 MoM 增速）

| 品类 | 市场 | 增速 |
|---|---|---|
{growth_table}

**洞察方向**：
- 高增速 + 大体量 = 当前爆款（红海竞争激烈）
- 高增速 + 小体量 = 蓝海机会（提前布局）
- 负增速品类 = 衰退期，避免库存压力

---

## 三、各市场品类全景交叉

| 市场 | 品类总数 | Top 10 品类 |
|---|---|---|
{region_crosstab_table}

**结构性洞察方向**：
1. 哪些品类在多市场都进入 Top 10（全球通用品类）
2. 哪些品类是区域特化（如东南亚食品饮料 vs 美区穆斯林时尚）
3. 市场成熟度信号：Top 10 集中度高的市场 = 头部效应强

---

## 四、跨市场重复品类（多市场 Top 5 同时出现）

{cross_region_repeats}

**洞察方向**：
- 同时进入多市场 Top 5 的品类是真正的"全球性"赛道
- 优先在这些品类做跨境多市场布局（供应链复用）

---

## 五、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **跨境商家** | _（优先跨市场 Top 5 品类；找高增速小体量品类作为新切入）_ |
| **品牌方** | _（按目标市场头部品类做品牌定位）_ |
| **投资人** | _（关注多市场同步高增长的品类 = 大赛道信号）_ |

---

## 报告复现命令

```bash
# Step 1: 拉取每个市场的行业格局数据
python <path-to-skill>/scripts/fetch_distribution.py \\
    --region US,ID,TH,MY --time month \\
    --out <out-dir>/categories_by_region.csv

# Step 2: 生成报告
python <path-to-skill>/scripts/analyze.py \\
    --distribution <out-dir>/categories_by_region.csv \\
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
