"""第5步 · 灵感熔炉·Idea Forge Agent：创意公式 → 完整传播方案。

创意公式 = 在地真实性 × 人物情绪 × 视觉奇观 × 社交参与 × 时间窗口 × 城市承接力。
产出：六因子评分、创意概念、脚本三件套、传播矩阵、线下承接、媒体与负面预案。
"""
import json

from .. import config, data_loader
from . import base
from . import excavator, migrator, spark


def _find_event(event_id):
    for e in data_loader.load_events():
        if e.get("id") == event_id:
            return e
    return None


def _default_event():
    events = sorted(data_loader.load_events(), key=lambda e: str(e.get("time", "")), reverse=True)
    return events[0] if events else None


def _factors(asset, spark_data, mission):
    profile = asset.get("profile", {}) or {}
    sig = profile.get("signature_lines") or []
    D = {k: (v.get("score") or 0) for k, v in ((spark_data or {}).get("dimensions") or {}).items()}
    facts = {
        "在地真实性": D.get("在地独特性", 70) + (8 if profile.get("heritage") else 0),
        "人物情绪": D.get("人物故事力", 70) + min(10, len(sig) * 3),
        "视觉奇观": D.get("短视频视觉力", 70),
        "社交参与": D.get("用户参与性", 65),
        "时间窗口": 78 if (mission or {}).get("window") else 70,
        "城市承接力": D.get("城市承接能力", 70),
    }
    scores = {k: round(min(100, max(40, v))) for k, v in facts.items()}
    product = 1.0
    for v in scores.values():
        product *= v / 100
    return scores, round(product * 100, 1)


def _scripts(shop_name, hook, profile):
    visual = profile.get("visual_hook") or "成品视觉冲击"
    return {
        "15s": {
            "title": "一句话勾魂", "length": "15秒",
            "scene": [f"{shop_name}门头/制作特写（0-3s）", f"人物出镜说『{hook}』（3-8s）", f"{visual} + 夜色/排队（8-15s）"],
            "voiceover": f"『{hook}』——就这句，评论区见。",
            "on_screen": f"大字文案：{hook}",
        },
        "30s": {
            "title": "反套路短剧情", "length": "30秒",
            "scene": [f"顾客问『{shop_name}有什么好吃的』（0-8s）", f"老板不按套路回应（8-18s）", f"成品上桌视觉反转（18-30s）"],
            "voiceover": "在顺德，你以为的，往往都不是你以为的。",
            "on_screen": "进度条钩子：『30秒告诉你它凭什么火』",
        },
        "180s": {
            "title": "人物故事向", "length": "180秒",
            "scene": [f"老店的一天从凌晨开始（0-40s）", f"老板讲述坚持与拒绝（40-120s）", f"一句『{hook}』点题（120-150s）", f"营业中的烟火气收尾（150-180s）"],
            "voiceover": "这家店在顺德开了几十年，老板说：『{hook}』。",
            "on_screen": "字幕强调：{hook}",
        },
    }


def _matrix(shop_name, hook):
    return {
        "official": {
            "channel": "文旅/镇街官方号", "cadence": "首周1条/2天，之后1条/周",
            "content_ideas": [f"揭秘{shop_name}的一天", "记录一条视频的诞生", "回应网友神评论"],
        },
        "influencer": {
            "channel": "本地美食达人5-10位 + 跨城中腰部1-2位", "cadence": "集中投放7天",
            "content_ideas": [f"『{hook}』挑战", "跨城探店对比", "同款复刻"],
        },
        "merchant": {
            "channel": "商户自账号", "cadence": "每日更新",
            "content_ideas": ["老板日常", "后厨花絮", "营业实况"],
        },
    }


def _offline(shop_name, hook):
    return {
        "activity": f"线下「{hook}」打卡点 + 限定套餐",
        "route": "联动周边地标做一日城市动线（含该店）",
        "coupon": "话题互动抽免单 / 到店核销优惠券",
    }


def _media(shop_name, event):
    return {
        "angle": "人间烟火 + 城市议题，弱化纯营销感",
        "overseas": "评论区/海外社媒搬运做二次发酵",
        "negative_prep": ["食安抽查前置", "排队过载预案", "官方回应口径预埋", "不追负面流量"],
    }


def _rule_forge(shop, event, asset, migrate, spark_data, mission):
    scores, intensity = _factors(asset, spark_data, mission)
    profile = asset.get("profile", {}) or {}
    sig = profile.get("signature_lines") or []
    shop_name = shop.get("name", "")
    hook = sig[0] if sig else shop_name
    plan = (migrate.get("plans") or {}).get("突破档", {})
    topic = f"#顺德{shop_name}的{hook[:10]}"
    concept = {
        "topic_name": topic,
        "hook": hook,
        "story_line": (
            f"开场即钩子（{hook}）→ 冲突（反套路/稀缺）→ 爆点（{profile.get('visual_hook') or '视觉奇观'}）"
            f"→ 情绪落点（老店坚守）→ 留白引导二创"
        ),
        "platform_first": "抖音/视频号首发，小红书种草承接",
        "recommend_gear": plan.get("name") if plan else "突破档",
    }
    return {
        "shop_id": shop.get("id"), "shop_name": shop_name,
        "event_id": event.get("id"), "event_name": event.get("name"),
        "dominant_genes": ((migrate.get("mapping_table") or [{}])[0]).get("case_genes", [])[:3],
        "formula": {
            "name": "创意公式 = 在地真实性 × 人物情绪 × 视觉奇观 × 社交参与 × 时间窗口 × 城市承接力",
            "factors": scores,
            "intensity": intensity,
            "note": "六因子乘积=创意强度（%）。任一因子 <60 都会指数级拖累整体，先补短板再投放",
        },
        "concept": concept,
        "scripts": _scripts(shop_name, hook, profile),
        "matrix": _matrix(shop_name, hook),
        "offline": _offline(shop_name, hook),
        "media": _media(shop_name, event),
        "generated_by": "规则引擎（灵感熔炉模板）",
    }


SYSTEM = (
    "你是「灵感熔炉·Idea Forge」Agent。用创意公式（在地真实性×人物情绪×视觉奇观×社交参与×"
    "时间窗口×城市承接力）把资产卡、三档迁移与星火指数熔合成一份可落地的传播创意方案，"
    "含六因子评分、概念、15/30/180s脚本、传播矩阵、线下承接、媒体与负面预案。输出严格 JSON："
    '{"forge":{...}}'
)


def forge(shop_id, event_id=None, mission=None, use_llm=True,
          asset=None, migrate=None, spark_data=None):
    """熔炉：创意方案。asset/migrate/spark_data 可选，缺省时走规则路径现算。"""
    shop = data_loader.get_shop(shop_id)
    event = _find_event(event_id) if event_id else _default_event()
    if not shop:
        raise ValueError(f"未找到店铺 {shop_id}")
    if not event:
        raise ValueError("事件库为空，无法提供对标案例")
    if asset is None:
        asset, _, _ = excavator.excavator(shop_id, use_llm=False)
    if migrate is None:
        migrate, _, _ = migrator.migrator(event["id"], shop_id, use_llm=False)
    if spark_data is None:
        spark_data, _, _ = spark.spark(shop_id, use_llm=False)
    sid = f"{shop_id}__{event['id']}"
    user = json.dumps({
        "店铺": {k: v for k, v in shop.items() if not k.startswith("_")},
        "案例": event, "资产卡": asset, "三档迁移": migrate,
        "星火指数": spark_data, "任务书": mission,
    }, ensure_ascii=False)
    payload, source, model = base.agent_run(
        "forge", sid, SYSTEM, user,
        lambda: _rule_forge(shop, event, asset, migrate, spark_data, mission),
        "forge", use_llm=use_llm)
    if not isinstance(payload, dict) or "concept" not in payload or "formula" not in payload:
        print("[forge] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_forge(shop, event, asset, migrate, spark_data, mission), "rule", None
    return payload, source, model
