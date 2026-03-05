"""
集中管理模型、Agent、记忆与工具配置；敏感项（API Key）优先从环境变量读取。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

# 自动加载项目根目录 .env（若存在）
load_dotenv()

def _get_env(key: str, default: str = "") -> str:
    """从环境变量读取并去除首尾空白，空则返回 default。"""
    return os.environ.get(key, default).strip() or default


def _split_csv_env(key: str, default: str = "") -> tuple[str, ...]:
    """读取逗号分隔环境变量，输出规范化小写元组。"""
    raw = _get_env(key, default)
    if not raw:
        return ()
    return tuple(item.strip().lower() for item in raw.split(",") if item.strip())


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
    "max_consecutive_tool_failures": int(
        os.environ.get("JARVIS_MAX_CONSECUTIVE_TOOL_FAILURES", "3")
    ),
    "enable_session_trim": os.environ.get("JARVIS_ENABLE_SESSION_TRIM", "true").lower()
    in ("true", "1", "yes"),
    "max_session_messages": int(os.environ.get("JARVIS_MAX_SESSION_MESSAGES", "80")),
    "request_timeout_seconds": float(os.environ.get("JARVIS_REQUEST_TIMEOUT_SECONDS", "120")),
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
    "http_allow_hosts": _split_csv_env("JARVIS_HTTP_ALLOW_HOSTS", ""),
    "http_deny_hosts": _split_csv_env("JARVIS_HTTP_DENY_HOSTS", ""),
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
        model_config=load_model_config(),
        llm_config=LLM_CONFIG,
        agent_config=AGENT_CONFIG,
        tool_config=TOOL_CONFIG,
    )


def _provider_env_prefix(provider: str) -> str:
    return provider.upper().replace("-", "_")


def load_model_config() -> dict[str, dict[str, Any]]:
    """
    从 .env / 环境变量动态构建模型配置。
    通过 JARVIS_PROVIDERS 指定 provider 列表，例如：deepseek,gemini。
    每个 provider 读取：
      - <PROVIDER>_BASE_URL
      - <PROVIDER>_API_KEY
      - <PROVIDER>_MODEL
    """
    providers_env = _get_env("JARVIS_PROVIDERS", "deepseek,gemini")
    providers = [p.strip() for p in providers_env.split(",") if p.strip()]
    out: dict[str, dict[str, Any]] = {}
    for provider in providers:
        prefix = _provider_env_prefix(provider)
        out[provider] = {
            "base_url": _get_env(f"{prefix}_BASE_URL"),
            "api_key": _get_env(f"{prefix}_API_KEY"),
            "model": _get_env(f"{prefix}_MODEL"),
        }
    return out


def get_provider_model_config(provider: str) -> dict[str, Any]:
    cfg = load_model_config()
    if provider not in cfg:
        raise ValueError(f"未知 provider: {provider}，可选: {list(cfg.keys())}")
    return cfg[provider]


def collect_settings_errors() -> list[str]:
    """收集配置错误，返回错误列表（空列表表示配置合法）。"""
    settings = load_settings()
    errors: list[str] = []
    if not settings.model_config:
        errors.append("JARVIS_PROVIDERS 不能为空，至少配置一个 provider")
        return errors

    if settings.default_provider not in settings.model_config:
        errors.append(f"JARVIS_DEFAULT_PROVIDER={settings.default_provider} 不在 JARVIS_PROVIDERS 中")
    for provider, provider_cfg in settings.model_config.items():
        provider_key = provider.upper().replace("-", "_")
        if not provider_cfg.get("base_url"):
            errors.append(f"{provider_key}_BASE_URL 不能为空")
        if not provider_cfg.get("model"):
            errors.append(f"{provider_key}_MODEL 不能为空")

    if settings.llm_config["max_retries"] < 0:
        errors.append("JARVIS_LLM_MAX_RETRIES 不能小于 0")
    if settings.agent_config["max_iterations"] <= 0:
        errors.append("JARVIS_MAX_ITERATIONS 必须大于 0")
    if settings.agent_config["max_consecutive_tool_failures"] <= 0:
        errors.append("JARVIS_MAX_CONSECUTIVE_TOOL_FAILURES 必须大于 0")
    if settings.agent_config["max_session_messages"] <= 1:
        errors.append("JARVIS_MAX_SESSION_MESSAGES 必须大于 1")
    if settings.agent_config["request_timeout_seconds"] <= 0:
        errors.append("JARVIS_REQUEST_TIMEOUT_SECONDS 必须大于 0")
    if settings.tool_config["max_retries"] < 0:
        errors.append("JARVIS_TOOL_MAX_RETRIES 不能小于 0")
    return errors


def validate_settings() -> None:
    """校验 provider、重试与迭代等配置合法性；不通过时抛出 ValueError。"""
    errors = collect_settings_errors()
    if errors:
        details = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"配置校验失败，共 {len(errors)} 项：\n{details}")
