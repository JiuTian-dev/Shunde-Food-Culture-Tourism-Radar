"""DeepSeek LLM 封装：OpenAI 兼容接口 + JSON 输出解析。"""
import json
import re

from . import config


def _get_client():
    from openai import OpenAI

    return OpenAI(api_key=config.QWEN_API_KEY, base_url=config.QWEN_BASE_URL)


def chat_json(system: str, user: str, timeout: int | None = None) -> dict:
    """调用千问并强制解析为 JSON 对象。

    :raises RuntimeError: 网络失败 / 无 key / 输出无法解析为 JSON
    """
    if not config.LLM_ENABLED:
        raise RuntimeError("未配置 LLM API Key，无法调用真实 LLM")

    timeout = timeout or config.LLM_TIMEOUT
    client = _get_client()
    resp = client.chat.completions.create(
        model=config.QWEN_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=16384,
        timeout=timeout,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        # 思考型模型 content 常为空，答案可能在 reasoning_content 里
        text = (getattr(resp.choices[0].message, "reasoning_content", None) or "").strip()
    if not text:
        raise RuntimeError("DeepSeek 返回空内容")
    return _extract_json(text)


def _extract_json(text: str) -> dict:
    """从模型输出中稳健提取 JSON 对象（兼容代码块包裹）。"""
    # 去掉 ```json ... ``` 代码块外壳
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(f"DeepSeek 输出不含有效 JSON：{text[:200]}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"DeepSeek JSON 解析失败：{e}\n片段：{text[start:end+1][:200]}")


def chat_stream(system: str, user: str):
    """流式调用 DeepSeek，逐段 yield 文本增量（用于页面数字人打字机效果）。

    :raises RuntimeError: 网络失败 / 无 key
    """
    if not config.LLM_ENABLED:
        raise RuntimeError("未配置 LLM API Key，无法调用真实 LLM")
    client = _get_client()
    resp = client.chat.completions.create(
        model=config.QWEN_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=16384,
        stream=True,
        timeout=config.LLM_TIMEOUT,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
