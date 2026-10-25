import datetime as dt


def monthly(build, points, name):
    return build.direct_chart(points, name, monthly=True)


def apply_freshness(build):
    plate = build.zhiji("a10018953")
    bean = build.zhiji("a10018954")
    social = {date: plate.get(date, 0) + bean.get(date, 0) for date in sorted(set(plate) | set(bean))}
    for key, points, name, indicator in [
        ("inventory_social", social, "SMM纯镍社会库存", "a10018953+a10018954"),
        ("inventory_plate", plate, "SMM国内镍板库存", "a10018953"),
        ("inventory_bean", bean, "SMM国内镍豆库存", "a10018954"),
    ]:
        build.put(key, build.direct_chart(points, name, limit=500), {"type": "zhiji", "indicator": indicator, "unit": "吨"})
    latest = max(social)
    build.latest["social_stock"] = [latest, social[latest]]

    for key, indicator, name in [
        ("demand_ss_import", "a10018706", "中国不锈钢进口量"),
        ("demand_ss_export", "a10018707", "中国不锈钢出口量"),
        ("supply_chrome_import", "a10158279", "中国高碳铬铁进口量"),
    ]:
        points = build.zhiji(indicator)
        build.put(key, monthly(build, points, name), {"type": "zhiji", "indicator": indicator, "unit": "吨" if key != "supply_chrome_import" else "万吨"})
    refined_import = build.zhiji("a10000643")
    refined_export = build.zhiji("a10000647")
    net = {date: refined_import[date] - refined_export[date] for date in sorted(set(refined_import) & set(refined_export))}
    build.put("overview_trade_net", monthly(build, net, "中国电解镍净进口量"),
              {"type": "derived", "formula": "a10000643进口-a10000647出口", "unit": "吨"})

    if build.charts.get("inventory_ss_cold", {}).get("labels") and build.charts.get("inventory_ss_hot", {}).get("labels"):
        cold = build.zhiji("ID01706925")
        hot = build.zhiji("ID01706924")
        total = {date: cold[date] + hot[date] for date in sorted(set(cold) & set(hot))}
        build.put("inventory_ss300", build.direct_chart(total, "300系冷轧+热轧库存", limit=500),
                  {"type": "derived", "formula": "ID01706925+ID01706924", "unit": "吨"})

    if build.series.get("SHFE_STOCK"):
        lme = build.zhiji("a10018390")
        shfe = build.series["SHFE_STOCK"]
        history = {}
        for date in sorted(lme):
            if date < "2022-01-01":
                continue
            shfe_dates = [day for day in shfe if day <= date and (dt.date.fromisoformat(date) - dt.date.fromisoformat(day)).days <= 7]
            social_dates = [day for day in social if day <= date and (dt.date.fromisoformat(date) - dt.date.fromisoformat(day)).days <= 7]
            if shfe_dates and social_dates:
                history[date] = lme[date] + shfe[max(shfe_dates)] + social[max(social_dates)]
        if history:
            build.series["GLOBAL_STOCK"] = history
            build.put("overview_global_stock", build.direct_chart(history, "2022年以来LME+SHFE仓单+SMM社库"),
                      {"type": "derived", "formula": "2022年以来LME+SHFE仓单+SMM社库（周度值平推）"})
            latest = max(history)
            build.latest["global_stock"] = [latest, history[latest]]
