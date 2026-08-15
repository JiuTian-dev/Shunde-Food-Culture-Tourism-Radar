"""顺德美食流量孵化引擎 —— Web 看板后端（FastAPI）。

运行：uvicorn app.main:app --reload
访问：http://127.0.0.1:8000
"""
import json
from pathlib import Path

import yaml

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, data_loader
from .agents import diagnose, forecast, pet
from .agents import mission, radar, excavator, codebreaker, migrator, forge, spark, workflow

app = FastAPI(title="顺德美食流量孵化引擎", version="0.1.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class DiagnoseRequest(BaseModel):
    shop_id: str
    use_llm: bool = Field(default=True)


class ForecastRequest(BaseModel):
    shop_id: str
    use_llm: bool = Field(default=True)


@app.get("/", include_in_schema=False)
def index():
    f = STATIC_DIR / "index.html"
    if f.exists():
        return FileResponse(str(f))
    return JSONResponse({"msg": "前端未构建，请先创建 app/static/index.html"}, status_code=404)


@app.get("/api/status")
def status():
    return {
        "llm_enabled": config.LLM_ENABLED,
        "model": config.QWEN_MODEL,
        "base_url": config.QWEN_BASE_URL,
        "allow_fallback": config.ALLOW_FALLBACK,
        "mode": "LLM Agent 在线" if config.LLM_ENABLED else "内置报告回放（未配置 API Key）",
        "shop_count": len(data_loader.load_shops()),
    }


@app.get("/api/shops")
def shops():
    rows = []
    for s in data_loader.load_shops():
        rows.append(
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "category": s.get("category", ""),
                "district": s.get("district", ""),
                "pre": s.get("_pre", {}),
                "index": s.get("_index", 0),
                "level": s.get("_level", "B"),
                "is_candidate": s.get("_is_candidate", False),
            }
        )
    rows.sort(key=lambda r: (-r["index"]))
    return {"items": rows, "total": len(rows)}


@app.get("/api/locations")
def locations():
    """地图坐标：读 data/location.yaml，合并店铺名/指数/级别，供前端地图标记。"""
    path = data_loader.DATA_DIR / "location.yaml"
    if not path.exists():
        return {"items": [], "total": 0}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    shop_map = {s.get("id"): s for s in data_loader.load_shops()}
    items = []
    for i, loc in enumerate(raw, 1):
        sid = loc.get("id")
        s = shop_map.get(sid) or {}
        items.append(
            {
                "id": sid,
                "name": s.get("name") or loc.get("name"),
                "area": loc.get("area", ""),
                "x": loc.get("x"),
                "y": loc.get("y"),
                "index": s.get("_index"),
                "level": s.get("_level", "B"),
                "n": i,
            }
        )
    return {"items": items, "total": len(items)}


@app.get("/api/leaderboard")
def leaderboard():
    """潜力榜：A 类置顶，其余按指数降序。"""
    items = []
    for s in data_loader.load_shops():
        diag = data_loader.load_diagnosis(s.get("id")) or {}
        fcst = data_loader.load_forecast(s.get("id")) or {}
        items.append(
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "category": s.get("category", ""),
                "district": s.get("district", ""),
                "index": s.get("_index", 0),
                "level": s.get("_level", "B"),
                "has_diagnosis": bool(diag),
                "has_forecast": bool(fcst),
                "diagnosis_level": (diag.get("diagnosis") or {}).get("level"),
            }
        )
    items.sort(key=lambda r: (-(r["level"] == "A"), -r["index"]))
    return {"items": items, "total": len(items)}


@app.get("/api/shops/{shop_id}")
def shop_detail(shop_id: str):
    s = data_loader.get_shop(shop_id)
    if not s:
        raise HTTPException(404, f"未找到店铺 {shop_id}")
    diag = data_loader.load_diagnosis(shop_id)
    fcst = data_loader.load_forecast(shop_id)
    return {
        "shop": s,
        "diagnosis": (diag or {}).get("diagnosis"),
        "forecast": (fcst or {}).get("forecast"),
        "source_hint": "回放已固化报告（配置千问 Key 后可现场重跑）",
    }


@app.post("/api/diagnose")
def run_diagnose(req: DiagnoseRequest):
    try:
        payload, source, model = diagnose.diagnose(req.shop_id, use_llm=req.use_llm)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model, "llm_enabled": config.LLM_ENABLED}


class ChatRequest(BaseModel):
    message: str = Field(max_length=500)


@app.post("/api/chat")
def chat(req: ChatRequest):
    """小顺页面数字人：流式对话（SSE）。"""
    return StreamingResponse(
        pet.sse_gen(req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/forecast")
def run_forecast(req: ForecastRequest):
    try:
        shop = data_loader.get_shop(req.shop_id)
        if not shop:
            raise HTTPException(404, f"未找到店铺 {req.shop_id}")
        payload, source, model = forecast.forecast(req.shop_id, use_llm=req.use_llm)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model, "llm_enabled": config.LLM_ENABLED}


# ── 城市烟火 IP 智能策源与增长引擎 · 流水线 API（纯增量，不动既有端点）──────────────

class MissionRequest(BaseModel):
    task_type: str = "承接网络热点"
    city: str = "顺德"
    budget: str | None = None
    window: str | None = None
    audience: str | None = None
    resources: list[str] | None = None
    use_llm: bool = True


class ForgeRequest(BaseModel):
    shop_id: str
    event_id: str | None = None
    use_llm: bool = True


class WorkflowRunRequest(BaseModel):
    task_type: str = "承接网络热点"
    city: str = "顺德"
    budget: str | None = None
    window: str | None = None
    audience: str | None = None
    resources: list[str] | None = None
    focus_shop_id: str | None = None
    focus_event_id: str | None = None
    approve: bool = True
    use_llm: bool = True


@app.get("/api/events")
def events():
    """事件库：全网爆火案例，供前端选择对标。"""
    items = data_loader.load_events()
    return {"items": items, "total": len(items)}


@app.post("/api/mission")
def run_mission(req: MissionRequest):
    try:
        payload, source, model = mission.mission(
            req.task_type, req.city, req.budget, req.window, req.audience, req.resources,
            use_llm=req.use_llm)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model, "llm_enabled": config.LLM_ENABLED}


@app.get("/api/radar")
def run_radar():
    # 只读查询走规则路径（瞬时返回）；需要 LLM 增强时用 POST /api/workflow/run 或显式重跑
    payload, source, model = radar.radar(use_llm=False)
    return {"data": payload, "source": source, "model": model}


@app.get("/api/asset-card/{shop_id}")
def run_asset_card(shop_id: str):
    try:
        payload, source, model = excavator.excavator(shop_id, use_llm=False)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model}


@app.get("/api/spark/{shop_id}")
def run_spark(shop_id: str):
    try:
        payload, source, model = spark.spark(shop_id, use_llm=False)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model}


@app.get("/api/decode/{event_id}")
def run_decode(event_id: str):
    try:
        payload, source, model = codebreaker.codebreaker(event_id, use_llm=False)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model}


@app.get("/api/migrate")
def run_migrate(event_id: str, shop_id: str):
    try:
        payload, source, model = migrator.migrator(event_id, shop_id, use_llm=False)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model}


@app.post("/api/forge")
def run_forge(req: ForgeRequest):
    try:
        payload, source, model = forge.forge(req.shop_id, req.event_id, use_llm=req.use_llm)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"data": payload, "source": source, "model": model}


@app.post("/api/workflow/run")
def run_workflow(req: WorkflowRunRequest):
    """端到端跑一轮策源流水线 → 返回含全部环节的《最终方案》。"""
    try:
        record = workflow.run(
            req.task_type, req.city, req.budget, req.window, req.audience, req.resources,
            req.focus_shop_id, req.focus_event_id, approve=req.approve, use_llm=req.use_llm)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"run": record}


@app.post("/api/workflow/{run_id}/approve")
def approve_workflow(run_id: str):
    """政府人工闸门：审批后进入作战包与战情室。"""
    rec = workflow.get(run_id)
    if not rec:
        raise HTTPException(404, f"未找到运行 {run_id}")
    rec = workflow.approve_run(rec)
    return {"run": rec}


@app.get("/api/workflow")
def list_workflow():
    return {"runs": workflow.list_runs()}


@app.get("/api/workflow/{run_id}")
def get_workflow(run_id: str):
    rec = workflow.get(run_id)
    if not rec:
        raise HTTPException(404, f"未找到运行 {run_id}")
    return {"run": rec}
