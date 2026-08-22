# 跨境商品数据分析插件（cross-border-analyzer）

面向 TikTok 跨境卖家的商品数据分析插件，首发数据源为 FastMoss（fastmoss.com）。
你只需要用一句话描述需求，例如：

> 美国 时尚配饰 近 7 天 商品销量榜 Top 100

插件会自动完成：**意图解析 → FastMoss 数据抓取 → 清洗 → 评分 → 输出报告、交互仪表盘和 Excel 排名表**。

评分模型默认按"美国时尚配件 / 平价饰品"类目调校，权重可改。

## 功能特性

- **一句话需求解析**：自动识别榜单、时间范围、地区、品类、数量，缺省值智能补齐；
- **FastMoss 七大模块抓取**：商品 / 达人 / 店铺 / 广告 / 素材 / 直播 / 品类大盘，复用社区开源工具 fastmoss-rpa；
- **自动清洗**：中英文列名别名自适应（排名、价格、销量、GMV、佣金率、上架天数等），无需手动整理；
- **评分模型**：每个商品输出市场热度、可做性、综合潜力三个分数，并标注暴涨新星 / 价格战红海 / 高佣爆款等风险信号；
- **三类输出**：Markdown 分析报告、交互式 HTML 仪表盘（价格/销量/品类筛选）、Excel 友好的 CSV 排名表；
- **品类自适应**：品类以实际抓取到的数据范围为准，不写死；种子映射表仅用于抓取前的筛选参数；
- **多通道降级**：bsk 浏览器自动化 → Codex 内嵌浏览器 → 手动导入 CSV，总有一条路能跑通。

## 适用场景

- 美国 TikTok 时尚配件 / 平价饰品选品调研（爆款榜单、新品机会）；
- 竞品与市场监控（商品榜、达人榜、店铺榜、广告趋势、素材榜、直播榜、品类大盘）；
- 自有运营数据导入分析（手动上传 CSV，走同一套评分与输出管道）。

## 目录结构

```text
cross-border-analyzer/
├── .codex-plugin/plugin.json        插件清单
├── skills/
│   ├── cross-border-analysis/       总控 skill：意图解析、路由、评分、报告、仪表盘
│   └── fastmoss-fetch/              FastMoss 抓取 skill：复用社区工具 + 降级链
├── rules.md                         用户前置规则（筛选条件、Top N、阈值，改这里即改行为）
├── scripts/
│   ├── vendor/fastmoss-rpa/         社区 fastmoss_rpa.py（原样打包，仅改 bsk 路径查找）
│   ├── normalize.py                 列名识别与清洗
│   ├── score.py                     评分模型
│   ├── report.py                    Markdown 报告生成
│   ├── dashboard.py                 交互式 HTML 仪表盘生成
│   └── fastmoss_filtered.py         bsk 编排：销量榜 URL / 月榜 / 日期范围抓取（社区工具缺的能力）
├── references/
│   ├── categories.md                FastMoss 品类种子映射表（以实际数据为准）
│   ├── scoring.md                   评分模型说明与调参
│   └── fastmoss-fields.md           FastMoss 字段说明与提取方法
├── assets/sample/                   示例数据（24 款饰品，用于演示）
├── data/raw/                        已抓取的真实榜单数据（新品榜 245 / 销量榜 260）
├── output/                          分析产物（报告 / 仪表盘 / 评分表）
├── THIRD_PARTY_NOTICE.md            第三方组件与许可说明
└── README.md                        本文档
```

## 前置规则（rules.md）

插件根目录的 `rules.md` 是**用户配置入口**：分析范围、商品筛选条件（价格/佣金/销量下限）、
详情页补充范围与标签阈值、评分权重、抓取参数都在这里设置。修改后直接生效，无需改代码。

**里面的值都是默认值，不是写死**：每次分析时你可以临时指定国家（美国 / 英国 / 印尼…）、
类目（时尚配件 / 美妆个护 / 女装…及子类）、榜单（商品 / 达人 / 店铺 / 广告 / 素材 / 直播 /
品类大盘）、时间（日 / 周 / 月 / 自定义日期）和数量；你没指定的才用 `rules.md` 的默认值。

## 详情页补充（成交渠道占比）

对评分总结出的 Top N 商品（`rules.md` 第 3 节），用 browser-skill 打开 FastMoss
商品详情页，提取**成交渠道占比**（商品卡 / 店铺自营号 / 达人带货）和带货达人数，
并按阈值打"达人依赖型 / 自然流量型"标签后写回评分表。
该指标决定爆品是吃商品卡自然流量还是靠达人带货，直接影响跟款策略。

## 安装

### 1. 环境前置

- Codex（插件目标环境）；
- FastMoss 账号并已登录浏览器（专业版数据最完整）；
- Python 3.8+（脚本只用标准库）。

### 2. BrowserSkill（bsk，推荐，可选）

bsk 让抓取全自动；不装也能用内嵌浏览器或手动导入兜底。

```bash
# 安装 CLI（macOS / Linux）
curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh

# 安装 browser-skill 使用说明（含 Claude Code / Codex 等）
bsk install-skill --yes

# 自检：确保 extension connected 显示 1 browser(s) connected
bsk doctor
```

浏览器扩展需要手动安装：打开
<https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi>
→ 添加至 Chrome → 扩展弹窗变绿。

终端找不到 `bsk` 时执行 `source ~/.zshrc` 或重开终端。

### 3. 插件安装

把 `cross-border-analyzer/` 目录加入 Codex 个人 marketplace（`~/.agents/plugins/marketplace.json`），
或按 Codex 的本地插件安装方式注册，之后即可在 Codex 中直接使用。

## 快速开始

### 方式一：自然语言（推荐）

在 Codex 中说：

> 用跨境商品数据分析插件，分析美国珠宝及饰品近 7 天商品销量榜 Top 100

### 方式二：命令行（示例数据演示）

```bash
# 1. 抓取（需要 bsk 已连接；示例数据可跳过这步）
python3 scripts/vendor/fastmoss-rpa/fastmoss_rpa.py filter \
  --section products --country 美国 --category "时尚配件" \
  --pages 5 --out data/raw/products_us.csv

# 2. 清洗
python3 scripts/normalize.py data/raw/products_us.csv data/raw/normalized.csv

# 3. 评分
python3 scripts/score.py data/raw/normalized.csv data/raw/scored.csv

# 4. 报告 + 仪表盘
python3 scripts/report.py data/raw/scored.csv output/report.md \
  --query "美国 珠宝及饰品 近7天 商品销量榜 Top 100"
python3 scripts/dashboard.py data/raw/scored.csv output/dashboard.html

# 用示例数据直接跑（无需抓取）：
python3 scripts/normalize.py assets/sample/products_sales_us.csv /tmp/n.csv
python3 scripts/score.py /tmp/n.csv /tmp/s.csv
python3 scripts/report.py /tmp/s.csv /tmp/report.md --query "示例数据"
python3 scripts/dashboard.py /tmp/s.csv /tmp/dashboard.html
```

## 输出说明

| 产物 | 路径 | 说明 |
|---|---|---|
| 分析报告 | `output/<时间戳>/report.md` | 需求复述、市场概览、Top 榜单、选品建议、风险提示 |
| 交互仪表盘 | `output/<时间戳>/dashboard.html` | 价格分布、销量散点、潜力 Top 20、可筛选商品表 |
| 评分排名表 | `output/<时间戳>/scored.csv` | UTF-8 BOM，Excel 直接打开，含三个分数与标记 |
| 原始数据 | `data/raw/`、`data/import/` | 原始字段不改，可回溯 |

## 评分模型

| 维度 | 默认权重 |
|---|---|
| 销量与增长 | 30% |
| 价格带适配（5–25 美元） | 20% |
| 佣金率 | 15% |
| 竞争度 | 15% |
| 生命周期 | 10% |
| 店铺质量 | 10% |

三个综合分：市场热度、可做性、综合潜力；异常标记：暴涨新星 / 价格战红海 / 高佣爆款 / 高潜力 / 谨慎。
权重与规则详见 [references/scoring.md](references/scoring.md)，修改 `scripts/score.py` 顶部常量即可调参。

## 品类说明

抓取前的品类筛选参数参考 [references/categories.md](references/categories.md) 的种子映射；
分析阶段以数据中实际出现的品类为准（自动去重枚举），不写死。

## 第三方组件与许可

- **fastmoss-rpa**（[liangdabiao/fastmoss-rpa-skills](https://github.com/liangdabiao/fastmoss-rpa-skills)）：
  抓取核心，已打包至 `scripts/vendor/fastmoss-rpa/`。该仓库未标注明确 LICENSE，当前仅限个人本地使用；
- **BrowserSkill / bsk**（[Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill)）：
  浏览器桥接工具，可选依赖。

详见 [THIRD_PARTY_NOTICE.md](THIRD_PARTY_NOTICE.md)。

## 开发与验证

```bash
# 插件校验（需 PyYAML）
python3 /Users/zhangxinyu/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py cross-border-analyzer

# skill 校验
python3 /Users/zhangxinyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py cross-border-analyzer/skills/cross-border-analysis
python3 /Users/zhangxinyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py cross-border-analyzer/skills/fastmoss-fetch
```

## 常见问题

| 现象 | 处理 |
|---|---|
| `bsk: command not found` | `source ~/.zshrc` 或重开终端；或直接 `/Users/zhangxinyu/.local/bin/bsk` |
| `bsk status` 提示 daemon 未运行 | `bsk daemon start` 后重试 |
| `extension connected: 0` | 浏览器扩展未装或未连接，装好后弹窗变绿 |
| 抓到 0 行数据 | 翻页太快，加 `--nav-sleep 6 --page-sleep 4` |
| 字段为空 | 多为 FastMoss 套餐权限限制，保留原样，不编造 |
