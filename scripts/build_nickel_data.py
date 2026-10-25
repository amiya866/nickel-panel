import argparse
import datetime as dt
import json
import math
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlencode

import xlrd
from openpyxl import load_workbook

from excel_charts import COLORS, ChartExtractor, empty_chart, number

ROOT = Path(__file__).resolve().parents[1]
NIW = Path(r"D:/拷贝文件/E/永安/周报数据更新/图表格式(1)/锡周报20260709_试跑/镍不锈钢")
ND = NIW / "镍数据.xlsx"
B01 = NIW / "表01_镍产业数据.xlsx"
CRU_COST = NIW / "nickel-industry-costs-q3-2026.xls"
FINANCIAL = Path(r"D:/Kimi/金属总网/网站构建/财报汇总/镍/全球镍企季度产量梳理.xlsx")
MYSTEEL_DB = Path(r"D:/Kimi/mysteel_mirror/mysteel_mirror.db")
CNFEOL_DB = Path(r"D:/Kimi/cnfeol_mirror/cnfeol_mirror.db")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
REQUIRED = [
    "overview_shfe", "overview_ss", "overview_lme", "overview_global_stock", "overview_trade",
    "premium", "lme03", "import_profit", "npi_price", "ni_curve", "ss_curve", "lme_curve",
    "ratio_ni_ss", "ratio_ni_copper", "ratio_npi_refined", "supply_refined_cn", "supply_refined_id",
    "supply_npi_cn", "supply_npi_id", "supply_npi_stock", "supply_nickel_sulfate", "supply_matte",
    "supply_mhp", "demand_ss_cn", "demand_ss_id", "demand_battery_ternary", "demand_battery_lfp",
    "demand_install_ternary", "demand_install_lfp", "demand_ss_import", "demand_ss_export",
    "inventory_shfe", "inventory_lme", "inventory_social", "inventory_plate", "inventory_bean",
    "inventory_ss300", "inventory_ss_cold", "inventory_ss_hot", "cost_npi_profit", "cost_ss_profit",
    "cost_chrome", "cost_chromium",
]
BINDING_MAP = {
    "supply_refined_cn": "P11-TL", "supply_refined_id": "P11-TR", "overview_trade_net": "P11-BL",
    "inventory_social": "P12-T0", "inventory_plate": "P12-T1", "inventory_shfe": "P12-B1",
    "inventory_lme": "P13-TR", "lme_region": "P13-BL", "supply_sulfate_rate": "P14-TR",
    "demand_battery_ternary": "P16-TL", "demand_battery_lfp": "P16-TR",
    "demand_install_ternary": "P16-BL", "demand_install_lfp": "P16-BR", "npi_price": "P24-TL",
    "supply_chrome": "P27-TL", "supply_chrome_import": "P27-TR", "supply_npi_cn": "P28-TL",
    "supply_npi_id": "P28-BL", "supply_npi_stock": "P28-BR", "demand_ss_cn": "P29-TL",
    "demand_ss_id": "P29-TR", "demand_ss_import": "P29-BL", "demand_ss_export": "P29-BR",
    "inventory_ss300": "P30-TL",
}


class Build:
    def __init__(self, offline=False):
        self.offline = offline
        self.warnings = []
        self.charts = {key: empty_chart() for key in REQUIRED}
        self.latest = {key: [None, None] for key in [
            "shfe", "ss", "lme", "global_stock", "trade_peer", "trade_downstream", "npi_price",
            "social_stock", "lme_stock", "tc_yunnan", "smelting_profit",
        ]}
        self.sources = {}
        self.series = {}
        self.binding_records = {}
        self.live_quote = {}

    def warn(self, scope, error):
        text = f"{scope}: {str(error)[:300]}"
        self.warnings.append(text)
        print("WARN", text, flush=True)

    def put(self, key, chart, source):
        self.charts[key] = chart or empty_chart()
        self.sources[key] = source

    def mirror(self, chart_code, start="2021-01-01"):
        connection = sqlite3.connect(f"file:{MYSTEEL_DB.as_posix()}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "select series_name,date,value from series_points where chart_code=? and date>=? order by date",
                (chart_code, start),
            ).fetchall()
        finally:
            connection.close()
        grouped = {}
        for name, date, value in rows:
            numeric = number(value)
            if numeric is not None and numeric != 0:
                grouped.setdefault(name, {})[date[:10]] = numeric
        if not grouped:
            raise RuntimeError(f"Mysteel {chart_code} 无有效数据")
        return grouped

    def mirror_chart(self, code, name=None):
        grouped = self.mirror(code)
        labels = sorted({date for values in grouped.values() for date in values})
        datasets = []
        for i, (series_name, values) in enumerate(grouped.items()):
            datasets.append({
                "label": name or series_name, "data": [values.get(date) for date in labels],
                "borderColor": COLORS[i % len(COLORS)], "borderWidth": 1.6,
            })
        return {"labels": labels, "datasets": datasets}

    def zhiji_key(self):
        if os.environ.get("ZHIJI_KEY"):
            return os.environ["ZHIJI_KEY"]
        path = Path(r"D:/拷贝文件/E/永安/2025 永安/zhiji_mcp_server.py")
        match = re.search(r"wk_[0-9a-f]+", path.read_text(encoding="utf-8", errors="ignore"))
        if not match:
            raise RuntimeError("未找到 ZHIJI_KEY")
        return match.group(0)

    def zhiji(self, indicator, start="2021-01-01"):
        if self.offline:
            raise RuntimeError("offline 模式禁用 zhiji")
        url = "https://zhiji-ai.xyz/commodity/api/series?" + urlencode({
            "id": indicator, "start": start, "end": dt.date.today().isoformat(),
        })
        result = subprocess.run([
            "curl", "-sS", "--max-time", "40", "-H", f"X-Data-Key: {self.zhiji_key()}",
            "-H", "User-Agent: nickel-panel-data/1.0", url,
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=50,
            creationflags=NO_WINDOW)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f"curl rc={result.returncode}")
        payload = json.loads(result.stdout)
        points = {}
        for row in payload.get("points") or []:
            numeric = number(row.get("value"))
            if numeric is not None:
                points[str(row.get("date"))[:10]] = numeric
        if not points:
            raise RuntimeError(f"zhiji {indicator} 无有效数据 {str(payload)[:100]}")
        return points

    def guan(self, symbol):
        if self.offline:
            raise RuntimeError("offline 模式禁用 guan")
        url = f"https://zhiji-ai.xyz/guan/api/kline?symbol={symbol}&freq=D&limit=500"
        result = subprocess.run(["curl", "-sS", "--max-time", "40", "-H", f"X-Guan-Key: {self.zhiji_key()}", url],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=50,
                                creationflags=NO_WINDOW)
        payload = json.loads(result.stdout)
        rows = payload.get("bars") or payload.get("data") or payload.get("points") or payload.get("klines") or []
        if isinstance(rows, dict):
            rows = rows.get("data") or rows.get("points") or []
        output = []
        for row in rows:
            if isinstance(row, dict):
                date = row.get("date") or row.get("d") or row.get("time")
                close = row.get("close") if row.get("close") is not None else row.get("c")
                numeric = number(close)
                if date and numeric is not None:
                    output.append((str(date)[:10], numeric, row))
        if not output:
            raise RuntimeError(f"guan {symbol} 无法解析 {str(payload)[:200]}")
        return output

    def cnfeol(self, indicator):
        connection = sqlite3.connect(f"file:{CNFEOL_DB.as_posix()}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "select date,value from series_points where indicator_id=? order by date", (indicator,)
            ).fetchall()
        finally:
            connection.close()
        points = {}
        for date, value in rows:
            numeric = number(value)
            if numeric is not None:
                text = str(date)
                points[text[:10] if len(text) >= 10 else text + "-01"] = numeric
        if not points:
            raise RuntimeError(f"cnfeol {indicator} 无有效数据")
        return points

    def direct_chart(self, points, name, monthly=False, limit=None):
        items = sorted(points.items())
        if limit:
            items = items[-limit:]
        labels = [date[:7] if monthly else date for date, _ in items]
        return {"labels": labels, "datasets": [{
            "label": name, "data": [value for _, value in items], "borderColor": COLORS[0], "borderWidth": 1.7,
        }]}

    def ratio(self, left, right, name):
        common = sorted(set(left) & set(right))
        points = {date: left[date] / right[date] for date in common if right[date]}
        return self.direct_chart(points, name)

    def load_bindings(self):
        bindings = json.loads((NIW / "_ni_bindings.json").read_text(encoding="utf-8"))
        extractors = {"ND": ChartExtractor(ND), "B01": ChartExtractor(B01)}
        try:
            for key, slot in BINDING_MAP.items():
                config = bindings[slot]
                try:
                    chart, records = extractors[config["wb"]].extract(config["sheet"], config["pos"], config)
                    if not chart["datasets"]:
                        raise RuntimeError("原生图无有效系列")
                    self.put(key, chart, {"type": "excel-native", "slot": slot, "workbook": config["wb"],
                                          "sheet": config["sheet"], "position": config["pos"],
                                          "unit": config.get("unit"), "valueScale": config.get("value_scale", 1)})
                    self.binding_records[key] = records
                    print("EXCEL", key, len(chart["datasets"]), flush=True)
                except Exception as error:
                    self.warn(f"Excel {key}/{slot}", error)
        finally:
            for extractor in extractors.values():
                extractor.close()

    def seasonal_latest(self, key, year=2026):
        for record in self.binding_records.get(key, []):
            if str(year) in record["name"] and record["points"]:
                point = record["points"][-1]
                raw = point[2]
                if isinstance(raw, (dt.date, dt.datetime)):
                    date = dt.date(year, raw.month, raw.day).isoformat()
                elif "周" in str(raw):
                    date = f"{year}-W{re.search(r'\d+', str(raw)).group()}"
                else:
                    date = f"{year}-{point[0]}"
                return [date, point[1]]
        return [None, None]

    def load_market(self):
        for symbol, key, latest_key, name in [("NI", "overview_shfe", "shfe", "沪镍主连"),
                                               ("SS", "overview_ss", "ss", "不锈钢主连"),
                                               ("CU", "copper", None, "沪铜主连")]:
            try:
                today = dt.date.today().isoformat()
                rows = [row for row in self.guan(symbol)
                        if row[0] <= today and dt.date.fromisoformat(row[0]).weekday() < 5]
                if not rows:
                    raise RuntimeError(f"guan {symbol} 无有效交易日")
                self.series[symbol] = {date: value for date, value, _ in rows}
                if key != "copper":
                    self.put(key, self.direct_chart(self.series[symbol], name), {"type": "zhiji-guan", "symbol": symbol})
                    date, value, raw = rows[-1]
                    self.latest[latest_key] = [date, value]
            except Exception as error:
                self.warn(f"行情 {symbol}", error)
        try:
            points = self.zhiji("FU00014810")
            self.series["LME"] = points
            chart = self.direct_chart(points, "LME镍3M", limit=500)
            self.put("overview_lme", chart, {"type": "zhiji", "indicator": "FU00014810"})
            date = max(points)
            self.latest["lme"] = [date, points[date]]
        except Exception as error:
            self.warn("LME 3M", error)
        if "NI" in self.series and "SS" in self.series:
            self.put("ratio_ni_ss", self.ratio(self.series["NI"], self.series["SS"], "沪镍/不锈钢"),
                     {"type": "derived", "formula": "SHFE NI / SHFE SS"})
        if "NI" in self.series and "CU" in self.series:
            self.put("ratio_ni_copper", self.ratio(self.series["NI"], self.series["CU"], "沪镍/沪铜"),
                     {"type": "derived", "formula": "SHFE NI / SHFE CU"})
        if "NI" in self.series and self.binding_records.get("npi_price"):
            self.latest["npi_price"] = self.seasonal_latest("npi_price")
            current_record = next(record for record in self.binding_records["npi_price"] if "2026" in record["name"])
            npi = {}
            for text, value, raw in current_record["points"]:
                if isinstance(raw, (dt.date, dt.datetime)):
                    npi[dt.date(2026, raw.month, raw.day).isoformat()] = value * 100
                else:
                    match = re.match(r"(\d{2})-(\d{2})", str(raw))
                    if match:
                        npi[f"2026-{match.group(1)}-{match.group(2)}"] = value * 100
            self.put("ratio_npi_refined", self.ratio(npi, self.series["NI"], "镍铁折镍价/沪镍"),
                     {"type": "derived", "formula": "NPI元/镍点*100 / SHFE NI"})
        if self.latest["shfe"][1] is not None:
            values = list(self.series["NI"].values())
            change = (values[-1] / values[-2] - 1) * 100 if len(values) > 1 else None
            self.live_quote = {"last": values[-1], "changePct": change, "asOf": self.latest["shfe"][0],
                               "snapshot": True, "source": "zhiji guan 日K"}

    def load_direct(self):
        direct = [
            ("premium_russia", "ID00302596", "俄镍升贴水"),
            ("premium_jinchuan", "s20019092", "金川镍升贴水"),
            ("premium_bean", "ID00302595", "镍豆升贴水"),
            ("cost_chrome", "ID00258454", "南非铬矿36-38%Cr"),
            ("inventory_ss_cold", "ID01706925", "不锈钢300系冷轧库存"),
            ("inventory_ss_hot", "ID01706924", "不锈钢300系热轧库存"),
        ]
        for key, indicator, name in direct:
            try:
                points = self.zhiji(indicator)
                self.put(key, self.direct_chart(points, name, limit=500), {"type": "zhiji", "indicator": indicator})
            except Exception as error:
                self.warn(f"直连 {key}", error)
        premium_parts = [self.charts[key] for key in ["premium_russia", "premium_jinchuan", "premium_bean"]]
        premium_labels = sorted({date for chart in premium_parts for date in chart["labels"]})
        premium_datasets = []
        for chart in premium_parts:
            for dataset in chart["datasets"]:
                lookup = dict(zip(chart["labels"], dataset["data"]))
                premium_datasets.append({**dataset, "data": [lookup.get(date) for date in premium_labels]})
        if premium_labels:
            self.put("premium", {"labels": premium_labels, "datasets": premium_datasets},
                     {"type": "zhiji", "indicators": ["ID00302596", "s20019092", "ID00302595"], "unit": "元/吨"})
        for key, code in [("import_profit", "niProfitImport"), ("supply_nickel_sulfate", "niRawSupplyMetalYield"),
                          ("inventory_bean", "niRawStockSociety")]:
            try:
                self.put(key, self.mirror_chart(code), {"type": "mysteel-mirror", "chart": code,
                                                       "staleSource": key == "inventory_bean"})
            except Exception as error:
                self.warn(f"镜像 {key}", error)
        try:
            self.put("cost_chromium", self.direct_chart(self.cnfeol("cv:282"), "高碳铬铁 内蒙古", limit=1000),
                     {"type": "cnfeol-mirror", "indicator": "cv:282"})
        except Exception as error:
            self.warn("铬铁镜像", error)
        try:
            values = next(iter(self.mirror("niStockLmeSum").values()))
            date = max(values)
            self.latest["lme_stock"] = [date, values[date]]
        except Exception as error:
            self.warn("LME库存latest", error)
        self.latest["social_stock"] = self.seasonal_latest("inventory_social")
        if not self.latest["npi_price"][0]:
            self.latest["npi_price"] = self.seasonal_latest("npi_price")

    def sina_contract(self, code):
        if self.offline:
            raise RuntimeError("offline 模式禁用新浪")
        url = f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/x/InnerFuturesNewService.getDailyKLine?symbol={code}"
        result = subprocess.run(["curl", "-sS", "--max-time", "25", url], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=35, creationflags=NO_WINDOW)
        match = re.search(r"\((.*)\)", result.stdout, re.S)
        if not match:
            raise RuntimeError(f"新浪 {code} 无K线")
        rows = json.loads(match.group(1))
        return {row["d"]: float(row["c"]) for row in rows if row.get("d") and number(row.get("c")) is not None}

    def shfe_curve(self, symbol):
        today = dt.date.today()
        year, month = today.year, today.month
        contracts = []
        for _ in range(10):
            code = f"{symbol}{year % 100:02d}{month:02d}"
            try:
                points = self.sina_contract(code)
                if points:
                    contracts.append((code, month, points))
            except Exception:
                pass
            month += 1
            if month == 13:
                year, month = year + 1, 1
        if not contracts:
            raise RuntimeError(f"{symbol} 无可用合约")
        latest = max(max(points) for _, _, points in contracts)
        cutoff = (dt.date.fromisoformat(latest) - dt.timedelta(days=10)).isoformat()
        contracts = [item for item in contracts if max(item[2]) >= cutoff]
        dates = sorted({date for _, _, points in contracts for date in points})[-5:]
        labels = [f"{month}月" for _, month, _ in contracts]
        datasets = []
        for i, date in enumerate(dates):
            values = []
            for _, _, points in contracts:
                eligible = [d for d in points if d <= date]
                values.append(points[max(eligible)] if eligible else None)
            datasets.append({"label": date, "data": values, "borderColor": COLORS[i % len(COLORS)], "borderWidth": 1.5})
        return {"labels": labels, "datasets": datasets}

    def load_curves(self):
        for symbol, key in [("NI", "ni_curve"), ("SS", "ss_curve")]:
            try:
                self.put(key, self.shfe_curve(symbol), {"type": "sina-contracts", "symbol": symbol})
            except Exception as error:
                self.warn(f"月间结构 {symbol}", error)
        try:
            price = self.zhiji("FU00014810", "2026-01-01")
            spread03 = self.zhiji("a10018357", "2026-01-01")
            self.put("lme03", self.direct_chart(spread03, "LME镍0-3升贴水"),
                     {"type": "zhiji", "indicator": "a10018357", "unit": "美元/吨"})
            spread15 = self.zhiji("j02797786", "2026-01-01")
            spread27 = self.zhiji("j02797787", "2026-01-01")
            common = sorted(set(price) & set(spread03) & set(spread15) & set(spread27))[-5:]
            datasets = []
            for i, date in enumerate(common):
                raw = [price[date] + spread03[date], price[date], price[date] - spread15[date], price[date] - spread27[date]]
                datasets.append({"label": date, "data": raw, "borderColor": COLORS[i % len(COLORS)], "borderWidth": 1.5})
            self.put("lme_curve", {"labels": ["0M", "3M", "15M", "27M"], "datasets": datasets},
                     {"type": "zhiji", "indicators": ["FU00014810", "a10018357", "j02797786", "j02797787"]})
        except Exception as error:
            self.warn("LME月间结构", error)

    def load_cost_profit(self):
        workbook = load_workbook(B01, read_only=True, data_only=True)
        try:
            rows = []
            for row in workbook["NPI利润"].iter_rows(min_row=18, min_col=3, max_col=43, values_only=True):
                date, price, cost = row[0], number(row[14]), number(row[40])
                if isinstance(date, (dt.date, dt.datetime)) and price is not None and cost is not None:
                    rows.append((date.strftime("%Y-%m-%d"), price, cost, price - cost))
            rows = rows[-600:]
            self.put("cost_npi_profit", {"labels": [r[0] for r in rows], "datasets": [
                {"label": "山东RKEF成本", "data": [r[2] for r in rows], "borderColor": COLORS[1]},
                {"label": "山东RKEF理论利润", "data": [r[3] for r in rows], "borderColor": COLORS[0]},
            ]}, {"type": "B01", "sheet": "NPI利润", "formula": "Q高镍铁价格-AQ山东RKEF成本", "unit": "元/镍点"})
            if rows:
                self.latest["smelting_profit"] = [rows[-1][0], rows[-1][3]]
            rows = []
            for row in workbook["SS利润"].iter_rows(min_row=34, min_col=3, max_col=46, values_only=True):
                date, integrated, npi, scrap = row[0], number(row[38]), number(row[40]), number(row[42])
                if isinstance(date, (dt.date, dt.datetime)) and any(v is not None for v in [integrated, npi, scrap]):
                    rows.append((date.strftime("%Y-%m-%d"), integrated, npi, scrap))
            rows = rows[-600:]
            self.put("cost_ss_profit", {"labels": [r[0] for r in rows], "datasets": [
                {"label": "一体化利润率", "data": [r[1] * 100 if r[1] is not None else None for r in rows], "borderColor": COLORS[0]},
                {"label": "高镍铁利润率", "data": [r[2] * 100 if r[2] is not None else None for r in rows], "borderColor": COLORS[1]},
                {"label": "废不锈钢利润率", "data": [r[3] * 100 if r[3] is not None else None for r in rows], "borderColor": COLORS[2]},
            ]}, {"type": "B01", "sheet": "SS利润", "columns": ["AO", "AQ", "AS"], "unit": "%"})
        finally:
            workbook.close()

    def load_global_stock(self):
        shfe = self.seasonal_latest("inventory_shfe")
        social = self.latest["social_stock"]
        lme = self.latest["lme_stock"]
        if all(item[1] is not None for item in [shfe, social, lme]):
            self.latest["global_stock"] = [lme[0], shfe[1] + social[1] + lme[1]]
        try:
            lme_points = next(iter(self.mirror("niStockLmeSum").values()))
            points = {date: value + (shfe[1] or 0) + (social[1] or 0) for date, value in lme_points.items()}
            self.put("overview_global_stock", self.direct_chart(points, "LME+SHFE仓单+社库（最新国内值平推）"),
                     {"type": "derived", "formula": "LME日度 + 最新SHFE仓单 + 最新社库", "note": "国内周度值平推，仅作显性库存近似"})
        except Exception as error:
            self.warn("全球显性库存", error)

    def balance_block(self, rows, forecast_start=None):
        if not rows:
            return {"labels": [], "supply": [], "demand": [], "balance": [], "cumulative": [],
                    "forecast": [], "actualThrough": None, "summary": {}}
        labels = [row[0] for row in rows]
        supply = [row[1] for row in rows]
        demand = [row[2] for row in rows]
        balance = [row[3] for row in rows]
        cumulative = []
        running = 0
        for label, value in zip(labels, balance):
            if label.endswith("-01"):
                running = 0
            running += value
            cumulative.append(running)
        forecast = [bool(forecast_start and label >= forecast_start) for label in labels]
        actual_indices = [i for i, flag in enumerate(forecast) if not flag]
        actual_index = actual_indices[-1] if actual_indices else 0
        actual_through = labels[actual_index]
        ytd = sum(value for label, value in zip(labels, balance) if label[:4] == actual_through[:4] and label <= actual_through)
        return {"labels": labels, "supply": supply, "demand": demand, "balance": balance,
                "cumulative": cumulative, "forecast": forecast, "actualThrough": actual_through,
                "summary": {"month": actual_through, "balance": balance[actual_index], "ytdBalance": ytd,
                            "unit": "吨镍", "source": "B01可核实月度平衡表"}}

    def load_balance(self):
        result = {"mineral": self.balance_block([]), "refined": self.balance_block([])}
        workbook = load_workbook(B01, read_only=True, data_only=True)
        try:
            rows = []
            sheet = workbook["中国平衡（NPI）"]
            header_rows = list(sheet.iter_rows(min_row=31, max_row=32, min_col=2, max_col=34, values_only=True))
            headers = [top or sub for top, sub in zip(*header_rows)]
            supply_col = headers.index("印尼+中国NPI产量")
            demand_col = headers.index("表观消费")
            for row in sheet.iter_rows(min_row=250, min_col=2, max_col=34, values_only=True):
                date, supply, demand = row[0], number(row[supply_col]), number(row[demand_col])
                if isinstance(date, (dt.date, dt.datetime)) and None not in (supply, demand):
                    supply, demand = supply * 0.0001, demand * 0.0001
                    if supply == demand == 0:
                        continue
                    rows.append((date.strftime("%Y-%m"), supply, demand, supply - demand))
            rows = rows[-36:]
            forecast_start = next((label for label, _, _, _ in rows if label >= "2026-10"), None)
            result["mineral"] = self.balance_block(rows, forecast_start)
            rows = []
            for row in workbook["中国平衡（电镍）"].iter_rows(min_row=63, min_col=2, max_col=20, values_only=True):
                date, production, net_import, reserve, demand = row[0], number(row[3]), number(row[11]), number(row[12]), number(row[18])
                if isinstance(date, (dt.date, dt.datetime)) and None not in (production, net_import, reserve, demand):
                    supply = production + net_import + reserve
                    if supply == demand == 0:
                        continue
                    rows.append((date.strftime("%Y-%m"), supply, demand, supply - demand))
            rows = rows[-36:]
            forecast_start = next((label for label, _, _, _ in rows if label >= "2026-09"), None)
            result["refined"] = self.balance_block(rows, forecast_start)
        except Exception as error:
            self.warn("B01月度平衡", error)
        finally:
            workbook.close()
        return result

    def load_cost_samples(self):
        workbook = xlrd.open_workbook(str(CRU_COST), on_demand=True)
        try:
            sheet = workbook.sheet_by_name("League Data")
            period = str(sheet.cell_value(12, 1))
            samples = []
            for row in range(16, sheet.nrows):
                operation = str(sheet.cell_value(row, 0)).strip()
                cost = number(sheet.cell_value(row, 7))
                production = number(sheet.cell_value(row, 3))
                if not operation or operation.startswith("Totals") or cost is None or production is None:
                    continue
                samples.append({
                    "operation": operation, "country": str(sheet.cell_value(row, 1)), "period": period,
                    "metric": "Cash Cost (C1)", "costUsd": cost * 2204.62262185,
                    "production": production * 453.59237, "original": f"C1 {cost:.4f} 美元/磅；产量 {production:.3f} Mlbs",
                    "source": "CRU Nickel Industry Costs Q3 2026 · League Data", "url": CRU_COST.as_posix(),
                    "rank": number(sheet.cell_value(row, 2)), "centile": number(sheet.cell_value(row, 6)),
                })
            return samples
        except Exception as error:
            self.warn("CRU成本", error)
            return []
        finally:
            workbook.release_resources()

    def load_financial(self):
        workbook = load_workbook(FINANCIAL, read_only=True, data_only=True)
        projects, elasticity = [], []
        supply = {"matte": {}, "mhp": {}}
        try:
            for sheet in workbook.worksheets:
                if sheet.title == "更新日志":
                    continue
                rows = sheet.iter_rows(values_only=True)
                next(rows)
                for row in rows:
                    company, country, project = row[0], row[1], row[2]
                    if not company or not project:
                        continue
                    q2 = number(row[21])
                    reason, guidance, note = row[23], row[24], row[25]
                    basis = f"{sheet.title} · {project}"
                    if q2 is not None:
                        annualized = q2 * 4
                        elasticity.append({"name": str(company), "ticker": str(company), "basis": basis,
                                           "mineTons": annualized, "grossProfitPer10k": annualized * 10000 / 100000000,
                                           "period": "2026Q2年化", "source": FINANCIAL.as_posix()})
                    if country == "印尼":
                        projects.append({
                            "project": str(project), "company": str(company), "region": "印度尼西亚",
                            "certainty": "财报已披露" if q2 is not None else "持续跟踪",
                            "certaintyClass": "high" if q2 is not None else "watch",
                            "certaintyReason": "2026Q2实际产量" if q2 is not None else "本季未披露",
                            "status": str(reason or "在产"), "start": "在产项目", "capacity": str(guidance or "未披露"),
                            "inc26": 0, "inc27": 0, "note": str(note or "增量预测未核实，不测算"),
                            "production26Q2": q2, "source": FINANCIAL.as_posix(),
                        })
                    text = str(project)
                    kind = "mhp" if "MHP" in text.upper() else ("matte" if any(word in text for word in ["冰镍", "镍锍"]) else None)
                    if kind and q2 is not None:
                        supply[kind][f"{company} · {project}"] = q2
            for key, target in [("matte", "supply_matte"), ("mhp", "supply_mhp")]:
                values = supply[key]
                if values:
                    self.put(target, {"labels": ["2026Q2"], "datasets": [{
                        "label": name, "data": [value], "borderColor": COLORS[i % len(COLORS)],
                    } for i, (name, value) in enumerate(values.items())]},
                        {"type": "financial", "path": FINANCIAL.as_posix(), "period": "2026Q2", "unit": "吨镍"})
            return projects, elasticity
        except Exception as error:
            self.warn("财报项目/弹性", error)
            return [], []
        finally:
            workbook.close()

    def warehouse(self):
        output = []
        for name, chart_code in [("LME镍库存", "niStockLmeSum"), ("无锡不锈钢库存", "ssStockWuXiSum"),
                                 ("佛山不锈钢库存", "ssStockFoShanSum")]:
            try:
                values = next(iter(self.mirror(chart_code).values()))
                dates = sorted(values)
                i = len(dates) - 1
                output.append({"name": name, "date": dates[i], "latest": values[dates[i]],
                               "d5": values[dates[i]] - values[dates[max(0, i - 5)]],
                               "d20": values[dates[i]] - values[dates[max(0, i - 20)]]})
            except Exception as error:
                self.warn(f"仓库 {name}", error)
        return output


def finite_tree(value, path="root"):
    if isinstance(value, float) and not math.isfinite(value):
        raise AssertionError(f"非有限数值 {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            finite_tree(item, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            finite_tree(item, f"{path}[{i}]")


def validate(data):
    missing = [key for key in ["charts", "latest", "sourceMeta", "tech", "kline", "liveQuote", "social",
                                "warehouse", "projects", "projectTotals", "monthlyBalance", "costSamples",
                                "companyElasticity", "financial", "meta"] if key not in data]
    assert not missing, f"缺顶层键 {missing}"
    for key in REQUIRED:
        chart = data["charts"][key]
        assert isinstance(chart.get("labels"), list) and isinstance(chart.get("datasets"), list), key
        assert len(chart["labels"]) == 0 or all(
            len(dataset["data"]) == len(chart["labels"]) for dataset in chart["datasets"]
        ), f"日期-值数量不一致 {key}"
    for key, value in data["latest"].items():
        assert isinstance(value, list) and len(value) == 2, f"latest结构 {key}"
    for block in data["monthlyBalance"].values():
        lengths = {len(block[key]) for key in ["labels", "supply", "demand", "balance", "cumulative", "forecast"]}
        assert len(lengths) == 1, "月度平衡数组长度不一致"
    finite_tree(data)


def inject(data_json):
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    start_marker, end_marker = "const DATA=", ";\n</script>"
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("未找到精确标记 const DATA=")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        raise RuntimeError("未找到精确标记 ;\\nconst STATIC_HOST=")
    updated = text[:start] + start_marker + data_json + text[end:]
    path.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="构建镍与不锈钢面板 data.json")
    parser.add_argument("--inject", action="store_true", help="同时注入 index.html 的 DATA 精确标记")
    parser.add_argument("--offline", action="store_true", help="只用本地 Excel/镜像，不访问 zhiji/新浪")
    parser.add_argument("--output", default=str(ROOT / "data.json"))
    args = parser.parse_args()
    build = Build(offline=args.offline)
    steps = [
        ("Excel原生图", build.load_bindings), ("行情", build.load_market), ("直连与镜像", build.load_direct),
        ("月间结构", build.load_curves), ("成本利润", build.load_cost_profit), ("全球库存", build.load_global_stock),
    ]
    for name, function in steps:
        try:
            function()
        except Exception as error:
            build.warn(name, error)
    projects, elasticity = build.load_financial()
    data = {
        "charts": build.charts,
        "latest": build.latest,
        "sourceMeta": {"charts": build.sources, "workbooks": {"ND": ND.as_posix(), "B01": B01.as_posix(),
                       "CRU": CRU_COST.as_posix(), "financial": FINANCIAL.as_posix()},
                       "priority": ["本地镜像/已核实Excel原生图", "zhiji/新浪直连", "合法空结构"],
                       "notes": ["tc_yunnan为遗留键，镍面板无该口径，保持null", "贸易商同业/下游未找到可靠源，保持null",
                                 "monthlyBalance仅采用B01可核实列", "所有源工作簿只读，未保存"]},
        "tech": [], "kline": {}, "liveQuote": build.live_quote, "social": [],
        "warehouse": build.warehouse(), "projects": projects,
        "projectTotals": {"highCount": sum(p["certaintyClass"] == "high" for p in projects),
                          "inc26": sum(p["inc26"] for p in projects), "inc27": sum(p["inc27"] for p in projects)},
        "monthlyBalance": build.load_balance(), "costSamples": build.load_cost_samples(),
        "globalBalanceBase": 0.7, "intermediateConversion": 1.0,
        "companyElasticity": elasticity,
        "financial": {"path": FINANCIAL.as_posix(), "projects": len(projects), "elasticityRows": len(elasticity),
                      "latestPeriod": "2026Q2"},
        "meta": {"commodity": "nickel-stainless", "builtAt": dt.datetime.now().isoformat(timespec="seconds"),
                 "dataDate": dt.date.today().isoformat(), "warnings": build.warnings,
                 "requiredCanvasIds": REQUIRED, "emptyCharts": [key for key, chart in build.charts.items()
                                                               if not chart["labels"] or not chart["datasets"]]},
    }
    validate(data)
    output = Path(args.output)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    output.write_text(payload, encoding="utf-8")
    if args.inject:
        inject(payload)
    nonempty = sum(bool(chart["labels"] and chart["datasets"]) for chart in data["charts"].values())
    print(json.dumps({
        "output": str(output), "charts": len(data["charts"]), "nonemptyCharts": nonempty,
        "latest": data["latest"], "balance": {key: len(value["labels"]) for key, value in data["monthlyBalance"].items()},
        "costSamples": len(data["costSamples"]), "projects": len(data["projects"]),
        "companyElasticity": len(data["companyElasticity"]), "warnings": data["meta"]["warnings"],
        "injected": args.inject,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
