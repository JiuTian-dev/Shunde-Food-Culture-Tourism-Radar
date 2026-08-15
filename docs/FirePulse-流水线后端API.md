# FirePulse 顺德 · 流水线后端 API 参考

> 城市烟火 IP 智能策源与增长引擎 —— Agent 工作流后端。全部为**纯增量**挂载，
> 既有的 `/api/status` `/api/shops` `/api/locations` `/api/leaderboard`
> `/api/shops/{id}` `/api/diagnose` `/api/forecast` `/api/chat` 均未改动。

## 流水线数据流

```
城市传播任务书 → 天眼雷达 → 烟火考古(资产卡) → 星火指数(9维+三指)
  → 爆点解码(8基因) → 灵感迁移(三档) → 灵感熔炉(创意方案) → [政府闸门] → 作战包 → 战情室
```

每次 `POST /api/workflow/run` 生成一个 `run_id`（`output/workflow/WF-*.json`），
9 个环节的 payload + source（`llm` / `rule` / `cached`）全部落盘可回读。

## 端点一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET  | `/api/events` | 事件库（20 个全网爆火案例，供选对标） |
| POST | `/api/mission` | 生成《城市传播任务书》 |
| GET  | `/api/radar` | 全域热点雷达（热点/弱信号/资源/机会清单） |
| GET  | `/api/asset-card/{shop_id}` | 烟火考古局 → 城市IP资产卡 |
| GET  | `/api/spark/{shop_id}` | 星火指数（9维100分 + 爆点/长红/留量三指） |
| GET  | `/api/decode/{event_id}` | 爆点解码器 → 8种爆款基因 |
| GET  | `/api/migrate?event_id=&shop_id=` | 灵感迁移器 → 稳健/突破/现象级三档 |
| POST | `/api/forge` | 灵感熔炉 → 创意方案（公式/脚本/矩阵/线下/媒体） |
| POST | `/api/workflow/run` | 端到端跑一轮流水线，返回《最终方案》 |
| POST | `/api/workflow/{run_id}/approve` | 政府人工闸门：审批 → 追加作战包+战情室 |
| GET  | `/api/workflow` | 运行列表（摘要） |
| GET  | `/api/workflow/{run_id}` | 运行详情（全环节 payload） |

## 请求示例

```bash
# 端到端（演示建议 use_llm=false，规则路径瞬时返回）
curl -X POST http://127.0.0.1:8000/api/workflow/run \
  -H "Content-Type: application/json" \
  -d '{"task_type":"承接网络热点","focus_shop_id":"SD-P01","focus_event_id":"EV-13","use_llm":false,"approve":true}'
```

`WorkflowRunRequest` 字段：`task_type`（默认承接网络热点）/`city`/`budget`/`window`/
`audience`/`resources`/`focus_shop_id`/`focus_event_id`/`approve`（默认 true，自动过闸门）/
`use_llm`（默认 true；false 时全链路走规则引擎，<1s）。

## 返回结构（/api/workflow/run）

```jsonc
{
  "run": {
    "run_id": "WF-20260815-001",
    "created": "...",
    "shop_id": "SD-P01", "shop_name": "莫氏鸡煲",
    "event_id": "EV-13", "event_name": "杭州「不正宗坐牢」湘菜馆",
    "status": "approved",          // awaiting_review / approved
    "decision": {"by":"政府决策层", "note":"...", "decided_at":"..."},
    "stages": {
      "mission":     {"source":"rule", "payload":{...}},
      "radar":       {"source":"rule", "payload":{...}},
      "asset_card":  {"source":"rule", "payload":{...}},
      "spark":       {"source":"rule", "payload":{...}},
      "decode":      {"source":"rule", "payload":{...}},
      "migrate":     {"source":"rule", "payload":{...}},
      "forge":       {"source":"rule", "payload":{...}},
      "ops_kit":     {"source":"rule", "payload":{...}},
      "warroom":     {"source":"rule", "payload":{...}}
    },
    "log": [ {"stage":"mission","source":"rule","brief":"..."} ]
  }
}
```

## 可靠性约定（演示永不中断）

- 每个 Agent 三层模式：LLM → 固化报告/规则 → 落盘。
- 每个 Agent 做**必需字段校验**：LLM 输出缺核心键时自动回退规则，防 KeyError 崩页。
- 只读 GET 端点默认 `use_llm=false`：避免慢 LLM 让演示卡 90s。
- 战情室监测数据为**模拟采集**（确定性生成），接入真实平台只需替换 `_mock_feed`。

## 冒烟验证

```bash
python scripts/smoke_workflow.py   # 13 项检查：事件库/任务书/雷达/资产卡/星火/解码/迁移/熔炉/作战包/战情室/编排器/回读/列表
```
