# FastMoss 多维度分析报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{country_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample}

---

## 一、全局 Top 50 概览

### 国家分布

| 国家 | 数量 | 占比 |
|---|---|---|
{country_table}

**核心洞察**: _（看东南亚占比、欧美占比、单一市场是否垄断）_

### 品类分布（Top 8）

| 品类 | 数量 |
|---|---|
{category_table}

### 佣金策略

| 佣金 | 数量 | 占比 |
|---|---|---|
{commission_table}

**洞察方向**：
- "−" 占比高 → 新品初期不开联盟，纯靠短视频/直播
- 10% 是主流 → 高于 10% 的可视为推新加速
- 极端高佣（13%+）值得单独追踪

### 重复上榜店铺（同一店铺多新品 ≥ 2 次）

{repeat_shops}

---

## 二、国家 × 品类交叉对比

**每行：国家 | 品类 #1 销量 | #2 | #3 | (该国总样本)**

{country_category_table}

**结构性洞察方向**：
1. 哪个国家被 1-2 个品类垄断（>50%）？
2. 哪个品类在多国都强势（区域性大单品）？
3. 美区 vs 东南亚品类差异 → 决定出海路径

---

## 三、品类 × 国家交叉对比

**每行：品类 | 国家 #1 销量 | #2 | #3 | (该品类总样本)**

{category_country_table}

**洞察方向**：
- 单一国家垄断某品类（如印尼占保健品 60%+）→ 该国是该品类的必选市场
- 多国分布均衡的品类 → 全球通用品类
- 仅在某国出现的品类（如马来穆斯林时尚）→ 文化本土化

---

## 四、单店铺上新节奏

### 月度上新数（近 8 个月）

| 月份 | 上新数 |
|---|---|
{shop_cadence_table}

**节奏洞察方向**：
1. 上新频率是否在加速？（近 2 月 vs 半年前）
2. 上新即爆款（同一店铺近期上新中有 1 款冲进 Top 50）
3. 历史商品 / 在售商品比例 → 淘汰率，反映快时尚还是耐用品逻辑
4. 跟踪建议：每月底集中上新后 1-2 周，看哪款冲销量榜 → 复刻同款面料/版型/概念

> 多店铺追踪时，对每个店铺单独跑一次 `shop_scraper.py`，再分别用 `analyze.py --shop <path>` 渲染。

---

## 五、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **女装出海** | _（首选马来穆斯林款 / 泰国高频消费；避美区红海）_ |
| **美妆出海** | _（首选泰国 / 印尼，平价+本地化）_ |
| **保健品出海** | _（首选印尼，其他小众）_ |
| **联盟达人** | _（盯零佣金新品 → 联系店铺挂 10% 抢首发）_ |
| **竞品监控** | _（重点跟 Top 50 中重复上榜的 2-3 家店铺）_ |

---

## 报告复现命令

```bash
python <path-to-skill>/scripts/analyze.py \
    --top50 <out-dir>/top50.csv \
    --by-country <out-dir>/by_country.csv \
    --by-category <out-dir>/by_category.csv \
    --shop <out-dir>/shop_<name>.csv \
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
