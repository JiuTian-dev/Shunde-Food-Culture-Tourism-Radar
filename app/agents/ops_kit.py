"""第6步 · 作战包 Agent：把创意方案落成 10 项可执行的作战包。"""
import json

from .. import config
from . import base


def _rule_ops_kit(forge_payload, mission):
    concept = forge_payload.get("concept", {}) or {}
    media = forge_payload.get("media", {}) or {}
    shop_name = forge_payload.get("shop_name", "顺德老店")
    hook = concept.get("hook", shop_name)
    topic = concept.get("topic_name", f"#顺德{shop_name}")
    return {
        "topic": topic,
        "shop_name": shop_name,
        "calendar": {
            "第1周": [f"定稿脚本，开拍『{hook}』钩子视频", "上线话题页与挑战赛", "官方号首发 + 达人铺垫"],
            "第30天": ["数据复盘，跟进网友二创做二次话题", "线下打卡点运营", "官方媒体跟进报道"],
            "第90天": ["沉淀为城市IP资产，加入资源池", "策划第二阶段（镇街联动）", "沉淀可复用方法论"],
        },
        "account_matrix": "官方号（权威定调）× 本地达人（扩散）× 商户自号（日常素材）三账号矩阵",
        "topic_scripts": f"主话题「{topic}」+ 2 个分支话题（二创/探店）",
        "influencer_suggest": "优先本地真实探店型达人 5-10 位，配 1-2 位跨城中腰部",
        "visual_assets": ["横竖版各一套 15/30/180s", "店内店外 B-roll 30 条", "花絮与二创授权素材"],
        "merchant_training": ["统一对外口径", "拍摄配合度（后厨/出餐节奏）", "版权与肖像授权清单"],
        "capacity_plan": "按预测峰值预留产能与排队动线，设限流阈值与补货预案",
        "traffic_logistics": "明确停车/接驳/打卡动线，高峰期引导分流",
        "food_safety_checklist": ["食材溯源留证", "高峰前食安自查", "投诉响应 ≤2小时"],
        "crisis_voice": media.get("negative_prep") or ["官方口径预埋", "不追负面流量"],
        "generated_by": "规则引擎（作战包模板）",
    }


SYSTEM = ("你是「作战包」Agent。把创意方案落成 10 项可执行作战包（7/30/90天日历、账号矩阵、"
          "话题脚本、达人建议、视觉资产、商户培训、产能预案、交通动线、食安清单、危机口径）。"
          "输出严格 JSON：{\"ops_kit\":{...}}")


def ops_kit(forge_payload: dict, mission: dict | None = None, use_llm: bool = True):
    sid = f"ops-{forge_payload.get('shop_id', 'shop')}-{forge_payload.get('event_id', 'ev')}"
    user = json.dumps({"创意方案": forge_payload, "任务书": mission}, ensure_ascii=False)
    payload, source, model = base.agent_run(
        "ops_kit", sid, SYSTEM, user,
        lambda: _rule_ops_kit(forge_payload, mission), "ops_kit", use_llm=use_llm)
    # 结构校验：决策落点必须有核心字段，LLM 输出不符时回退规则，保证演示永不中断
    if not isinstance(payload, dict) or "calendar" not in payload or "account_matrix" not in payload:
        print("[ops_kit] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_ops_kit(forge_payload, mission), "rule", None
    return payload, source, model
