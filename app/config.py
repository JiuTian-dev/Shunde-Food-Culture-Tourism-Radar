"""全局配置：LLM 连接与环境变量（OpenAI 兼容接口，默认接入 DeepSeek）。

配置优先级：环境变量 > .env 文件 > 默认值。
    QWEN_BASE_URL  = OpenAI 兼容接口地址（默认 https://api.deepseek.com/v1）
    QWEN_API_KEY   = 接口 API Key
    QWEN_MODEL     = 模型名（如 deepseek-v4-flash）

有 key 时启用真实 LLM Agent；无 key 时自动使用已生成结果兜底（见 agents/*）。
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def _load_dotenv(path: Path):
    """极简 .env 加载（不引入 python-dotenv 依赖）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if v.startswith(('"', "'")) and v.endswith(('"', "'")):
            v = v[1:-1]
        os.environ.setdefault(k, v)


_load_dotenv(ENV_PATH)

QWEN_BASE_URL = os.environ.get(
    "QWEN_BASE_URL",
    "https://api.deepseek.com/v1",
)
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "deepseek-v4-flash")

# 有 key 才启用真实 LLM
LLM_ENABLED = bool(QWEN_API_KEY)

# 无 key / 调用失败时，是否允许回退到已生成的 output/*.json
ALLOW_FALLBACK = True

# LLM 调用超时（秒）
LLM_TIMEOUT = 90
