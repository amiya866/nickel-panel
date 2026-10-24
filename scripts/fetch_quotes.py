import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SHANGHAI = ZoneInfo("Asia/Shanghai")
SINA_URL = "https://hq.sinajs.cn/rn=nickel-pages&list=nf_NI0,nf_SS0,nf_CU0,hf_NID"
SINA_HEADERS = {"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0 (Nickel Dashboard)"}
ZHIJI_URL = "https://zhiji-ai.xyz/guan/api/quote"


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pct(last, reference):
    return None if last is None or not reference else (last - reference) / reference * 100


def ratio(numerator, denominator):
    return None if numerator is None or not denominator else numerator / denominator


def clock(value):
    text = str(value or "")
    return f"{text[:2]}:{text[2:4]}:{text[4:]}" if len(text) == 6 and text.isdigit() else text


def fetch_sina_rows():
    request = Request(SINA_URL, headers=SINA_HEADERS)
    with urlopen(request, timeout=30) as response:
        text = response.read().decode("gb18030", errors="replace")
    return {key: value.split(",") for key, value in re.findall(r'var hq_str_(\w+)="([^"]*)";', text)}


def fetch_zhiji_quotes():
    key = os.environ.get("ZHIJI_API_KEY", "").strip() or os.environ.get("ZHIJI_KEY", "").strip()
    if not key:
        return {}
    request = Request(ZHIJI_URL + "?" + urlencode({"symbols": "NI,SS,CU", "key": key}), headers={"User-Agent": "Nickel Dashboard"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = {}
    for item in payload.get("quotes") or payload.get("data") or []:
        product = str(item.get("product") or item.get("resolved_from") or "").upper()
        if product and not item.get("error"):
            result[product] = item
    return result


def zhiji_quote(item, fallback_name, now):
    if not item:
        return None
    return {"symbol": item.get("symbol"), "name": item.get("name") or fallback_name, "last": number(item.get("last")), "change_pct": number(item.get("change_pct")), "time": item.get("time"), "date": now.date().isoformat(), "open_interest": number(item.get("open_interest")), "volume": number(item.get("volume")), "source": "知几实时行情"}


def sina_domestic(row, symbol, fallback_name):
    if not row or len(row) < 18:
        return None
    last = number(row[8])
    reference = next((value for value in (number(item) for item in row[18:]) if value and value > 100), number(row[10]))
    return {"symbol": symbol, "name": row[0] or fallback_name, "last": last, "change_pct": pct(last, reference), "time": clock(row[1]), "date": row[17], "open_interest": number(row[13]), "volume": number(row[14]), "source": "新浪期货行情（回退）"}


def main():
    now = datetime.now(SHANGHAI)
    rows = fetch_sina_rows()
    try:
        zhiji = fetch_zhiji_quotes()
    except Exception:
        zhiji = {}
    ni = zhiji_quote(zhiji.get("NI"), "沪镍", now) or sina_domestic(rows.get("nf_NI0"), "NI0", "沪镍")
    ss = zhiji_quote(zhiji.get("SS"), "不锈钢", now) or sina_domestic(rows.get("nf_SS0"), "SS0", "不锈钢")
    cu = zhiji_quote(zhiji.get("CU"), "沪铜", now) or sina_domestic(rows.get("nf_CU0"), "CU0", "沪铜")
    if not ni or ni.get("last") is None:
        raise RuntimeError("沪镍行情不可用")
    lme_row = rows.get("hf_NID")
    if not lme_row or len(lme_row) < 13:
        raise RuntimeError("Sina LME nickel quote response is incomplete")
    lme_last = number(lme_row[0])
    lme = {"symbol": "NID", "name": lme_row[13] if len(lme_row) > 13 else "LME镍3个月", "last": lme_last, "change_pct": pct(lme_last, number(lme_row[7])), "time": lme_row[6], "date": lme_row[12], "source": "新浪外盘期货准实时"}
    npi = None
    data_path = ROOT / "data.json"
    if data_path.exists():
        try:
            npi = json.loads(data_path.read_text(encoding="utf-8")).get("latest", {}).get("npi_price", [None, None])[1]
        except Exception:
            pass
    as_of = now.isoformat(timespec="seconds")
    payload = {"updated_at": as_of, "source": "知几实时行情优先；新浪回退", "ni": ni, "ss": ss, "lme": lme, "cu": cu, "ratios": {"ni_ss": {"value": ratio(ni.get("last"), ss and ss.get("last")), "as_of": as_of}, "ni_copper": {"value": ratio(ni.get("last"), cu and cu.get("last")), "as_of": as_of}, "npi_refined": {"value": ratio(npi * 100 if npi is not None else None, ni.get("last")), "as_of": as_of}}}
    (ROOT / "quotes.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
