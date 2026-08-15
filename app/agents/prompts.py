"""加载 Prompt 模板（优先读 docs/ 已固化的模板，文件缺失时用内嵌精简版）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOCS = ROOT / "docs"

DIAG_PROMPT_PATH = DOCS / "诊断Agent-Prompt模板.md"
FCST_PROMPT_PATH = DOCS / "预言师Agent-Prompt模板.md"

# 内嵌精简版（docs 模板缺失时的兜底）
DIAG_SYSTEM_FALLBACK = (
    "你是「诊断医师」，顺德美食流量孵化引擎的核心决策 Agent。"
    "对给定店铺做爆款诊断：五维打分（人设反差度/风味品相度/故事叙事性/情绪共鸣度/素材续航度，各0-100），"
    "按公式 爆款指数=0.25×人设+0.25×风味+0.20×故事+0.20×情绪+0.10×续航 计算。"
    "风险是门槛：红线（卫生/安全/违规）一票不推荐，黄线（产能不足/主理人抗拒/健康）降级。"
    "每个分数必须引用档案证据。输出严格 JSON："
    '{"diagnosis":{"shop_id","shop_name","verified","field_gaps","scores","score_reasons","index","level","risks","stress_test","recommendation"}}'
)

FCST_SYSTEM_FALLBACK = (
    "你是「流量预言师」，顺德美食流量孵化引擎的量化决策 Agent。"
    "基于诊断报告与店铺档案预测：量级（曝光/客流/排队/周期）+置信度+变现回报。"
    "锚点：莫氏鸡煲=爆款指数94.1为1.0、曝光1.5亿、客流3000人/日、直播750万/30天、周期约3个月。"
    "公式：曝光=1.5亿×引爆力×品类系数；引爆力=min(指数/94.1,1)；客流=3000×引爆力×品类系数（受产能封顶）；周期=2+素材续航/100。"
    "永远给 low/mid/high 区间。输出严格 JSON："
    '{"forecast":{"shop_id","shop_name","level","basis","boom_power","category","category_factor","volume","capacity_limit","confidence","confidence_basis","monetization","recommendation"}}'
)


def _read(path: Path, fallback: str) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return fallback


def get_diagnose_system() -> str:
    return _read(DIAG_PROMPT_PATH, DIAG_SYSTEM_FALLBACK)


def get_forecast_system() -> str:
    return _read(FCST_PROMPT_PATH, FCST_SYSTEM_FALLBACK)
