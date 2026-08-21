# FastMoss 达人榜多维度分析报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{country_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample}

---

## 一、达人国家分布

| 国家 | 数量 | 占比 |
|---|---|---|
{country_table}

**核心洞察**: _（看东南亚占比、欧美占比、单一市场是否垄断。达人分布 ≠ 商品分布：商品榜反映需求方，达人榜反映供给侧。东南亚达人供给充足但单价低，美区达人少但 GMV 高）_

---

## 二、达人品类分布（Top 10）

| 品类 | 数量 |
|---|---|
{category_table}

**洞察方向**：
- 哪些品类的达人供给最饱和（竞争激烈）
- 哪些品类达人稀缺（议价空间大）
- 是否存在"高 GMV 品类但达人少"的供需缺口（如保健、3C）

---

## 三、各榜单 × 国家交叉

**每行：榜单 | 总样本 | Top 3 国家 (含计数)**

{ranking_country_table}

**结构性洞察方向**：
1. 哪个榜单被某一国家垄断？（如蓝 V 榜美区主导 → 品牌化集中）
2. 哪些国家的达人在多榜单都强势？（综合型达人市场）
3. 哪些国家只涨粉不带货？（流量 vs 商业化的差距）

---

## 四、跨榜重复达人

{repeat_creators}

**洞察方向**：
- 同时进入多榜（如涨粉+带货）的达人是高价值合作对象
- 单榜单高频出现 = 持续运营；多榜单出现 = 综合能力

---

## 五、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **品牌方** | _（按目标市场找头部达人；优先跨榜达人）_ |
| **MCN** | _（找达人稀缺品类签约；填补供需缺口）_ |
| **跨境商家** | _（马来/泰国流量便宜；美区 GMV 高但门槛高）_ |
| **达人运营** | _（盯黑马榜潜力达人提前签约，成本最低）_ |

---

## 报告复现命令

```bash
python <path-to-skill>/scripts/analyze.py \\
    --fans <out-dir>/fans.csv \\
    --commerce <out-dir>/commerce.csv \\
    --blue-v <out-dir>/blue-v.csv \\
    --popular <out-dir>/popular.csv \\
    --horse <out-dir>/horse.csv \\
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
