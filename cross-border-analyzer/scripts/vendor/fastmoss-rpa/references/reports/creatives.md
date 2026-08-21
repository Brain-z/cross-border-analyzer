# FastMoss 视频素材榜多维度分析报告

> This template is auto-filled by `scripts/analyze.py --out-md <path>`.  
> Curly-brace tokens like `{{country_table}}` are placeholders — do **not** rename them or `analyze.py` rendering will fail.  
> After generation, fill in the insight paragraphs (italics placeholders) by interpreting the tables.

**抓取时间**: {scrape_date} | **样本量**: {sample}

---

## 一、素材国家分布

| 国家 | 数量 | 占比 |
|---|---|---|
{country_table}

**核心洞察**: _（视频/音乐/标签的"火"地域分布。素材榜反映"内容供给端"趋势：哪些市场的内容创意正在引领）_

---

## 二、各榜单 × 国家交叉

**每行：榜单 | 总样本 | Top 3 国家 (含计数)**

{ranking_country_table}

**结构性洞察方向**：
1. 哪个国家的视频/音乐/标签同时强势？（综合内容市场）
2. 哪些国家的视频热但音乐弱？反之亦然？（内容生态差异）
3. 标签榜的"地域集中度"反映话题传播模式

---

## 三、跨榜重复实体（视频/音乐/标签）

{repeat_entities}

**洞察方向**：
- 同一首音乐 / 同一个标签在多个视频反复出现 = 高潜力素材
- 优先采用高频音乐/标签可借势

---

## 四、行动建议（模板）

| 角色 | 建议（根据上方数据填写）|
|---|---|
| **投手/剪辑** | _（采用热门音乐+热门标签组合，提升自然流量）_ |
| **内容策略** | _（学习热门视频的发布时间、互动率结构）_ |
| **品牌方** | _（在素材中融入热门标签，借势提升曝光）_ |

---

## 报告复现命令

```bash
python <path-to-skill>/scripts/analyze.py \\
    --video <out-dir>/videos.csv \\
    --song <out-dir>/songs.csv \\
    --hashtag <out-dir>/hashtags.csv \\
    --out-md <report>.md
```

`<path-to-skill>` = the directory holding this skill's `SKILL.md` (`.workbuddy/skills/fastmoss-rpa` for project install, `~/.workbuddy/skills/fastmoss-rpa` for user install).
