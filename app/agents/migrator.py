"""第4步 · 城市灵感迁移器 Agent：跨城映射 → 稳健/突破/现象级 三档方案。"""
import json

from .. import config, data_loader
from . import base


def _rule_migrate(event, shop):
    owner = shop.get("owner", {}) or {}
    craft = shop.get("craft", {}) or {}
    sig = owner.get("signatureLines") or []
    kw = craft.get("keywords") or []
    shop_name = shop.get("name", "")
    hook = sig[0] if sig else shop_name
    resource = "、".join(kw[:4]) if kw else shop_name
    mapping = {
        "case": event.get("name"), "case_time": event.get("time"),
        "case_genes": event.get("labels", [])[:4],
        "shunde_resource": resource,
        "shunde_action": f"把「{event.get('name')}」的爆点逻辑迁移到 {shop_name}，以『{hook}』为钩子",
    }
    plans = {
        "稳健档": {
            "name": f"{shop_name}招牌内容化", "effort": "低", "risk": "低",
            "key_actions": [
                f"拍摄 3 条人物故事向短视频（以『{hook}』为钩子）",
                f"发起一次「{hook}」相关的话题挑战",
                "商户自运营 + 本地达人 5-10 位分发",
            ],
            "expected_impact": "本地圈层小爆，承接稳妥，7 天可见数据",
        },
        "突破档": {
            "name": f"{shop_name} × {event.get('name')} 城市迁移", "effort": "中", "risk": "中",
            "key_actions": [
                f"复刻「{event.get('name')}」的事件节奏（预热-爆发-沉淀）",
                "设置线下快闪/打卡点，提供可拍摄画面",
                "官方号 + 中腰部达人矩阵集中投放 7 天",
            ],
            "expected_impact": "单平台大爆，跨城媒体跟进，周期约 30 天",
        },
        "现象级档": {
            "name": f"以 {shop_name} 为锚点的城市叙事", "effort": "高", "risk": "高",
            "key_actions": [
                "联动顺德十镇街资源，设计城市级话题",
                "政府背书 + 全媒体投放 + 线下节事承接",
                "沉淀为可复用的城市IP资产，滚动策源",
            ],
            "expected_impact": "对标现象级案例，带来城市留量与长期资产",
        },
    }
    return {
        "case_event": event.get("name"), "target_shop": shop_name,
        "mapping_table": [mapping], "plans": plans,
        "generated_by": "规则引擎（三档迁移模板）",
    }


def _find_event(event_id):
    for e in data_loader.load_events():
        if e.get("id") == event_id:
            return e
    return None


SYSTEM = ("你是「城市灵感迁移器」Agent。把外部爆火案例映射到顺德本地资源，给出稳健/突破/"
          "现象级 三档迁移方案。输出严格 JSON：{\"migrate\":{...}}")


def migrator(event_id: str, shop_id: str, use_llm: bool = True):
    event = _find_event(event_id)
    shop = data_loader.get_shop(shop_id)
    if not event or not shop:
        raise ValueError("事件或店铺不存在")
    sid = f"{event_id}__{shop_id}"
    user = json.dumps({"案例": event, "目标店铺": {k: v for k, v in shop.items() if not k.startswith("_")}}, ensure_ascii=False)
    payload, source, model = base.agent_run("migrate", sid, SYSTEM, user,
                                            lambda: _rule_migrate(event, shop), "migrate", use_llm=use_llm)
    if not isinstance(payload, dict) or "plans" not in payload:
        print("[migrator] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_migrate(event, shop), "rule", None
    return payload, source, model
