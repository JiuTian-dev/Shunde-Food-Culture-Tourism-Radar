# 顺德寻味 · 城市增长驾驶舱 🍜🏙️

> 帮顺德文旅与宣传部门，把"该爆但还没爆"的本地美食店变成可执行的城市行动方案。
> 单 Agent 完成"发现—挖掘—诊断—预测—传播"全链路，把"网红偶然性"变成"可计算的潜力"。

---

## 在线 Demo

- 线上地址：https://shunde-food-radar.pages.dev/
- 本地启动：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` → 浏览器打开 http://127.0.0.1:8000

---

## 核心功能

| 模块 | 说明 |
|---|---|
| 🗺️ 城市味觉地图 | 36 家顺德美食店按坐标落点，点击查看店铺档案 |
| 📊 潜力榜 | 按爆款指数排序，A 类重点孵化置顶 |
| 🏪 店铺档案 | 品类 / 主理人人设 / 视觉卖点 / 定价能力 / 事实依据，全部可溯源 |
| 🔍 诊断报告 | 五维打分 + 爆款指数 + 红/黄线风险门槛 + 压力测试 + 结论 |
| 📈 流量预测 | 对标莫氏鸡煲的引爆力系数、曝光/客流/排队/周期量级、变现回报 |
| 🚀 政府助推方案 | 选中店铺一键生成城市行动方案（9 阶段：任务→雷达→资产卡→星火指数→基因解码→迁移方案→灵感熔炉→作战包→战情室）|
| 📖 全屏方案书 | 按章节展示完整方案，供决策者阅读 |
| 💬 小顺对话助手 | 文旅策划搭子，支持 DeepSeek 流式对话 |

---

## 核心逻辑

### 爆款指数（五维加权）
```
爆款指数 = 0.25×人设反差度 + 0.25×风味品相度 + 0.20×故事叙事性
        + 0.20×情绪共鸣度 + 0.10×素材续航度
```

| 等级 | 区间 | 处置 |
|---|---|---|
| **A** | ≥75 | 重点孵化 |
| **B** | 60–75 | 待观察 |
| **C** | <60 | 不推荐 |

### 风险门槛（不是加分项）
- 🔴 红线（卫生/安全/资质）→ 一票否决
- 🟡 黄线（产能不足/主理人抗拒）→ 降级"需先扶持"
- ⚪ 提示项 → 执行时注意

### 流量预测：对标莫氏法
以「莫氏鸡煲」（爆款指数 94.1）为锚点，对任何一家店：`引爆力 = min(指数/94.1, 1)`，`曝光 = 1.5亿 × 引爆力 × 品类系数`，**产能硬约束封顶**——先算能不能接住流量，再谈放大。

---

## 项目结构

```
顺德黑客松/
├─ app/                       Python 后端
│  ├─ agents/                 单 Agent 工作流（诊断/预测/策源等）
│  ├─ static/index.html       单文件 Web 看板
│  ├─ main.py                 FastAPI 后端
│  ├─ data_loader.py          数据加载 + 指数计算
│  └─ llm.py                  LLM 封装
├─ deploy/                    Cloudflare Pages 部署包
│  ├─ _worker.js              Pages Worker（API 路由）
│  ├─ _data.js                线上数据
│  ├─ index.html              线上前端
│  └─ static/                 静态资源
├─ data/                      数据集
│  ├─ candidates.yaml         25 家候选店铺
│  ├─ events.yaml             热点事件库
│  ├─ location.yaml           地图坐标
│  ├─ positive.yaml           已验证爆款（正样本）
│  └─ negative.yaml           有名但没爆（负样本）
├─ docs/                      产品与技术文档
├─ scripts/                   构建与验证脚本
└─ wrangler.toml              Cloudflare Pages 配置
```

---

## 部署

### Cloudflare Pages（线上）
```bash
npx wrangler pages deploy deploy --project-name=shunde-food-radar --branch=main
```

### 本地开发
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

LLM 配置（可选，不配置则使用内置规则引擎）：
```bash
# .env
QWEN_API_KEY=你的key
QWEN_MODEL=deepseek-v4-flash
```

---

## 数据集

36 家店全部来自真实公开信息（网易《寻味顺德》系列、小红书/抖音传播事件、新闻报道），每条带 `evidence`（来源+链接+日期）。

---

*顺德寻味 · 城市增长驾驶舱 · 顺德黑客松作品*
