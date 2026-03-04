"""
集中管理模型、Agent、记忆与工具配置；敏感项（API Key）优先从环境变量读取。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _get_env(key: str, default: str = "") -> str:
    """从环境变量读取并去除首尾空白，空则返回 default。"""
    return os.environ.get(key, default).strip() or default


# ---------- 模型配置 ----------
# api_key 优先从环境变量读取，避免提交到版本库
MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "deepseek": {
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key": _get_env("DEEPSEEK_API_KEY"),
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    },
    "gemini": {
        "base_url": os.environ.get(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        "api_key": _get_env("GEMINI_API_KEY"),
        "model": os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
    },
}

DEFAULT_PROVIDER = os.environ.get("JARVIS_DEFAULT_PROVIDER", "deepseek")

# ---------- LLM 调用：重试与超时（基础设施层） ----------
LLM_CONFIG = {
    "max_retries": int(os.environ.get("JARVIS_LLM_MAX_RETRIES", "3")),
    "base_backoff_ms": int(os.environ.get("JARVIS_LLM_BASE_BACKOFF_MS", "1000")),
    "max_backoff_ms": int(os.environ.get("JARVIS_LLM_MAX_BACKOFF_MS", "30000")),
    "timeout_seconds": float(os.environ.get("JARVIS_LLM_TIMEOUT_SECONDS", "60")),
}

# ---------- Agent 与记忆 ----------
AGENT_CONFIG = {
    "max_iterations": int(os.environ.get("JARVIS_MAX_ITERATIONS", "10")),
    "enable_planning": os.environ.get(
        "JARVIS_ENABLE_PLANNING",
        os.environ.get("JARVIS_ENABLE_PLANNER", "true"),
    ).lower() in ("true", "1", "yes"),
    "memory_backend": os.environ.get("JARVIS_MEMORY_BACKEND", "sqlite"),
    "memory_file_path": os.environ.get("JARVIS_MEMORY_FILE_PATH", ".jarvis/memory.json"),
    "memory_db_path": os.environ.get("JARVIS_MEMORY_DB_PATH", ".jarvis/memory.db"),
}

# ---------- 工具执行：可选重试（仅对 idempotent 工具） ----------
TOOL_CONFIG = {
    "max_retries": int(os.environ.get("JARVIS_TOOL_MAX_RETRIES", "2")),
    "retryable_errors": ("timeout", "connection", "5xx"),
}


@dataclass(frozen=True)
class AppSettings:
    """只读配置快照，供校验与依赖注入使用。"""
    default_provider: str
    model_config: dict[str, dict[str, Any]]
    llm_config: dict[str, Any]
    agent_config: dict[str, Any]
    tool_config: dict[str, Any]


def load_settings() -> AppSettings:
    """加载当前环境下的全部配置为 AppSettings。"""
    return AppSettings(
        default_provider=DEFAULT_PROVIDER,
        model_config=MODEL_CONFIG,
        llm_config=LLM_CONFIG,
        agent_config=AGENT_CONFIG,
        tool_config=TOOL_CONFIG,
    )


def validate_settings() -> None:
    """校验 provider、重试与迭代等配置合法性；不通过时抛出 ValueError。"""
    settings = load_settings()
    if settings.default_provider not in settings.model_config:
        raise ValueError(
            f"JARVIS_DEFAULT_PROVIDER={settings.default_provider} 不在 MODEL_CONFIG 中"
        )
    if settings.llm_config["max_retries"] < 0:
        raise ValueError("JARVIS_LLM_MAX_RETRIES 不能小于 0")
    if settings.agent_config["max_iterations"] <= 0:
        raise ValueError("JARVIS_MAX_ITERATIONS 必须大于 0")
    if settings.tool_config["max_retries"] < 0:
        raise ValueError("JARVIS_TOOL_MAX_RETRIES 不能小于 0")
