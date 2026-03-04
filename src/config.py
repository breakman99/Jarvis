"""
集中管理模型、Agent 与记忆配置。敏感项（API Key）优先从环境变量读取。
"""
from __future__ import annotations

import os
from typing import Any

# 模型配置：api_key 优先从环境变量读取，避免提交到版本库
def _get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip() or default


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

# LLM 调用：重试与超时（基础设施层）
LLM_CONFIG = {
    "max_retries": int(os.environ.get("JARVIS_LLM_MAX_RETRIES", "3")),
    "base_backoff_ms": int(os.environ.get("JARVIS_LLM_BASE_BACKOFF_MS", "1000")),
    "max_backoff_ms": int(os.environ.get("JARVIS_LLM_MAX_BACKOFF_MS", "30000")),
    "timeout_seconds": float(os.environ.get("JARVIS_LLM_TIMEOUT_SECONDS", "60")),
}

AGENT_CONFIG = {
    "max_iterations": int(os.environ.get("JARVIS_MAX_ITERATIONS", "10")),
    "enable_planner": os.environ.get("JARVIS_ENABLE_PLANNER", "true").lower() in ("true", "1", "yes"),
    "memory_backend": os.environ.get("JARVIS_MEMORY_BACKEND", "sqlite"),
    "memory_file_path": os.environ.get("JARVIS_MEMORY_FILE_PATH", ".jarvis/memory.json"),
    "memory_db_path": os.environ.get("JARVIS_MEMORY_DB_PATH", ".jarvis/memory.db"),
    "enable_multi_agent": os.environ.get("JARVIS_ENABLE_MULTI_AGENT", "false").lower() in ("true", "1", "yes"),
}

# 工具执行：可选重试（仅对标记为可重试的工具）
TOOL_CONFIG = {
    "max_retries": int(os.environ.get("JARVIS_TOOL_MAX_RETRIES", "2")),
    "retryable_errors": ("timeout", "connection", "5xx"),
}
