from pathlib import Path

p = Path(__file__).resolve().parent.parent / "index.html"
s = p.read_text(encoding="utf-8")


def card(title, cid, meta="", wide=False, tall=False):
    return f'<div class="card{" wide" if wide else ""}"><h3>{title}</h3><div class="meta">{meta}</div><div class="chart{" tall" if tall else ""}"><canvas id="{cid}"></canvas><div class="empty">暂无数据</div></div></div>'


def section(sid, title, subtitle, body, active=False, tag=""):
    return f'<section class="section{" active" if active else ""}" id="{sid}"><div class="section-head"><div><h2>{title}</h2><p>{subtitle}</p></div>{tag}</div>{body}</section>'


parts = []
parts.append(section("overview", "市场总览", "沪镍、不锈钢、伦镍、库存与成交活跃度", '<div class="kpis" id="overview-kpis"></div><div class="grid">' + "".join([
    card("沪镍主连｜日度走势", "overview_shfe", "元/吨 · 上期所 / 知几 / 新浪"),
    card("不锈钢主连｜日度走势", "overview_ss", "元/吨 · 上期所 / 知几 / 新浪"),
    card("LME 3M 镍｜日度走势", "overview_lme", "美元/吨 · LME / Mysteel"),
    card("全球显性库存｜LME + SHFE仓单 + 社库", "overview_global_stock", "吨 · LME日度 + 国内最新周度值平推"),
    card("镍市场成交与持仓", "overview_trade", "吨 / 手 · 来源与口径逐图标注"),
]), True, '<span class="tag ok" id="live-quote-status">行情快照加载中</span>'))
parts.append(section("price", "价格与资金", "现货升贴水、期限结构、进口窗口与镍铁", '<div class="grid">' + "".join([
    card("品牌现货升贴水", "premium", "元/吨 · 俄镍 / 金川镍 / 镍豆", tall=True),
    card("LME 0–3 升贴水｜日度走势", "lme03", "美元/吨 · 负值为 contango"),
    card("精炼镍进口盈亏｜日度走势", "import_profit", "元/吨 · Mysteel / 本地镜像"),
    card("镍铁价格｜江苏", "npi_price", "元/镍点 · 7%≤Ni≤13%"),
    card("上期所镍月间结构", "ni_curve", "元/吨 · 新浪逐合约日 K"),
    card("不锈钢月间结构", "ss_curve", "元/吨 · 新浪逐合约日 K"),
    card("伦镍月间结构", "lme_curve", "美元/吨 · 0 / 3 / 15 / 27 个月"),
]) + "</div>"))
parts.append(section("ratios", "镍价相关", "镍、不锈钢、铜与镍铁折纯镍的相对价格监测", '<div class="kpis" id="ratio-kpis"></div><div class="grid">' + "".join([
    card("镍 / 不锈钢", "ratio_ni_ss", "沪镍主连 / 不锈钢主连 · 原始报价比"),
    card("镍 / 铜", "ratio_ni_copper", "沪镍主连 / 沪铜主连 · 原始报价比"),
    card("NPI 折纯镍 / 精炼镍", "ratio_npi_refined", "镍铁折金属价 / 电解镍价 · 同口径比较"),
]) + '</div><div class="callout" style="margin-top:14px"><b>口径：</b>三项均为同日价格水平的直接比值，不是收益率相关系数；跨品种比值用于观察相对强弱，不解释为实物兑换比例。</div>', tag='<span class="tag warn">价格比值 · 非相关系数</span>'))
project = '<div class="card wide"><h3>印尼镍产业链项目与公司季度产量</h3><div class="meta" id="project-meta">项目进度与财报口径分项展示</div><div class="project-summary"><div class="project-stat"><span>HIGH-CONFIDENCE</span><strong id="project-high-count">—</strong></div><div class="project-stat"><span>2026 EXPECTED ADDITION</span><strong id="project-inc26">—</strong></div><div class="project-stat"><span>2027 IDEAL ADDITION</span><strong id="project-inc27">—</strong></div></div><div class="project-list" id="project-body"></div><div class="project-method">项目确定性只描述当前阶段，不构成投产时间或产量保证；公司产量按 100% 项目、权益或包销口径分别标注。</div></div>'
parts.append(section("supply", "供应", "矿端、精炼镍、镍铁与印尼中间品", '<div class="grid">' + "".join([
    card("中国精炼镍产量", "supply_refined_cn", "金属吨 · 月度"),
    card("印尼精炼镍产量", "supply_refined_id", "金属吨 · 月度"),
    card("中国镍铁产量", "supply_npi_cn", "万金属吨 · 月度"),
    card("印尼镍铁产量", "supply_npi_id", "万金属吨 · 月度"),
    card("镍铁库存", "supply_npi_stock", "万金属吨 · 月度"),
    card("中国硫酸镍产量", "supply_nickel_sulfate", "金属吨 · 月度"),
    card("印尼冰镍主要项目产量（财报）", "supply_matte", "吨镍 · 2026Q2分项目"),
    card("印尼 MHP 主要项目产量（财报）", "supply_mhp", "吨镍 · 2026Q2分项目"),
]) + project + "</div>"))
demand_table = '<div class="card wide"><h3>新能源与不锈钢最新信号</h3><div class="table-wrap"><table><thead><tr><th>指标</th><th>最新期间</th><th class="num">读数</th><th>口径与来源</th></tr></thead><tbody id="demand-signal-body"></tbody></table></div></div>'
parts.append(section("demand", "需求", "不锈钢、动力电池与新能源汽车", '<div class="grid">' + "".join([
    card("中国 300 系不锈钢粗钢产量", "demand_ss_cn", "万吨 · 月度"),
    card("印尼 300 系不锈钢产量", "demand_ss_id", "万吨 · 月度"),
    card("中国动力电池产量：三元", "demand_battery_ternary", "MWh · 月度"),
    card("中国动力电池产量：磷酸铁锂", "demand_battery_lfp", "MWh · 月度"),
    card("中国动力电池装车量：三元", "demand_install_ternary", "MWh · 月度"),
    card("中国动力电池装车量：磷酸铁锂", "demand_install_lfp", "MWh · 月度"),
    card("中国不锈钢进口量", "demand_ss_import", "万吨 · 月度"),
    card("中国不锈钢出口量", "demand_ss_export", "万吨 · 月度"),
]) + demand_table + "</div>"))
warehouse = '<div class="card wide"><h3>交易所与不锈钢库存变化</h3><div class="meta">吨 · LME / 无锡 / 佛山 · 最新可得日期</div><div class="table-wrap"><table><thead><tr><th>地区 / 仓库</th><th>最新日期</th><th class="num">库存</th><th class="num">5 日变化</th><th class="num">20 日变化</th></tr></thead><tbody id="warehouse-body"></tbody></table></div></div>'
parts.append(section("inventory", "库存", "交易所、社会库存与不锈钢库存", '<div class="grid">' + "".join([
    card("SHFE 镍库存 / 仓单", "inventory_shfe", "吨 · 日度或周度"),
    card("LME 镍库存", "inventory_lme", "吨 · 日度"),
    card("SMM 纯镍社会库存（镍板+镍豆）", "inventory_social", "吨 · 周度"),
    card("SMM 国内镍板库存", "inventory_plate", "吨 · 周度"),
    card("SMM 国内镍豆库存", "inventory_bean", "吨 · 周度"),
    card("300 系不锈钢库存：总量（冷轧+热轧）", "inventory_ss300", "吨 · 周度"),
    card("300 系不锈钢库存：冷轧", "inventory_ss_cold", "吨 · 日度"),
    card("300 系不锈钢库存：热轧", "inventory_ss_hot", "吨 · 日度"),
]) + warehouse + "</div>"))
balance = '''<div class="kpis" id="monthly-balance-kpis"></div><div class="grid"><div class="card"><h3>中国镍铁月度供需与平衡</h3><div class="meta">万金属吨 · 供应 / 需求 / 月度平衡</div><div class="balance-chart"><canvas id="mineral-monthly-balance"></canvas><div class="empty">暂无月度平衡数据</div></div></div><div class="card"><h3>中国精炼镍月度供需与平衡</h3><div class="meta">金属吨 · 供应 / 表观消费 / 月度平衡</div><div class="balance-chart"><canvas id="refined-monthly-balance"></canvas><div class="empty">暂无月度平衡数据</div></div></div><div class="card wide"><h3>当年月度镍平衡明细</h3><div class="meta">实绩、当前估算与预测分段；未核实数据留空</div><div class="table-wrap"><table><thead><tr><th>月份</th><th>状态</th><th class="num">NPI供应</th><th class="num">NPI需求</th><th class="num">NPI平衡</th><th class="num">NPI累计</th><th class="num">精炼镍供应</th><th class="num">精炼镍表消</th><th class="num">精炼镍平衡</th><th class="num">精炼镍累计</th></tr></thead><tbody id="monthly-balance-body"></tbody></table></div></div></div><div class="callout" style="margin:14px 0"><b>口径：</b>NPI 与精炼镍分开展示，不跨品类直接相加；金属量与实物量不混用，预测段与已回填数据分开标识。</div><div class="section-head" style="margin-top:24px"><div><h2 style="font-size:20px">全球年度敏感性情景</h2><p>印尼 NPI、印尼中间品、中国精炼镍与全球需求</p></div></div><div class="card"><div class="sliders"><label class="slider">印尼 NPI 变化 <b id="v-mm">0</b> 万吨<input id="s-mm" type="range" min="-5" max="5" step="0.1" value="0"></label><label class="slider">印尼中间品变化 <b id="v-id">0</b> 万吨<input id="s-id" type="range" min="-5" max="5" step="0.1" value="0"></label><label class="slider">中国精炼镍变化 <b id="v-cn">0</b> 万吨<input id="s-cn" type="range" min="-3" max="3" step="0.1" value="0"></label><label class="slider">全球需求变化 <b id="v-dem">0</b> 万吨<input id="s-dem" type="range" min="-5" max="5" step="0.1" value="0"></label></div><div class="balance-result"><div>情景下精炼镍平衡<br><span class="small">正值为过剩，负值为短缺</span></div><strong id="balance-value">—</strong></div></div><div class="callout" style="margin-top:14px">滑块是敏感性情景，不是预测；中间品向精炼镍的传导只按明确假设计算，基准取已核实的 CRU 或本地平衡表。</div>'''
parts.append(section("balance", "镍供需平衡表", "中国月度平衡与全球年度情景", balance, tag='<span class="tag ok">月度实绩 / 当前估算 / 未来预测</span>'))
cost = '<div class="kpis" id="cost-kpis"></div><div class="grid"><div class="card"><h3>全球镍生产成本样本</h3><div class="meta">CRU · C1 / C2 / C3 分口径展示，不混算</div><div class="cost-curve"><canvas id="nickel-cost-curve"></canvas></div></div>' + "".join([
    card("镍铁理论利润", "cost_npi_profit", "元/镍点 · RKEF · 季节性"),
    card("不锈钢利润率（分工艺）", "cost_ss_profit", "% · 300 系 · 一体化 / 高镍铁 / 废不锈钢"),
    card("铬矿价格", "cost_chrome", "元/干吨度 · 南非块矿"),
    card("高碳铬铁价格与钢招", "cost_chromium", "元/50基吨 · cnfeol"),
]) + '<div class="card wide"><h3>镍企产量与价格弹性</h3><div class="meta">按财报披露的镍产量暴露，仅计算价格变化对应的理论收入/毛利变化</div><div class="elastic-controls"><span>基准价 <b id="elastic-base">—</b> 元/吨</span><input id="elastic-price" type="range" min="80000" max="250000" step="1000" value="120000"><span>情景价 <b id="elastic-price-value">—</b> 元/吨</span></div><div class="elastic-grid" id="elastic-grid"></div><div class="callout danger" style="margin-top:14px">这不是归母净利润预测：未扣除成本、加工、套保、税费、权益比例、少数股东与副产品影响；100% 项目口径与权益口径不混用。</div></div><div class="card wide"><h3>成本样本来源与口径</h3><div class="table-wrap"><table><thead><tr><th>公司 / 项目</th><th>期间</th><th>指标</th><th class="num">成本</th><th class="num">产量参考</th><th>原始披露</th><th>来源</th></tr></thead><tbody id="cost-source-body"></tbody></table></div></div></div>'
parts.append(section("cost", "成本曲线与盈利弹性", "CRU 成本、镍铁与不锈钢利润、公司产量弹性", cost, tag='<span class="tag warn">成本口径需逐项核对</span>'))
policy = '<div class="news-grid policy-grid" id="policy-grid"></div><div class="official-monitor"><b>镍产业跟踪入口</b><a href="https://www.esdm.go.id/" target="_blank">印尼 ESDM</a><a href="https://www.antam.com/" target="_blank">Antam</a><a href="https://www.nickelindustries.com/" target="_blank">Nickel Industries</a><a href="https://www.merdekabattery.com/" target="_blank">Merdeka Battery</a><a href="framework.html">原研究框架</a><a href="sources.html">68 槽位数据源</a><span class="small">优先检查 RKAB、公司公告、季度产量、指引与项目进度。</span></div>'
parts.append(section("policy", "政策与事件", "镍、不锈钢、印尼产业政策与宏观定价事件", policy, tag='<span class="tag ok" id="policy-live-status">近期事件加载中</span>'))
sentiment = '<div class="tech-grid" id="tech-grid"></div><div class="callout" style="margin:14px 0"><b>解释边界：</b>缠论与江恩在程序化面板中采用可复核的“分型/区间位置”和“区间分位”简化版，不把它们包装成确定性买卖信号。</div><div class="card" style="margin-bottom:14px"><h3>沪镍主连｜日K价格与均线</h3><div class="meta" id="technical-live-meta">元/吨 · 最近 320 个交易日 · MA5 / MA10 / MA20 / MA60 / MA288 · 红涨绿跌</div><div class="kline-chart"><canvas id="ni-kline"></canvas></div></div><div class="card"><h3>研究资料｜“镍”相关条目</h3><div class="meta" id="social-live-meta">本地真实研究资料快照；无互动数据时不生成热度或评论评分。</div><div class="news-grid" id="social-grid"></div></div><div class="callout danger" style="margin-top:14px"><b>资料边界：</b>只展示可追溯的条目与原文链接；获取失败时保留最近快照，不伪造社交热度或观点强弱。</div>'
parts.append(section("sentiment", "市场情绪与四框架技术分析", "道氏趋势 / 缠论结构 / MACD / 江恩", sentiment, tag='<span class="tag warn" id="intelligence-live-status">技术快照加载中</span>'))
footer = '<footer class="footer"><span>数据来源：上期所、LME、SMM、Mysteel、cnfeol、CRU、公司公告与本地研究资料 · <a href="framework.html">研究框架</a> · <a href="sources.html">数据溯源</a></span><span class="warning">正式版 · 不构成投资建议</span></footer>'
start = s.index('<section class="section active" id="overview">')
end = s.index('</div>\n<script>!function(t,e)', start)
s = s[:start] + "\n".join(parts) + "\n" + footer + "\n" + s[end:]
p.write_text(s, encoding="utf-8")
