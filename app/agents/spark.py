"""星火指数 Agent：9 维 100 分 + 爆点/长红/留量三指。

定位：作为「叠加评分层」，不改 data_loader 的 5 维契约与前端读取的
scores/index/level 字段；由现有档案 + 诊断 + 事件库推导更决策导向的指标。
"""
import json
from datetime import date

from .. import config, data_loader
from . import base

DIMENSIONS = [
    ("在地独特性", 15), ("人物故事力", 15), ("情绪共鸣度", 15),
    ("短视频视觉力", 10), ("用户参与性", 10), ("当前热点匹配度", 10),
    ("线下消费转化力", 10), ("城市承接能力", 10), ("风险可控性", 5),
]

_REVERSE_WORDS = ("佛系", "反套路", "耿直", "拒绝", "劝退", "别来", "怼", "反差", "不按常理", "有意思", "吐槽")
_PARTICIPATE_KW = ("挑战", "比赛", "试吃", "DIY", "互动", "现做", "现切", "现宰", "试玩")


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(round(v))))


def _score_dim(shop, name):
    pot = shop.get("potentials", {}) or {}
    owner = shop.get("owner", {}) or {}
    craft = shop.get("craft", {}) or {}
    pricing = shop.get("pricingCapacity", {}) or {}
    risks = shop.get("risks", []) or []
    sig = owner.get("signatureLines") or []
    personality = owner.get("personality", "")
    rarity = craft.get("rarity") or 0

    if name == "在地独特性":
        s = rarity * 20; ev = [f"稀缺度 rarity={rarity}"]
        if craft.get("heritage"):
            s += 12; ev.append(f"传承：{craft['heritage']}")
        if shop.get("district"):
            s += 8; ev.append(f"镇街归属：{shop['district']}")
        return _clamp(s), "；".join(ev)
    if name == "人物故事力":
        s = pot.get("故事叙事性", 60) * 0.6; ev = [f"故事叙事性 {pot.get('故事叙事性', 60)}"]
        if sig:
            s += min(25, len(sig) * 8); ev.append(f"{len(sig)} 句口头禅")
        if personality:
            s += 10 if any(w in personality for w in _REVERSE_WORDS) else 0
            ev.append(f"人设：{personality[:14] or '—'}")
        if owner.get("background"):
            s += 8; ev.append("有背景故事")
        return _clamp(s), "；".join(ev)
    if name == "情绪共鸣度":
        s = pot.get("情绪共鸣度", 60); ev = [f"情绪共鸣度 {s}"]
        if sig:
            s += 8; ev.append(f"口头禅可共鸣（{len(sig)}句）")
        return _clamp(s), "；".join(ev)
    if name == "短视频视觉力":
        s = (pot.get("风味品相度", 60) + pot.get("素材续航度", 60)) / 2
        ev = [f"品相 {pot.get('风味品相度', 60)} + 续航 {pot.get('素材续航度', 60)}"]
        if craft.get("visualImpact"):
            s += 10; ev.append(f"视觉爆点：{str(craft['visualImpact'])[:20]}")
        return _clamp(s), "；".join(ev)
    if name == "用户参与性":
        s = pot.get("素材续航度", 50) * 0.5 + 20; ev = []
        kw = "".join(craft.get("keywords", []))
        if sig:
            s += 10; ev.append("口头禅可被玩梗二创")
        if any(x in kw for x in _PARTICIPATE_KW):
            s += 15; ev.append("有『可参与/可围观』制作动作")
        ev.append(f"素材续航 {pot.get('素材续航度', 50)}")
        return _clamp(s), "；".join(ev)
    if name == "当前热点匹配度":
        recent = [e for e in data_loader.load_events() if _is_recent(e)]
        kw_set = set(craft.get("keywords", [])) | {shop.get("category", "")}
        best = 0
        for e in recent:
            hit = len(kw_set & set(e.get("labels", [])))
            if e.get("category") == shop.get("category"):
                hit += 2
            best = max(best, hit)
        s = 40 + best * 12
        ev = [f"近3月案例匹配 hit={best}" if best else "暂无直接近期对标"]
        return _clamp(s), "；".join(ev)
    if name == "线下消费转化力":
        s = shop.get("_index", 60) * 0.5 + 30; ev = [f"5维指数 {shop.get('_index', 60)}"]
        if pricing.get("priceBand"):
            s += 5; ev.append(f"定价 {str(pricing['priceBand'])[:16]}")
        return _clamp(s), "；".join(ev)
    if name == "城市承接能力":
        cap = str(pricing.get("capacity", ""))
        s = 90 if "大" in cap else (65 if "中" in cap else 45)
        ev = [f"接待 {cap[:16] or '未知'}"]
        if shop.get("operating"):
            s += 5; ev.append("营业中")
        return _clamp(s), "；".join(ev)
    if name == "风险可控性":
        s = 100; ev = []
        for r in risks:
            s -= 18; ev.append(r[:24] + ("…" if len(r) > 24 else ""))
        if not risks:
            ev.append("档案无显式风险项")
        return _clamp(s), "；".join(ev)
    return 60, "规则默认"


def _is_recent(event, months=3):
    try:
        y, m = (int(x) for x in str(event.get("time", "")).split("-")[:2])
    except (ValueError, TypeError):
        return False
    cur = date.today()
    return (cur.year - y) * 12 + (cur.month - m) <= months


def _label(v):
    return "强" if v >= 75 else ("中" if v >= 60 else "待观察")


def _rule_spark(shop, diag):
    dims = {}
    for name, w in DIMENSIONS:
        score, ev = _score_dim(shop, name)
        dims[name] = {"weight": w, "score": score, "evidence": ev}
    idx = sum(d["weight"] / 100 * d["score"] for d in dims.values())
    pot = shop.get("potentials", {}) or {}
    D = {k: d["score"] for k, d in dims.items()}
    boom = _clamp(0.40 * D["人物故事力"] + 0.30 * D["情绪共鸣度"] + 0.30 * D["短视频视觉力"])
    long = _clamp(0.30 * pot.get("素材续航度", 60) + 0.30 * D["情绪共鸣度"] + 0.20 * D["城市承接能力"] + 0.20 * D["在地独特性"])
    stay = _clamp(0.40 * D["线下消费转化力"] + 0.30 * D["城市承接能力"] + 0.20 * D["在地独特性"] + 0.10 * D["风险可控性"])
    three = {
        "爆点指数": {"score": boom, "label": _label(boom), "basis": "首轮关注力：人物×情绪×视觉"},
        "长红指数": {"score": long, "label": _label(long), "basis": "热度维持力：续航×承接×独特性"},
        "留量指数": {"score": stay, "label": _label(stay), "basis": "转化力：消费×承接×风险"},
    }
    if idx >= 75:
        verdict = "A类 · 星火可期"
    elif idx >= 60:
        verdict = "B类 · 建议观察"
    else:
        verdict = "C类 · 先补短板"
    return {
        "shop_id": shop.get("id"),
        "shop_name": shop.get("name"),
        "spark_index": round(idx, 1),
        "dimensions": dims,
        "three": three,
        "verdict": verdict,
        "generated_by": "规则引擎（星火指数=9维加权；三指=决策导向推导）",
        "note": "叠加评分层：不改5维爆款指数契约，供政府决策用",
    }


SYSTEM = (
    "你是「星火指数」Agent。基于店铺档案与诊断报告，按9维（在地独特性15/人物故事力15/"
    "情绪共鸣度15/短视频视觉力10/用户参与性10/当前热点匹配度10/线下消费转化力10/"
    "城市承接能力10/风险可控性5）打分，并给爆点/长红/留量三指。输出严格 JSON："
    '{"spark":{...}}'
)


def spark(shop_id: str, use_llm: bool = True):
    """计算星火指数 + 三指。返回 (payload, source, model)。"""
    shop = data_loader.get_shop(shop_id)
    if not shop:
        raise ValueError(f"未找到店铺 {shop_id}")
    diag = data_loader.load_diagnosis(shop_id)
    clean = {k: v for k, v in shop.items() if not k.startswith("_")}
    user = json.dumps({"店铺档案": clean, "诊断报告": diag}, ensure_ascii=False)
    payload, source, model = base.agent_run(
        "spark", shop_id, SYSTEM, user,
        lambda: _rule_spark(shop, diag), "spark", use_llm=use_llm)
    if not isinstance(payload, dict) or "dimensions" not in payload or "three" not in payload:
        print("[spark] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_spark(shop, diag), "rule", None
    return payload, source, model
