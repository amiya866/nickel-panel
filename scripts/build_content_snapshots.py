import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NEWS = Path("D:/Kimi/整合研究站_中哲复制/site/data/news_latest.json")
ZSXQ = Path("D:/Kimi/金属总网/网站构建/小作文平台/知识星球/data/zsxq_metals.json")
CAIBAO = Path("D:/Kimi/caibao-hub/data/news.json")
KEYWORDS = re.compile(r"镍|不锈钢|RKAB|Nornickel|NPI|MHP|高冰镍|硫酸镍", re.I)
SOURCE_NAMES = {"jin10": "金十数据", "cs": "CS财经", "eastmoney": "东方财富", "sina": "新浪财经", "ah": "先讯"}


def main():
    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    policy = []
    if NEWS.exists():
        raw = json.loads(NEWS.read_text(encoding="utf-8"))
        for source, rows in raw.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                content = str(row.get("content") or "")
                match = re.search(r"【([^】]+)】", content)
                if not match or not KEYWORDS.search(match.group(1)):
                    continue
                summary = content[match.end():].strip()
                policy.append({"date": str(row.get("time") or row.get("ts") or "")[:10], "title_zh": match.group(1).strip(), "summary_zh": summary[:360], "category": "镍与不锈钢", "source": SOURCE_NAMES.get(source, source), "url": row.get("url") or ""})
    if CAIBAO.exists():
        for row in json.loads(CAIBAO.read_text(encoding="utf-8")):
            if row.get("commodity") != "镍":
                continue
            policy.append({"date": row.get("date") or "", "title_zh": row.get("title") or "", "summary_zh": row.get("summary") or "", "category": row.get("category") or "镍产业", "source": row.get("source") or "caibao-hub", "url": row.get("url") or ""})
    policy.sort(key=lambda x: x["date"], reverse=True)
    seen, unique = set(), []
    for item in policy:
        if item["title_zh"] in seen:
            continue
        seen.add(item["title_zh"])
        unique.append(item)
    (ROOT / "policy.json").write_text(json.dumps({"updated_at": now, "items": unique[:12]}, ensure_ascii=False, indent=2), encoding="utf-8")

    social = []
    if ZSXQ.exists():
        raw = json.loads(ZSXQ.read_text(encoding="utf-8"))
        for row in raw.get("by_comm", {}).get("ni", []):
            social.append({"date": row.get("date"), "title": row.get("title"), "summary": row.get("summary"), "platform": "知识星球", "author": row.get("source") or "纪要小能手", "url": row.get("url") or ""})
    (ROOT / "social.json").write_text(json.dumps({"updated_at": now, "items": social[:12]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"policy": len(unique[:12]), "social": len(social[:12]), "updated_at": now}, ensure_ascii=False))


if __name__ == "__main__":
    main()
