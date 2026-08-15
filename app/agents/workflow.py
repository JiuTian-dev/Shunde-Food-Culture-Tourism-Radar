"""工作流编排器：把 8 个环节串成一条可运行的策源流水线。

数据流：任务书 → 雷达 → [自动选店/选案例] → 考古(资产卡) → 星火(指数) →
       解码(8基因) → 迁移(三档) → 熔炉(创意方案) → [政府人工闸门] → 作战包 → 战情室。
每次运行生成一个 run_id，全程落盘 output/workflow/。
"""
import json
from datetime import date, datetime

from .. import config, data_loader
from . import base, mission, radar, excavator, codebreaker, migrator, forge, ops_kit, warroom, spark

WORKFLOW_DIR = base.OUTPUT_DIR / "workflow"


def _pick_shop(radar_payload, focus=None):
    if focus:
        return data_loader.get_shop(focus)
    for opp in radar_payload.get("top_opportunities", []):
        if opp.get("kind") == "本地弱信号":
            s = data_loader.get_shop(opp.get("source"))
            if s:
                return s
    return data_loader.get_shop("SD-P01")  # 兜底锚点：莫氏鸡煲


def _pick_event(radar_payload, focus=None):
    if focus:
        for e in data_loader.load_events():
            if e.get("id") == focus:
                return e
    for opp in radar_payload.get("top_opportunities", []):
        if opp.get("kind") == "全网热点借势":
            for e in data_loader.load_events():
                if e.get("id") == opp.get("source"):
                    return e
    events = data_loader.load_events()
    return events[0] if events else None


def _run_id():
    i = 1
    while True:
        rid = f"WF-{date.today():%Y%m%d}-{i:03d}"
        if not (WORKFLOW_DIR / f"{rid}.json").exists():
            return rid
        i += 1


def _persist(record):
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    (WORKFLOW_DIR / f"{record['run_id']}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def run(task_type="承接网络热点", city="顺德", budget=None, window=None, audience=None,
        resources=None, focus_shop_id=None, focus_event_id=None, approve=True, use_llm=True):
    """端到端跑一轮策源流水线，返回运行记录。approve=True 时自动过政府闸门。"""
    rid = _run_id()
    stages, log = {}, []

    def stage(name, src, payload, brief=""):
        stages[name] = {"source": src, "payload": payload}
        log.append({"stage": name, "source": src, "brief": brief})

    m, ms, _ = mission.mission(task_type, city, budget, window, audience, resources, use_llm=use_llm)
    stage("mission", ms, m, f"任务：{m['goal']}")

    r, rs, _ = radar.radar(use_llm=use_llm)
    stage("radar", rs, r, f"机会清单 {len(r['top_opportunities'])} 个")

    shop = _pick_shop(r, focus_shop_id)
    event = _pick_event(r, focus_event_id)

    ac, acs, _ = excavator.excavator(shop["id"], use_llm=use_llm)
    stage("asset_card", acs, ac, f"资产卡：{shop['name']}")

    sp, sps, _ = spark.spark(shop["id"], use_llm=use_llm)
    stage("spark", sps, sp, f"星火指数 {sp['spark_index']}")

    dc, dcs, _ = codebreaker.codebreaker(event["id"], use_llm=use_llm)
    stage("decode", dcs, dc, f"主基因：{'、'.join(dc['dominant_genes'])}")

    mg, mgs, _ = migrator.migrator(event["id"], shop["id"], use_llm=use_llm)
    stage("migrate", mgs, mg, "三档迁移方案就绪")

    fg, fgs, _ = forge.forge(shop["id"], event["id"], mission=m, use_llm=use_llm,
                             asset=ac, migrate=mg, spark_data=sp)
    stage("forge", fgs, fg, f"创意强度 {fg['formula']['intensity']}% · {fg['concept']['topic_name']}")

    record = {
        "run_id": rid,
        "created": datetime.now().isoformat(timespec="seconds"),
        "mission_id": m.get("mission_id"),
        "shop_id": shop.get("id"), "shop_name": shop.get("name"),
        "event_id": event.get("id"), "event_name": event.get("name"),
        "status": "awaiting_review",
        "decision": None,
        "stages": stages,
        "log": log,
    }
    if approve:
        record = approve_run(record, use_llm=use_llm)
    else:
        _persist(record)
    return record


def approve_run(record: dict, use_llm: bool | None = None):
    """政府人工闸门：审批后进入作战包与战情室。

    作战包/战情室是决策落点，规则输出结构必须可靠；LLM 输出结构不符时
    由各 Agent 内部自动回退规则（见 ops_kit/warroom 的校验）。
    """
    if use_llm is None:
        use_llm = config.LLM_ENABLED
    record["status"] = "approved"
    record["decision"] = {
        "by": "政府决策层",
        "note": "已审批，进入作战包与战情室",
        "decided_at": datetime.now().isoformat(timespec="seconds"),
    }
    fg = record["stages"]["forge"]["payload"]
    m = record["stages"]["mission"]["payload"]
    ok, oks, _ = ops_kit.ops_kit(fg, m, use_llm=use_llm)
    record["stages"]["ops_kit"] = {"source": oks, "payload": ok}
    record["log"].append({"stage": "ops_kit", "source": oks, "brief": "作战包 10 项就绪"})
    wr, wrs, _ = warroom.warroom(fg, m, use_llm=use_llm)
    record["stages"]["warroom"] = {"source": wrs, "payload": wr}
    record["log"].append({"stage": "warroom", "source": wrs, "brief": f"战情室决策：{wr['advice']['action']}"})
    _persist(record)
    return record


def get(run_id: str) -> dict | None:
    p = WORKFLOW_DIR / f"{run_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_runs() -> list[dict]:
    if not WORKFLOW_DIR.exists():
        return []
    runs = []
    for p in sorted(WORKFLOW_DIR.glob("WF-*.json"), reverse=True):
        rec = get(p.stem)
        if rec:
            runs.append({
                "run_id": rec["run_id"], "created": rec.get("created"),
                "shop_name": rec.get("shop_name"), "event_name": rec.get("event_name"),
                "status": rec.get("status"), "decision": rec.get("decision"),
            })
    return runs
