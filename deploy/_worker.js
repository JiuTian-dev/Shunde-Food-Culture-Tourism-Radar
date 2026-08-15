import { DATA } from "./_data.js";

const SYSTEM = "你是「小顺」，顺德文旅策源助手。回答要简短、务实、口语化，围绕顺德美食店铺、文旅路线与政府协同给出可执行建议。";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // GET /api/status
    if (path === "/api/status" && method === "GET") {
      const enabled = !!(env && env.DEEPSEEK_API_KEY);
      return Response.json({
        llm_enabled: enabled,
        model: (env && env.DEEPSEEK_MODEL) || "deepseek-chat",
        mode: enabled ? "LLM Agent 在线" : "内置报告回放",
        shop_count: 36,
      });
    }

    // GET /api/leaderboard
    if (path === "/api/leaderboard" && method === "GET") {
      return Response.json({ items: DATA.leaderboard, total: DATA.leaderboard.length });
    }

    // GET /api/locations
    if (path === "/api/locations" && method === "GET") {
      return Response.json({ items: DATA.locations, total: DATA.locations.length });
    }

    // GET /api/shops/:id
    const shopMatch = path.match(/^\/api\/shops\/(.+)$/);
    if (shopMatch && method === "GET") {
      const id = decodeURIComponent(shopMatch[1]);
      const d = DATA.shops[id];
      if (!d) return Response.json({ detail: `未找到店铺 ${id}` }, { status: 404 });
      return Response.json(d);
    }

    // POST /api/chat
    if (path === "/api/chat" && method === "POST") {
      let message = "";
      try {
        const body = await request.json();
        message = (body && body.message ? String(body.message) : "").slice(0, 500);
      } catch {}
      const sse = (text) => {
        const lines = text
          .split(/(?<=[。！？!?\n])/)
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s) => `data: ${JSON.stringify({ delta: s })}\n\n`)
          .join("");
        return new Response(lines + "data: [DONE]\n\n", {
          headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
        });
      };

      const key = env && env.DEEPSEEK_API_KEY;
      if (key) {
        try {
          const resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
            body: JSON.stringify({
              model: (env && env.DEEPSEEK_MODEL) || "deepseek-chat",
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

    // POST /api/workflow/run
    if (path === "/api/workflow/run" && method === "POST") {
      let focus = "SD-C15";
      try {
        const body = await request.json();
        if (body && body.focus_shop_id) focus = body.focus_shop_id;
      } catch {}
      const plan = DATA.plans[focus] || DATA.fallback;
      if (!plan) return Response.json({ detail: "暂无可用方案" }, { status: 400 });
      return Response.json({ run: plan });
    }

    // 默认：返回静态资源
    return env.ASSETS.fetch(request);
  },
};
