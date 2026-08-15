"""第1步 · 天眼·Trend Scout 全域热点雷达 Agent。

把事件库中的全网热点、店铺档案里的本地弱信号、资源分布，压缩成
《城市机会信号清单》，为后续寻宝/解码/迁移提供输入。
"""
import json
from collections import Counter
from datetime import date

from .. import config, data_loader
from . import base

_URGENCY = {0: "正在进行", 1: "余温未散", -1: "即将到来"}
_ORDER = {"正在进行": 0, "余温未散": 1, "即将到来": 2, "可复用逻辑": 3, "可借鉴": 4}


def _month_delta(e, cur):
    try:
        y, m = (int(x) for x in str(e.get("time", "")).split("-")[:2])
    except (ValueError, TypeError):
        return None
    return (cur.year - y) * 12 + (cur.month - m)


def _hot_signals(events):
    cur = date.today()
    out = []
    for e in events:
        md = _month_delta(e, cur)
        if md is None or abs(md) > 3:
            continue
        if md in _URGENCY:
            urgency = _URGENCY[md]
        else:
            urgency = "可复用逻辑" if md > 0 else "可借鉴"
        peak = (e.get("peakMetrics") or {}).get("peak_views", "—")
        out.append({
            "event_id": e.get("id"), "name": e.get("name"), "time": e.get("time"),
            "category": e.get("category"), "labels": e.get("labels", []),
            "factorType": e.get("factorType"), "peak_views": peak, "urgency": urgency,
            "why_now": f"距今日 {abs(md)} 个月，{urgency}；爆点逻辑可映射到顺德同类机会",
        })
    out.sort(key=lambda x: _ORDER.get(x["urgency"], 5))
    return out


def _weak_signals(shops):
    out = []
    for s in shops:
        owner = s.get("owner", {}) or {}
        craft = s.get("craft", {}) or {}
        pot = s.get("potentials", {}) or {}
        sig = owner.get("signatureLines") or []
        kw = "".join(craft.get("keywords", []))
        points = []
        if sig:
            points.append(f"人物口头禅鲜明（{len(sig)}句）")
        if any(w in (owner.get("personality") or "") for w in ("佛系", "反套路", "耿直", "别来", "劝退", "拒绝")):
            points.append("反套路人设")
        if any(x in kw for x in ("挑战", "比赛", "现做", "现切", "互动", "试吃")):
            points.append("制作动作可参与")
        if craft.get("rarity", 0) >= 4:
            points.append("品类稀缺")
        if pot.get("故事叙事性", 0) >= 80 or pot.get("情绪共鸣度", 0) >= 80:
            points.append("情绪价值高")
        if points:
            out.append({
                "shop_id": s.get("id"), "name": s.get("name"),
                "category": s.get("category"), "district": s.get("district"),
                "index": s.get("_index"), "signals": points,
                "why_now": "弱信号组合已具备至少一条爆款基因，缺的只是被城市策源系统看见",
            })
    out.sort(key=lambda x: len(x["signals"]), reverse=True)
    return out


def _resource_map(shops, events):
    districts = Counter(s.get("district") or "未知" for s in shops)
    categories = Counter(s.get("category") or "未知" for s in shops)
    heritage = [s for s in shops if (s.get("craft") or {}).get("heritage")]
    return {
        "district_counts": dict(districts),
        "category_counts": dict(categories),
        "heritage_shops": [{"id": s.get("id"), "name": s.get("name"), "heritage": (s.get("craft") or {}).get("heritage")} for s in heritage],
        "shop_total": len(shops), "event_total": len(events),
    }


def _opportunities(hot, weak):
    out = []
    for i, h in enumerate(hot[:6], 1):
        out.append({"rank": i, "kind": "全网热点借势", "title": h["name"], "source": h["event_id"], "why_now": h["why_now"], "urgency": h["urgency"]})
    for j, w in enumerate(weak[:6], len(out) + 1):
        out.append({"rank": j, "kind": "本地弱信号", "title": f"{w['name']} · {w['district']}", "source": w["shop_id"], "why_now": "；".join(w["signals"])})
    return out


def _rule_radar():
    events = data_loader.load_events()
    shops = data_loader.load_shops()
    hot = _hot_signals(events)
    weak = _weak_signals(shops)
    return {
        "window": "近3个月全网热点 × 全库店铺弱信号",
        "hot_signals": hot,
        "weak_signals": weak,
        "resource_map": _resource_map(shops, events),
        "top_opportunities": _opportunities(hot, weak),
        "generated_by": "规则引擎（事件库×店铺档案）",
    }


SYSTEM = ("你是「天眼·Trend Scout 全域热点雷达」Agent。把全网热点、本地弱信号、资源分布"
          "压缩成《城市机会信号清单》。输出严格 JSON：{\"radar\":{...}}")


def radar(use_llm: bool = True):
    sid = f"radar-{date.today():%Y%m%d}"
    payload, source, model = base.agent_run("radar", sid, SYSTEM, "扫描全域热点与本地弱信号",
                                            _rule_radar, "radar", use_llm=use_llm)
    if not isinstance(payload, dict) or "top_opportunities" not in payload:
        print("[radar] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_radar(), "rule", None
    return payload, source, model
