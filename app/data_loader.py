"""数据加载：读取数据集 YAML 与已生成的诊断/预测结果，并提供爆款指数计算。"""
from datetime import date, datetime
from pathlib import Path
import json

import yaml


def _jsonable(v):
    """把 YAML 解析出的 date/datetime 等递归转成字符串，保证 json.dumps 安全。"""
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _jsonable(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    return v

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DIAG_DIR = ROOT / "output" / "diagnosis"
FCST_DIR = ROOT / "output" / "forecast"

INDEX_WEIGHTS = {
    "人设反差度": 0.25,
    "风味品相度": 0.25,
    "故事叙事性": 0.20,
    "情绪共鸣度": 0.20,
    "素材续航度": 0.10,
}

LEVEL_LABELS = {"A": "A类·重点孵化", "B": "B类·待观察", "C": "C类·不推荐"}


def compute_index(potentials: dict) -> float:
    """爆款指数 = 五维加权。"""
    if not potentials:
        return 0.0
    return round(sum(potentials.get(k, 0) * w for k, w in INDEX_WEIGHTS.items()), 1)


def level_of(index: float) -> str:
    if index >= 75:
        return "A"
    if index >= 60:
        return "B"
    return "C"


def load_shops(sample_type: str | None = None) -> list[dict]:
    """读取 data/*.yaml，返回店列表，附预评分指数/级别。"""
    shops: list[dict] = []
    for fname in ("positive.yaml", "negative.yaml", "candidates.yaml"):
        path = DATA_DIR / fname
        if not path.exists():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for shop in raw:
            if sample_type and shop.get("sampleType") != sample_type:
                continue
            shop = _jsonable(shop)
            pot = shop.get("potentials", {})
            idx = compute_index(pot)
            shop["_index"] = idx
            shop["_level"] = level_of(idx)
            shop["_pre"] = pot
            shops.append(shop)
    return shops


def get_shop(shop_id: str) -> dict | None:
    for s in load_shops():
        if s.get("id") == shop_id:
            return s
    return None


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_diagnosis(shop_id: str) -> dict | None:
    return load_json(DIAG_DIR / f"{shop_id}.json")


def load_forecast(shop_id: str) -> dict | None:
    return load_json(FCST_DIR / f"{shop_id}.json")


def load_all_diagnoses() -> dict[str, dict]:
    out = {}
    for p in DIAG_DIR.glob("*.json"):
        d = load_json(p)
        if d:
            out.setdefault(d.get("diagnosis", {}).get("shop_id"), d)
    return out


def load_all_forecasts() -> dict[str, dict]:
    out = {}
    for p in FCST_DIR.glob("*.json"):
        d = load_json(p)
        if d:
            out.setdefault(d.get("forecast", {}).get("shop_id"), d)
    return out


def load_events() -> list[dict]:
    """读取 data/events.yaml 事件库（近5年爆火案例），供解码/迁移/雷达使用。

    结构字段：id/name/time/duration/region/category/labels/igniteLogic/
    factorType/peakMetrics/timeline/evidence。
    """
    path = DATA_DIR / "events.yaml"
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [_jsonable(e) for e in raw if isinstance(e, dict)]
