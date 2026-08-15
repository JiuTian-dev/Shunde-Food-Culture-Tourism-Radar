"""流量预言师 Agent：真实千问预测 + 缓存/规则引擎双兜底。"""
import json

from .. import config, data_loader, llm
from . import prompts


def forecast(shop_id: str, diagnosis: dict | None = None, use_llm: bool = True):
    """返回 (payload, source, model)。

    payload   : 预测内容 dict
    source    : "llm" | "cached" | "rule"
    """
    shop = data_loader.get_shop(shop_id)
    if not shop:
        raise ValueError(f"未找到店铺 {shop_id}")

    if use_llm and config.LLM_ENABLED:
        try:
            system = prompts.get_forecast_system()
            user = (
                "请对以下店铺做流量预测，严格按你的输出格式返回 JSON。\n\n诊断报告：\n"
                + json.dumps(diagnosis or data_loader.load_diagnosis(shop_id) or {}, ensure_ascii=False, indent=2)
                + "\n\n店铺档案：\n"
                + json.dumps(shop, ensure_ascii=False, indent=2)
            )
            data = llm.chat_json(system, user)
            payload = data.get("forecast", data)
            _patch_meta(payload, shop, diagnosis)
            return payload, "llm", config.QWEN_MODEL
        except Exception as e:
            print(f"[forecast] LLM 失败，走兜底：{e}")

    if config.ALLOW_FALLBACK:
        cached = data_loader.load_forecast(shop_id)
        if cached:
            payload = cached.get("forecast", cached)
            _patch_meta(payload, shop, diagnosis)
            return payload, "cached", None

    return _rule_forecast(shop), "rule", None


def _patch_meta(payload: dict, shop: dict, diagnosis: dict | None) -> dict:
    payload.setdefault("shop_id", shop.get("id"))
    payload.setdefault("shop_name", shop.get("name"))
    payload.setdefault("level", (diagnosis or {}).get("level", shop.get("_level")))
    payload.setdefault("category", shop.get("category", ""))
    payload.setdefault("boom_power", round(min((diagnosis or {}).get("index", shop.get("_index", 0)) / 94.1, 1.0), 2))
    return payload


def _rule_forecast(shop: dict) -> dict:
    idx = shop.get("_index", 0)
    power = round(min(idx / 94.1, 1.0), 2)
    cat_map = {"鸡煲/打边炉": 1.0, "桑拿鸡": 0.95, "烧鹅": 0.90, "粥": 0.85, "糖水": 0.85, "非遗点心": 0.85}
    cat_factor = cat_map.get(shop.get("category", ""), 0.85)
    mid_expo = round(1.5 * power * cat_factor, 2)
    return {
        "shop_id": shop.get("id"),
        "shop_name": shop.get("name"),
        "level": shop.get("_level", "B"),
        "basis": "规则引擎（基于预评分折算，非 LLM 预测）",
        "boom_power": power,
        "category": shop.get("category", ""),
        "category_factor": cat_factor,
        "volume": {
            "video_exposure": {"low": round(mid_expo * 0.7, 2), "mid": mid_expo, "high": round(mid_expo * 1.3, 2), "unit": "亿次", "note": "规则引擎估算"},
            "daily_customers_peak": {"low": None, "mid": None, "high": None, "unit": "人/日", "note": "需 LLM 结合产能评估"},
            "queue_hours": {"mid": None, "note": "需 LLM 评估"},
            "hot_cycle_months": {"mid": None, "note": "需 LLM 评估"},
        },
        "capacity_limit": "需 LLM 结合诊断的产能黄线评估",
        "confidence": "low",
        "confidence_basis": "规则引擎未充分评估，建议配置千问 API Key 后重试",
        "monetization": {"in_store_revenue": "需 LLM 评估", "livestream_gmv": "需 LLM 评估", "category_spillover": "需 LLM 评估", "support_score": "需 LLM 评估"},
        "recommendation": "规则引擎初步预测（置信度低）。详细预测请配置千问 API Key 后重试。",
    }
