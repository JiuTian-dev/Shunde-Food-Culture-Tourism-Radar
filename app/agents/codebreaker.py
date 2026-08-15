"""第3步 · 爆点解码器 Agent：把全网爆火案例拆解成 8 种爆款基因。"""
import json

from .. import config, data_loader
from . import base

GENES = [
    ("人物", ["人", "老板娘", "老板", "师傅", "店主", "老头", "少年", "00后", "草根", "大叔"], "有被记住的主角"),
    ("反差", ["反差", "劝退", "拒绝", "反套路", "错位", "大隐", "破店", "变脸", "巷子", "犄角"], "反套路/错位感"),
    ("视觉", ["锅气", "爆", "拉丝", "现宰", "冒烟", "造型", "画面", "浮夸", "满到", "堆成山", "创新"], "一眼记住的画面"),
    ("情绪", ["情绪", "共鸣", "情怀", "乡愁", "治愈", "感动", "骄傲", "执着", "坚持", "热爱"], "戳中集体情绪"),
    ("地域", ["顺德", "佛山", "地域", "地方", "古镇", "非遗", "老字号", "地名"], "在地味/地名梗"),
    ("参与", ["玩梗", "挑战", "比赛", "接龙", "二创", "投票", "打卡", "互动", "全民"], "可参与可二创"),
    ("事件", ["事件", "抢", "排队", "空降", "爆火", "翻红", "争议", "反转", "热搜"], "有事件性"),
    ("承接", ["承接", "接住", "出圈", "city", "文旅", "政府", "城市", "明星"], "城市接得住"),
]


def _hits(text, kws):
    return [k for k in kws if k in text]


def _rule_decode(event):
    text = "".join(event.get("labels", [])) + (event.get("igniteLogic") or "") + (event.get("factorType") or "")
    genes = []
    for gname, kws, desc in GENES:
        hit = _hits(text, kws)
        present = len(hit) > 0
        genes.append({
            "gene": gname, "desc": desc, "present": present,
            "evidence": f"命中：{'/'.join(hit)}" if hit else f"「{event.get('name')}」未显式体现该基因",
            "transferability": 5 if present else 2,
            "shunde_note": "顺德可直接迁移" if present else "顺德需另行点亮该基因",
        })
    return {
        "event_id": event.get("id"), "event_name": event.get("name"),
        "dominant_genes": [g["gene"] for g in genes if g["present"]][:3],
        "ignite_logic": event.get("igniteLogic"), "factor_type": event.get("factorType"),
        "peak_metrics": event.get("peakMetrics"), "timeline": event.get("timeline"),
        "genes": genes, "generated_by": "规则引擎（关键词命中→8基因）",
    }


def _find_event(event_id):
    for e in data_loader.load_events():
        if e.get("id") == event_id:
            return e
    return None


SYSTEM = ("你是「爆点解码器」Agent。把一个爆火案例拆解成 8 种爆款基因（人物/反差/视觉/情绪/"
          "地域/参与/事件/承接），给每个基因判存在、给证据、给顺德可迁移度。输出严格 JSON："
          '{"decode":{...}}')


def codebreaker(event_id: str, use_llm: bool = True):
    event = _find_event(event_id)
    if not event:
        raise ValueError(f"未找到事件 {event_id}")
    user = json.dumps({"案例": event}, ensure_ascii=False)
    payload, source, model = base.agent_run("decode", event_id, SYSTEM, user,
                                            lambda: _rule_decode(event), "decode", use_llm=use_llm)
    if not isinstance(payload, dict) or "genes" not in payload:
        print("[codebreaker] LLM 输出结构不符，回退规则")
        payload, source, model = _rule_decode(event), "rule", None
    return payload, source, model
