"""流水线 Agent 共享基座：LLM → 规则兜底 → 持久化 三层模式。

所有流水线 Agent 通过 agent_run() 收敛样板代码，与 diagnose/forecast 的
「演示永不中断」哲学一致：LLM 可用走真实模型，否则落规则引擎并落盘。
"""
import json

from .. import config, data_loader, llm

OUTPUT_DIR = data_loader.ROOT / "output"


def _persist(save_dir: str, sid: str, payload: dict, source: str) -> None:
    try:
        d = OUTPUT_DIR / save_dir
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{sid}.json").write_text(
            json.dumps({"payload": payload, "source": source}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[{save_dir}] 持久化失败：{e}")


def agent_run(name, sid, system, user, rule_fn, save_dir, use_llm=True):
    """执行一个流水线 Agent。

    :param name:     Agent 名（也作 LLM 输出 JSON 的顶层键）
    :param sid:      业务主键（店铺 id / 事件 id / 任务 id 等）
    :param system:   LLM system prompt
    :param user:     LLM user prompt
    :param rule_fn:  () -> dict，规则引擎兜底
    :param save_dir: output/ 下的落盘子目录
    :return: (payload, source, model)；source ∈ {"llm","rule"}
    """
    if use_llm and config.LLM_ENABLED:
        try:
            data = llm.chat_json(system, user)
            payload = data.get(name, data)
            if not isinstance(payload, dict):
                raise RuntimeError(f"{name} 输出不是对象")
            _persist(save_dir, sid, payload, "llm")
            return payload, "llm", config.QWEN_MODEL
        except Exception as e:
            print(f"[{name}] LLM 失败，走规则兜底：{e}")
    payload = rule_fn()
    _persist(save_dir, sid, payload, "rule")
    return payload, "rule", None
