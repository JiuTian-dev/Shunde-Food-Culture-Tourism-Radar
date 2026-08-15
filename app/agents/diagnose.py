"""诊断医师 Agent：真实千问诊断 + 缓存/规则引擎双兜底。"""
import json

from .. import config, data_loader, llm
from . import prompts


def _clean_shop(shop: dict) -> dict:
    """去掉内部字段（_ 前缀），保留纯档案供 LLM 参考。"""
    return {k: v for k, v in shop.items() if not k.startswith("_")}


def diagnose(shop_id: str, use_llm: bool = True):
    """返回 (payload, source, model)。

    payload   : 诊断内容 dict（含 scores/index/level/risks/...）
    source    : "llm" | "cached" | "rule"
    model     : 千问模型名 / None
    """
    shop = data_loader.get_shop(shop_id)
    if not shop:
        raise ValueError(f"未找到店铺 {shop_id}")

    if use_llm and config.LLM_ENABLED:
        try:
            system = prompts.get_diagnose_system()
            user = (
                "请对以下顺德美食店进行爆款诊断，严格按你的输出格式返回 JSON。\n\n店铺档案：\n"
                + json.dumps(_clean_shop(shop), ensure_ascii=False, indent=2)
            )
            data = llm.chat_json(system, user)
            payload = data.get("diagnosis", data)
            _patch_meta(payload, shop)
            return payload, "llm", config.QWEN_MODEL
        except Exception as e:
            print(f"[diagnose] LLM 失败，走兜底：{e}")

    # 兜底 1：已生成的诊断结果（output/diagnosis/*.json）
    if config.ALLOW_FALLBACK:
        cached = data_loader.load_diagnosis(shop_id)
        if cached:
            payload = cached.get("diagnosis", cached)
            _patch_meta(payload, shop)
            return payload, "cached", None

    # 兜底 2：规则引擎（基于预评分加权）
    return _rule_diagnosis(shop), "rule", None


def _patch_meta(payload: dict, shop: dict) -> dict:
    """补齐前端需要的 index/level/name 等字段。"""
    payload.setdefault("shop_id", shop.get("id"))
    payload.setdefault("shop_name", shop.get("name"))
    scores = payload.get("scores") or shop.get("_pre", {})
    if "index" not in payload or not payload.get("index"):
        payload["index"] = data_loader.compute_index(scores)
    if "level" not in payload or not payload.get("level"):
        payload["level"] = data_loader.level_of(payload.get("index", 0))
    payload["shop_name"] = payload.get("shop_name") or shop.get("name")
    return payload


def _rule_diagnosis(shop: dict) -> dict:
    """规则引擎兜底：预评分 + 模板化理由。"""
    pre = shop.get("_pre", {})
    idx = shop.get("_index", 0)
    level = shop.get("_level", "B")
    risks = shop.get("risks", [])

    def brief(dim):
        return f"基于内置预评分 {pre.get(dim, 0)} 分（规则引擎，非 LLM 独立判断）"

    return {
        "shop_id": shop.get("id"),
        "shop_name": shop.get("name"),
        "verified": True,
        "field_gaps": [],
        "scores": pre,
        "score_reasons": {d: brief(d) for d in data_loader.INDEX_WEIGHTS},
        "index": idx,
        "level": level,
        "risks": {"red": [], "yellow": risks, "notice": []},
        "stress_test": {
            "will_boom": shop.get("craft", {}).get("visualImpact", ""),
            "will_break": "规则引擎未评估，建议接入 LLM 深度诊断",
            "needs_before": "规则引擎未评估，建议接入 LLM 深度诊断",
        },
        "recommendation": f"规则引擎初步结论：{level}类。详细评估请配置千问 API Key 后重试。",
    }
