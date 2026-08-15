"""第0步 · 城市传播任务书 Agent。

把政府用户的『目标类型 + 城市 + 预算 + 时间窗口 + 目标人群 + 资源范围』
规范化为结构化的《城市传播任务书》，作为全流水线的输入。
"""
import json
from datetime import date

from . import base

TASK_TYPE_DEFS = {
    "推广老店": {
        "goal": "把老店故事与招牌产品做成全网话题，带动到店客流",
        "kpi": {"话题曝光": "≥5000万次", "到店客流": "较基线 +200%", "主话题": "1个"},
        "constraints": ["不消费老店信任资本", "不编造传承故事"],
    },
    "打造草根人物IP": {
        "goal": "孵化一位有绝活的草根人物，让『人』成为城市名片",
        "kpi": {"账号涨粉": "≥50万", "单条爆款": "≥1条/月", "跨城报道": "≥3家媒体"},
        "constraints": ["需人物本人书面授权", "保护隐私与肖像权"],
    },
    "激活老街商圈": {
        "goal": "把一条老街/商圈做成可打卡的城市叙事动线",
        "kpi": {"街区客流": "较基线 +150%", "商户参与": "≥60%", "打卡点": "≥8个"},
        "constraints": ["不搞拆迁式改造", "夜间经济需配套管理"],
    },
    "策划城市活动": {
        "goal": "策划一场可参与、可传播、可复购的城市活动",
        "kpi": {"现场参与": "≥3万人次", "话题播放": "≥10亿次", "消费转化": "文旅消费 +15%"},
        "constraints": ["预算内", "承载量封顶管理"],
    },
    "承接网络热点": {
        "goal": "72小时内接住正在发生的热点，转化为城市留量",
        "kpi": {"响应时效": "≤72小时", "官方口径": "1套", "承接动作": "≥3个"},
        "constraints": ["先核事实再发声", "不追负面流量"],
    },
    "节假日储备选题": {
        "goal": "为节假日提前储备选题弹药，届时一键释放",
        "kpi": {"储备选题": "≥20个", "预热时长": "节前30天", "节奏": "7/30/90天日历"},
        "constraints": ["与节令强相关", "留足拍摄周期"],
    },
    "改善负面标签": {
        "goal": "以真实故事对冲『美食荒漠/没夜生活』等负面标签",
        "kpi": {"负面声量占比": "下降至 <15%", "正面话题": "≥3个", "KOL背书": "≥5位"},
        "constraints": ["只讲真实，不搞形象工程"],
    },
}

DEFAULT_AUDIENCE = "18-35岁年轻游客 + 本地年轻市民"
DEFAULT_WINDOW = "未来30天"
DEFAULT_BUDGET = "300万以内"
DEFAULT_RESOURCES = ["顺德美食店铺三件套", "非遗/老字号", "镇街活动日历", "飞书推送通道"]


def _slug(task_type):
    idx = list(TASK_TYPE_DEFS.keys()).index(task_type) + 1 if task_type in TASK_TYPE_DEFS else 0
    return f"task{idx:02d}"


def build_mission(task_type="承接网络热点", city="顺德", budget=None,
                  window=None, audience=None, resources=None, **extra) -> dict:
    """规则兜底：按任务类型规范化输出《城市传播任务书》。"""
    task_type = task_type if task_type in TASK_TYPE_DEFS else "承接网络热点"
    d = TASK_TYPE_DEFS[task_type]
    return {
        "task_type": task_type,
        "city": city or "顺德",
        "audience": audience or DEFAULT_AUDIENCE,
        "budget": budget or DEFAULT_BUDGET,
        "window": window or DEFAULT_WINDOW,
        "resources": resources or DEFAULT_RESOURCES,
        "goal": d["goal"],
        "kpi": d["kpi"],
        "constraints": d["constraints"],
        "extra": extra,
        "generated_by": "规则引擎（配置 LLM 后可增强）",
    }


SYSTEM = (
    "你是「城市传播任务书」Agent。把政府用户的目标、城市、预算、时间窗口、目标人群、"
    "资源范围，规范化为结构化的《城市传播任务书》，含 goal/kpi/constraints。输出严格 JSON："
    '{"mission":{...}}'
)


def mission(task_type="承接网络热点", city="顺德", budget=None, window=None,
            audience=None, resources=None, use_llm=True, **extra):
    """生成《城市传播任务书》。返回 (payload, source, model)。"""
    task_type = task_type if task_type in TASK_TYPE_DEFS else "承接网络热点"
    sid = f"M-{date.today():%Y%m%d}-{_slug(task_type)}"
    user = json.dumps({
        "task_type": task_type, "city": city, "budget": budget, "window": window,
        "audience": audience, "resources": resources,
        "available_task_types": list(TASK_TYPE_DEFS.keys()), "extra": extra,
    }, ensure_ascii=False)
    payload, source, model = base.agent_run(
        "mission", sid, SYSTEM, user,
        lambda: build_mission(task_type, city, budget, window, audience, resources, **extra),
        "mission", use_llm=use_llm)
    payload["mission_id"] = sid
    return payload, source, model
