"""构建 Cloudflare Pages 部署包。

把前端静态资源 + 预生成数据打包成 `deploy/` 目录，并用 Pages Functions 模拟
FastAPI 的 /api/* 接口（回放模式），无需修改前端代码即可在 Cloudflare Pages 上运行。

运行：python scripts/build_pages.py
产物：deploy/  （可直接 wrangler pages deploy deploy）
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from app import data_loader  # noqa: E402

DEPLOY = ROOT / "deploy"
SRC = ROOT / "app" / "static"
WF_DIR = ROOT / "output" / "workflow"
FUNCTIONS = DEPLOY / "functions" / "api"


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_static():
    """拷贝静态资源：index.html 在根，其余资源放 static/ 前缀下。"""
    (DEPLOY / "static").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "index.html", DEPLOY / "index.html")
    for name in ["logo-icon.png", "map.png", "shunde-map.png", "xiaoshun.jpg"]:
        src = SRC / name
        if src.exists():
            shutil.copy2(src, DEPLOY / "static" / name)
    shop_images = SRC / "shop-images"
    if shop_images.exists():
        shutil.copytree(shop_images, DEPLOY / "static" / "shop-images", dirs_exist_ok=True)


def build_data() -> dict:
    """复刻 app/main.py 中 /api/leaderboard、/api/locations、/api/shops/{id}、workflow 回放逻辑。"""
    shops = data_loader.load_shops()

    # /api/leaderboard
    leaderboard = []
    for s in shops:
        diag = data_loader.load_diagnosis(s.get("id")) or {}
        fcst = data_loader.load_forecast(s.get("id")) or {}
        leaderboard.append(
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
    leaderboard.sort(key=lambda r: (-(r["level"] == "A"), -r["index"]))

    # /api/locations
    loc_path = data_loader.DATA_DIR / "location.yaml"
    raw = yaml.safe_load(loc_path.read_text(encoding="utf-8")) or []
    shop_map = {s.get("id"): s for s in shops}
    locations = []
    for i, loc in enumerate(raw, 1):
        sid = loc.get("id")
        s = shop_map.get(sid) or {}
        locations.append(
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

    # /api/shops/{id}
    shops_detail = {}
    for s in shops:
        sid = s.get("id")
        diag = data_loader.load_diagnosis(sid)
        fcst = data_loader.load_forecast(sid)
        shops_detail[sid] = {
            "shop": s,
            "diagnosis": (diag or {}).get("diagnosis"),
            "forecast": (fcst or {}).get("forecast"),
            "source_hint": "回放已固化报告（配置 DeepSeek Key 后可现场重跑）",
        }

    # /api/workflow/run 回放：每个店铺选最新一条已生成的 WF 记录
    records = []
    for p in WF_DIR.glob("WF-*.json"):
        try:
            records.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    records.sort(key=lambda r: r.get("created", ""), reverse=True)
    plans = {}
    for rec in records:
        sid = rec.get("shop_id")
        if sid and sid not in plans:
            plans[sid] = rec
    fallback = records[0] if records else {}

    return {"leaderboard": leaderboard, "locations": locations, "shops": shops_detail, "plans": plans, "fallback": fallback}


def build_functions(data: dict):
    js_data = "export const DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    write(FUNCTIONS / "_data.js", js_data)

    write(
        FUNCTIONS / "leaderboard.js",
        """import { DATA } from "./_data.js";
export async function onRequestGet() {
  return Response.json({ items: DATA.leaderboard, total: DATA.leaderboard.length });
}
""",
    )
    write(
        FUNCTIONS / "locations.js",
        """import { DATA } from "./_data.js";
export async function onRequestGet() {
  return Response.json({ items: DATA.locations, total: DATA.locations.length });
}
""",
    )
    write(
        FUNCTIONS / "status.js",
        """export async function onRequestGet(ctx) {
  const enabled = !!(ctx.env && ctx.env.DEEPSEEK_API_KEY);
  return Response.json({
    llm_enabled: enabled,
    model: (ctx.env && ctx.env.DEEPSEEK_MODEL) || "deepseek-chat",
    mode: enabled ? "LLM Agent 在线" : "内置报告回放",
    shop_count: 36,
  });
}
""",
    )
    write(
        FUNCTIONS / "shops" / "[id].js",
        """import { DATA } from "../_data.js";
export async function onRequestGet(ctx) {
  const d = DATA.shops[ctx.params.id];
  if (!d) return Response.json({ detail: `未找到店铺 ${ctx.params.id}` }, { status: 404 });
  return Response.json(d);
}
""",
    )
    write(
        FUNCTIONS / "workflow" / "run.js",
        """import { DATA } from "../_data.js";
export async function onRequestPost(ctx) {
  let focus = "SD-C15";
  try {
    const body = await ctx.request.json();
    if (body && body.focus_shop_id) focus = body.focus_shop_id;
  } catch {}
  const plan = DATA.plans[focus] || DATA.fallback;
  if (!plan) return Response.json({ detail: "暂无可用方案" }, { status: 400 });
  return Response.json({ run: plan });
}
""",
    )
    write(
        FUNCTIONS / "chat.js",
        """const SYSTEM = "你是「小顺」，顺德文旅策源助手。回答要简短、务实、口语化，围绕顺德美食店铺、文旅路线与政府协同给出可执行建议。";

export async function onRequestPost(ctx) {
  let message = "";
  try {
    const body = await ctx.request.json();
    message = (body && body.message ? String(body.message) : "").slice(0, 500);
  } catch {}
  const sse = (text) => {
    const lines = text
      .split(/(?<=[。！？!?\\n])/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => `data: ${JSON.stringify({ delta: s })}\\n\\n`)
      .join("");
    return new Response(lines + "data: [DONE]\\n\\n", {
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
    });
  };

  const key = ctx.env && ctx.env.DEEPSEEK_API_KEY;
  if (key) {
    try {
      const resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
        body: JSON.stringify({
          model: (ctx.env && ctx.env.DEEPSEEK_MODEL) || "deepseek-chat",
          messages: [{ role: "system", content: SYSTEM }, { role: "user", content: message }],
          stream: false,
          temperature: 0.8,
        }),
      });
      const data = await resp.json();
      const text = data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
      if (text) return sse(text);
    } catch {}
  }
  return sse(
    `我已经把「${message}」纳入顺德文旅行动方案。建议先聚焦一家真实店铺做深，再联动周末寻味路线与官方号、本地达人一起放大。`
  );
}
""",
    )


def main():
    if DEPLOY.exists():
        shutil.rmtree(DEPLOY)
    DEPLOY.mkdir(parents=True)
    build_static()
    data = build_data()
    build_functions(data)
    print(f"✓ 部署包已生成：{DEPLOY}")
    print(f"  - 店铺数：{len(data['leaderboard'])}")
    print(f"  - 地图标记：{len(data['locations'])}")
    print(f"  - 店铺详情：{len(data['shops'])}")
    print(f"  - 可回放方案：{len(data['plans'])}")


if __name__ == "__main__":
    main()
