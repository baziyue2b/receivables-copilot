"""Configure the local Agno receivables agent."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd

from src.tools import build_analysis_tools


OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:4b"


class AgentUnavailableError(RuntimeError):
    """Raised when the local agent runtime is unavailable."""


def available_ollama_models(host: str = OLLAMA_HOST) -> list[str]:
    """Return locally installed model names from the Ollama service."""
    request = Request(f"{host}/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.load(response)
    except (OSError, URLError, TimeoutError) as exc:
        raise AgentUnavailableError(
            "无法连接 Ollama。请先启动 Ollama 桌面程序或运行 ollama serve。"
        ) from exc
    return [str(item.get("name", "")) for item in payload.get("models", [])]


def build_agent(
    frame: pd.DataFrame,
    model_id: str = DEFAULT_MODEL,
    host: str = OLLAMA_HOST,
):
    """Create one reusable Agno agent bound to the analyzed dataset."""
    models = available_ollama_models(host)
    if not any(name == model_id or name.startswith(f"{model_id}:") for name in models):
        raise AgentUnavailableError(
            f"本地没有模型 {model_id}。请先运行：ollama pull {model_id}"
        )

    try:
        from agno.agent import Agent
        from agno.models.ollama import Ollama
    except ImportError as exc:
        raise AgentUnavailableError(
            "缺少 Agent 依赖，请运行：pip install -r requirements.txt"
        ) from exc

    return Agent(
        name="Receivables Copilot",
        model=Ollama(
            id=model_id,
            host=host,
            api_key=None,
            keep_alive="10m",
            options={"temperature": 0.1},
        ),
        tools=build_analysis_tools(frame),
        instructions=[
            "你是一名谨慎的应收账款风险分析助手。",
            "涉及金额、账龄、客户排名时必须调用工具，不得自行估算。",
            "用简洁中文回答，并明确金额单位为人民币。",
            "没有数据支持时应直接说明，不得编造客户、金额或日期。",
            "不要要求或输出 API Key、密码及其他敏感信息。",
        ],
        markdown=True,
        add_history_to_context=True,
        num_history_runs=4,
        tool_call_limit=5,
    )


def ask_agent(agent, question: str) -> str:
    """Run one agent turn and normalize its text response."""
    try:
        response = agent.run(question)
    except Exception as exc:
        raise AgentUnavailableError(f"Agent 运行失败：{exc}") from exc
    content = response.content
    return content if isinstance(content, str) else str(content)

