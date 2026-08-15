"""冒烟验证：端到端跑一轮策源流水线（规则路径，不依赖 LLM）。

运行：python scripts/smoke_workflow.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import data_loader
from app.agents import (mission, radar, excavator, codebreaker, migrator,
                        forge, spark, ops_kit, warroom, workflow)

OK = "\033[92m✓\033[0m"
BAD = "\033[91m✗\033[0m"


def check(name, cond, detail=""):
    print(f"{OK if cond else BAD} {name} {detail}")
    if not cond:
        raise SystemExit(1)


def main():
    print("── 顺德美食流量孵化引擎 · 流水线冒烟验证（规则路径）──")
    events = data_loader.load_events()
    check("事件库加载", len(events) >= 20, f"({len(events)} 条)")

    m, ms, _ = mission.mission("承接网络热点", use_llm=False)
    check("任务书", ms == "rule" and m.get("goal"), m.get("mission_id"))

    r, rs, _ = radar.radar(use_llm=False)
    check("雷达", rs == "rule" and len(r["top_opportunities"]) >= 1,
          f"({len(r['hot_signals'])} 热点 / {len(r['weak_signals'])} 弱信号)")

    shop = data_loader.get_shop("SD-P01")
    ac, acs, _ = excavator.excavator(shop["id"], use_llm=False)
    check("资产卡", acs == "rule" and ac.get("shop_name"), ac.get("shop_name"))

    sp, sps, _ = spark.spark(shop["id"], use_llm=False)
    three = {k: v["label"] for k, v in sp["three"].items()}
    check("星火指数", sps == "rule" and sp.get("spark_index") is not None,
          f"星火={sp.get('spark_index')} 三指={three}")

    dc, dcs, _ = codebreaker.codebreaker(events[0]["id"], use_llm=False)
    check("解码", dcs == "rule" and dc.get("dominant_genes"), f"主基因={dc['dominant_genes']}")

    mg, mgs, _ = migrator.migrator(events[0]["id"], shop["id"], use_llm=False)
    check("迁移", mgs == "rule" and len(mg["plans"]) == 3)

    fg, fgs, _ = forge.forge(shop["id"], events[0]["id"], use_llm=False)
    check("熔炉", fgs == "rule" and fg.get("concept") and fg["formula"]["intensity"] > 0,
          f"创意强度={fg['formula']['intensity']}% 话题={fg['concept']['topic_name']}")

    ok, oks, _ = ops_kit.ops_kit(fg, m, use_llm=False)
    check("作战包", oks == "rule" and ok.get("calendar") and len(ok) >= 10, f"({len(ok)} 项)")

    wr, wrs, _ = warroom.warroom(fg, m, use_llm=False)
    check("战情室", wrs == "rule" and wr.get("advice") and wr.get("leader_brief"),
          f"决策={wr['advice']['action']}")

    rec = workflow.run("承接网络热点", use_llm=False, approve=True)
    need = {"mission", "radar", "asset_card", "spark", "decode", "migrate", "forge", "ops_kit", "warroom"}
    check("编排器", rec["status"] == "approved" and need <= set(rec["stages"]), rec["run_id"])

    rec2 = workflow.get(rec["run_id"])
    check("回读落盘", rec2 is not None and rec2["stages"]["forge"]["payload"]["concept"]["topic_name"],
          f"{rec['run_id']} → {rec['stages']['forge']['payload']['concept']['topic_name']}")

    runs = workflow.list_runs()
    check("运行列表", len(runs) >= 1, f"({len(runs)} 条)")

    print("\n全部通过。最终方案核心话题：", rec["stages"]["forge"]["payload"]["concept"]["topic_name"])


if __name__ == "__main__":
    main()
