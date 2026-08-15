"""第2步 · 烟火考古局 Agent：城市IP寻宝 → 生成《城市IP资产卡》。"""
import json

from .. import config, data_loader
from . import base

_PARTICIPATE_KW = ("现做", "现切", "现宰", "挑战", "比赛", "互动", "试吃", "DIY")
_REVERSE_WORDS = ("佛系", "反套路", "耿直", "别来", "劝退", "拒绝", "不按常理")


def _rule_asset_card(shop):
    owner = shop.get("owner", {}) or {}
    craft = shop.get("craft", {}) or {}
    pricing = shop.get("pricingCapacity", {}) or {}
    risks = shop.get("risks", []) or []
    sig = owner.get("signatureLines") or []
    kw = "".join(craft.get("keywords", []))
    hits = []
    if sig:
        hits.append({"type": "有绝活的人", "evidence": f"口头禅 {len(sig)} 句，首句：{sig[0][:22]}"})
    if craft.get("heritage"):
        hits.append({"type": "有记忆的店", "evidence": craft["heritage"]})
    if craft.get("visualImpact"):
        hits.append({"type": "有画面的食物", "evidence": str(craft["visualImpact"])[:22]})
    if any(x in kw for x in _PARTICIPATE_KW):
        hits.append({"type": "有参与感的动作", "evidence": "制作过程可围观/可参与"})
    if any(w in (owner.get("personality") or "") for w in _REVERSE_WORDS):
        hits.append({"type": "有冲突的标签", "evidence": owner.get("personality")})
    return {
        "shop_id": shop.get("id"), "shop_name": shop.get("name"),
        "district": shop.get("district"), "category": shop.get("category"),
        "five_category_hits": hits,
        "profile": {
            "person": owner.get("name"), "personality": owner.get("personality"),
            "background": owner.get("background"), "signature_lines": sig,
            "signature_skill": "、".join(craft.get("keywords", []) or []),
            "visual_hook": craft.get("visualImpact"), "heritage": craft.get("heritage"),
            "story": owner.get("story"),
        },
        "capacity": {
            "price_band": pricing.get("priceBand"), "capacity": pricing.get("capacity"),
            "limit": pricing.get("limit"), "operating": shop.get("operating"),
        },
        "risks": risks,
        "lifecycle_estimate": "建议以 2-3 个月为一个观察周期（素材续航决定长红）",
        "generated_by": "规则引擎（烟火考古档案）",
    }


SYSTEM = ("你是「烟火考古局」Agent。基于店铺档案生成《城市IP资产卡》，含五类候选命中、"
          "人物/技艺/视觉/情绪资产、承接能力与风险。输出严格 JSON：{\"asset_card\":{...}}")


def excavator(shop_id: str, use_llm: bool = True):
    shop = data_loader.get_shop(shop_id)
    if not shop:
        raise ValueError(f"未找到店铺 {shop_id}")
    clean = {k: v for k, v in shop.items() if not k.startswith("_")}
    user = json.dumps({"店铺档案": clean}, ensure_ascii=False)
    payload, source, model = base.agent_run("asset_card", shop_id, SYSTEM, user,
                                            lambda: _rule_asset_card(shop), "asset_card", use_llm=use_llm)
    if not isinstance(payload, dict) or "profile" not in payload:
        print("[excavator] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_asset_card(shop), "rule", None
    return payload, source, model
