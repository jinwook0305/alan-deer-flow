"""Minimal vanilla chat agent: plain multi-turn LLM with no tools or skills."""

import logging

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.runnables import RunnableConfig

from deerflow.agents.middlewares.memory_middleware import MemoryMiddleware
from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from deerflow.agents.middlewares.title_middleware import TitleMiddleware
from deerflow.agents.middlewares.token_usage_middleware import TokenUsageMiddleware
from deerflow.agents.thread_state import ThreadState
from deerflow.config.app_config import AppConfig, get_app_config
from deerflow.models import create_chat_model

logger = logging.getLogger(__name__)


def _get_runtime_config(config: RunnableConfig) -> dict:
    cfg = dict(config.get("configurable", {}) or {})
    context = config.get("context", {}) or {}
    if isinstance(context, dict):
        cfg.update(context)
    return cfg


def _resolve_model_name(requested: str | None, *, app_config: AppConfig) -> str:
    default_model_name = app_config.models[0].name if app_config.models else None
    if default_model_name is None:
        raise ValueError("No chat models are configured. Please configure at least one model in config.yaml.")
    if requested and app_config.get_model_config(requested):
        return requested
    if requested and requested != default_model_name:
        logger.warning("Model '%s' not found in config; fallback to default model '%s'.", requested, default_model_name)
    return default_model_name


def _build_middlewares(*, agent_name: str | None, memory_enabled: bool, app_config: AppConfig) -> list[AgentMiddleware]:
    # ThreadDataMiddleware is required so the chat run has thread paths and the
    # last HumanMessage carries the standard run_id/timestamp metadata.
    middlewares: list[AgentMiddleware] = [ThreadDataMiddleware(lazy_init=True)]

    if app_config.token_usage.enabled:
        middlewares.append(TokenUsageMiddleware())

    # TitleMiddleware lets the sidebar show a sensible label after the first exchange.
    middlewares.append(TitleMiddleware(app_config=app_config))

    # MemoryMiddleware is opt-in for vanilla chat: only attach if both the global
    # memory config and the per-request flag are enabled.
    if memory_enabled and app_config.memory.enabled:
        middlewares.append(MemoryMiddleware(agent_name=agent_name, memory_config=app_config.memory))

    return middlewares


def make_chat_agent(config: RunnableConfig):
    """LangGraph graph factory for plain LLM chat. No tools, no skills, no system prompt."""
    cfg = _get_runtime_config(config)
    app_config: AppConfig = cfg.get("app_config") or get_app_config()

    requested_model_name: str | None = cfg.get("model_name") or cfg.get("model")
    model_name = _resolve_model_name(requested_model_name, app_config=app_config)

    thinking_enabled = bool(cfg.get("thinking_enabled", False))
    reasoning_effort = cfg.get("reasoning_effort", None)
    memory_enabled = bool(cfg.get("memory_enabled", False))
    agent_name = cfg.get("agent_name")

    model_config = app_config.get_model_config(model_name)
    if model_config is None:
        raise ValueError("No chat model could be resolved. Please configure at least one model in config.yaml or provide a valid 'model_name'/'model' in the request.")
    if thinking_enabled and not model_config.supports_thinking:
        logger.warning("Thinking mode is enabled but model '%s' does not support it; fallback to non-thinking mode.", model_name)
        thinking_enabled = False

    logger.info(
        "Create ChatAgent -> model_name: %s, thinking_enabled: %s, memory_enabled: %s",
        model_name,
        thinking_enabled,
        memory_enabled,
    )

    if "metadata" not in config:
        config["metadata"] = {}
    config["metadata"].update(
        {
            "agent_name": "chat_agent",
            "model_name": model_name,
            "thinking_enabled": thinking_enabled,
            "reasoning_effort": reasoning_effort,
            "memory_enabled": memory_enabled,
        }
    )

    return create_agent(
        model=create_chat_model(name=model_name, thinking_enabled=thinking_enabled, reasoning_effort=reasoning_effort, app_config=app_config),
        tools=[],
        middleware=_build_middlewares(agent_name=agent_name, memory_enabled=memory_enabled, app_config=app_config),
        system_prompt="",
        state_schema=ThreadState,
    )
