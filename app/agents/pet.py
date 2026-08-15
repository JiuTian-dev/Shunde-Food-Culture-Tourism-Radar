"""小顺 —— 页面数字人：人设 + 与客户实时对话（接入 DeepSeek）。

区别于 diagnose/forecast 的 JSON 工作流，小顺是闲聊/答疑向，
用 llm.chat_stream 流式出文本，前端打字机渲染。
"""
import json

from .. import config, llm

SYSTEM = """你是「小顺」，顺德美食流量孵化引擎的页面数字人、顺德美食宣传大使。
性格：热情、俏皮、接地气，像个懂吃又懂营销的顺德邻家朋友。
你会和来参观的客户/评委聊天：介绍顺德美食、讲讲「流量孵化」这套帮美食店变爆款的玩法、
用拟人化的比喻解释 人设反差 / 风味品相 / 情绪共鸣 这些概念。
说话简短有烟火气，多用地道口头禅（"饮啖茶""掂过碌蔗""食过返寻味"）。
默认回答控制在 60 字以内；客户问得很具体时再展开。始终用简体中文。"""

# LLM 失败 / 未配 Key 时的兜底回复（与项目「演示永不中断」哲学一致）
FALLBACK = "唔……小顺的脑瓜还没接上网线（DeepSeek 暂时不可用），先给你逛逛看板，等下再聊～"


def reply(message: str) -> str:
    """单条流式回复，yield 文本增量。LLM 不可用时给兜底话术。"""
    if not config.LLM_ENABLED:
        yield FALLBACK
        return
    try:
        for delta in llm.chat_stream(SYSTEM, message):
            yield delta
    except Exception:
        yield FALLBACK


def sse_gen(message: str):
    """把 reply 包成 SSE 事件流（data: JSON\\n\\n），供 /api/chat 使用。"""
    for delta in reply(message):
        yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
