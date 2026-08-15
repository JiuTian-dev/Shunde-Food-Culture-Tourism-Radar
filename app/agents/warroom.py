"""第8步 · 城市战情室 Agent：加热/转向/降温 决策 + 一页简报。

监测数据为演示用「模拟采集」（确定性生成，永不中断）。接入真实平台数据时
只需替换 _mock_feed 为真实拉取。
"""
import json
from datetime import date

from .. import config
from . import base

_SHAPE = [0.30, 0.55, 0.85, 1.00, 0.78, 0.52, 0.34]


def _mock_feed(forge_payload, mission):
    three = ((forge_payload.get("spark") or {}).get("three")) or {}
    boom = (three.get("爆点指数") or {}).get("score", 70)
    feed = []
    for i, shape in enumerate(_SHAPE, 1):
        feed.append({
            "day": i,
            "exposure": round(boom * 18 * shape),
            "exposure_unit": "万次",
            "outbound_ratio": round(30 + i * 4),
            "positive_ratio": round(96 - i),
            "shop_flow_gain": round(shape * 200),
            "orders": round(shape * 800),
            "food_safety_complaints": 0,
        })
    return feed


def _advice(feed):
    peak = max(f["exposure"] for f in feed)
    last = feed[-1]["exposure"]
    if last >= peak * 0.7:
        act, why = "加热", "声量仍在高位，追加官方投放与二创激励，把热度推向全国"
    elif last >= peak * 0.4:
        act, why = "转向", "第一波声量回落，启动第二阶段话题与镇街联动"
    else:
        act, why = "降温", "热度见顶，转入沉淀转化与产能消化，防止反噬"
    return {"action": act, "reason": why, "action_scale": "7天观察窗口"}


def _rule_warroom(forge_payload, mission):
    concept = forge_payload.get("concept", {}) or {}
    formula = forge_payload.get("formula", {}) or {}
    topic = concept.get("topic_name", "顺德")
    shop_name = forge_payload.get("shop_name", "顺德老店")
    feed = _mock_feed(forge_payload, mission)
    adv = _advice(feed)
    peak_day = max(feed, key=lambda f: f["exposure"])
    genes = "、".join(forge_payload.get("dominant_genes") or ["人物", "情绪"])
    brief = {
        "标题": f"《{topic}》战情简报",
        "日期": date.today().isoformat(),
        "今日头条": f"话题进入第 {peak_day['day']} 天峰值，单日曝光 {peak_day['exposure']} 万次，外地占比 {peak_day['outbound_ratio']}%",
        "为什么火": f"创意公式强度 {formula.get('intensity')}%，六因子乘积驱动；主基因：{genes}",
        "带来多少消费": f"预计到店客流 +{peak_day['shop_flow_gain']}%，订单 {peak_day['orders']} 单/日，食安投诉 {peak_day['food_safety_complaints']} 起",
        "什么风险在积累": "排队过载与跟风模仿是主要风险，需按作战包产能预案限流",
        "明天做什么": f"{adv['action']}：{adv['reason']}",
    }
    return {
        "shop_name": shop_name,
        "topic": topic,
        "monitor_feed": feed,
        "advice": adv,
        "leader_brief": brief,
        "generated_by": "规则引擎（模拟采集：演示用，可替换为真实数据源）",
    }


SYSTEM = ("你是「城市战情室」Agent。基于监测数据给出加热/转向/降温决策，并产出给领导看的"
          "一页简报。输出严格 JSON：{\"warroom\":{...}}")


def warroom(forge_payload: dict, mission: dict | None = None, use_llm: bool = True):
    sid = f"war-{forge_payload.get('shop_id', 'shop')}-{forge_payload.get('event_id', 'ev')}"
    user = json.dumps({"创意方案": forge_payload, "任务书": mission}, ensure_ascii=False)
    payload, source, model = base.agent_run(
        "warroom", sid, SYSTEM, user,
        lambda: _rule_warroom(forge_payload, mission), "warroom", use_llm=use_llm)
    # 结构校验：决策落点必须有核心字段，LLM 输出不符时回退规则
    if not isinstance(payload, dict) or "advice" not in payload or "leader_brief" not in payload:
        print("[warroom] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_warroom(forge_payload, mission), "rule", None
    return payload, source, model
