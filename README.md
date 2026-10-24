# 镍市瞭望 · nickel-panel

镍 × 不锈钢产业监测台。页面结构与视觉系统复刻 `tin-insight`：10 个板块、KPI、Chart.js 图表、平衡表、情景滑块、成本与弹性、政策事件、四框架技术分析、昼夜主题和移动端布局。

线上：https://amiya866.github.io/nickel-panel/

## 页面

- `index.html` — 镍×不锈钢主面板，内嵌 Chart.js 与 `DATA`。
- `framework.html` — 原 13 板块镍研究框架存档。
- `sources.html` / `sources.md` — 镍与不锈钢周报 68 个图表槽位溯源。
- `assets/app.js` — 导航、图表、K线、表格、滑块与快照刷新。
- `data.json` — 基本面构建产物；同时注入 `index.html` 的 `const DATA=`。
- `quotes.json` / `technical.json` — 公开行情与技术分析快照。
- `policy.json` / `social.json` — 真实事件与研究资料快照；无数据时保持空态。

## 本地构建

```bash
python scripts/build_nickel_data.py --inject
python scripts/fetch_quotes.py
python scripts/build_technical_snapshot.py
python scripts/build_content_snapshots.py
```

基本面脚本只用本机数据，不能在 GitHub Ubuntu 上直接运行。`--offline` 可关闭 zhiji/新浪直连。`--inject` 会同时更新 `index.html`；单独生成数据时省略该参数。

## 数据口径

- Excel：`镍数据.xlsx`、`表01_镍产业数据.xlsx`，按周报 `_ni_bindings.json` 已人工核定的原生图绑定只读提取，不保存工作簿。
- 直连：zhiji、Sina 期货逐合约/主连、LME 序列。
- 镜像：Mysteel、SMM、cnfeol；停更序列保留真实日期，未核实口径不以 0 或旧值代替。
- 财报真源：`D:/Kimi/金属总网/网站构建/财报汇总/镍/全球镍企季度产量梳理.xlsx`。
- 成本：CRU `nickel-industry-costs-q3-2026.xls`；C1 按美元/磅转美元/吨，保留副产物抵扣导致的负成本，不与 C2/C3 混算。
- 平衡：NPI 与精炼镍分开，金属量与实物量不混用；预测段单独标识。
- 事件：整合研究站与 caibao-hub 已核验条目；不生成虚构社交热度或评论评分。

## 发布

GitHub Actions 每 5 分钟刷新公开行情与技术快照，并部署 Pages。基本面 Excel/SQLite 数据在本机运行 `--inject` 后随页面发布。站点不依赖锡站 Worker，也不把快照标记为独立实时 Worker。

验收要求：10 个板块可切换、控制台无错误、图表键与 canvas 对应、JSON 可解析、日期与单位正确、移动端无横向溢出。
