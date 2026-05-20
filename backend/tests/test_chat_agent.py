"""Tests for the vanilla chat agent factory."""

from __future__ import annotations

import inspect

import pytest

from deerflow.agents.chat_agent import agent as chat_agent_module
from deerflow.agents.middlewares.memory_middleware import MemoryMiddleware
from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from deerflow.agents.middlewares.title_middleware import TitleMiddleware
from deerflow.agents.middlewares.token_usage_middleware import TokenUsageMiddleware
from deerflow.config.app_config import AppConfig
from deerflow.config.memory_config import MemoryConfig
from deerflow.config.model_config import ModelConfig
from deerflow.config.sandbox_config import SandboxConfig
from deerflow.config.token_usage_config import TokenUsageConfig


def _make_app_config(
    models: list[ModelConfig],
    *,
    memory_enabled: bool = False,
    token_usage_enabled: bool = False,
) -> AppConfig:
    return AppConfig(
        models=models,
        sandbox=SandboxConfig(use="deerflow.sandbox.local:LocalSandboxProvider"),
        memory=MemoryConfig(enabled=memory_enabled),
        token_usage=TokenUsageConfig(enabled=token_usage_enabled),
    )


def _make_model(name: str, *, supports_thinking: bool = False) -> ModelConfig:
    return ModelConfig(
        name=name,
        display_name=name,
        description=None,
        use="langchain_openai:ChatOpenAI",
        model=name,
        supports_thinking=supports_thinking,
        supports_vision=False,
    )


def test_make_chat_agent_signature_matches_langgraph_server_factory_abi():
    assert list(inspect.signature(chat_agent_module.make_chat_agent).parameters) == ["config"]


def test_make_chat_agent_uses_runtime_model_from_context(monkeypatch):
    app_config = _make_app_config(
        [
            _make_model("default-model"),
            _make_model("context-model"),
        ]
    )

    captured: dict[str, object] = {}

    def _fake_create_chat_model(*, name, thinking_enabled, reasoning_effort=None, app_config=None):
        captured["name"] = name
        captured["thinking_enabled"] = thinking_enabled
        captured["reasoning_effort"] = reasoning_effort
        captured["app_config"] = app_config
        return object()

    monkeypatch.setattr(chat_agent_module, "create_chat_model", _fake_create_chat_model)
    monkeypatch.setattr(chat_agent_module, "create_agent", lambda **kwargs: kwargs)

    result = chat_agent_module.make_chat_agent(
        {
            "context": {
                "model_name": "context-model",
                "app_config": app_config,
            }
        }
    )

    assert captured["name"] == "context-model"
    assert captured["thinking_enabled"] is False
    assert captured["app_config"] is app_config
    assert result["tools"] == []
    assert result["system_prompt"] == ""


def test_make_chat_agent_falls_back_to_default_model(monkeypatch, caplog):
    app_config = _make_app_config([_make_model("default-model")])

    monkeypatch.setattr(chat_agent_module, "create_chat_model", lambda **kwargs: object())
    monkeypatch.setattr(chat_agent_module, "create_agent", lambda **kwargs: kwargs)

    with caplog.at_level("WARNING"):
        result = chat_agent_module.make_chat_agent(
            {"context": {"model_name": "missing-model", "app_config": app_config}}
        )

    assert result["model"] is not None
    assert "fallback to default model 'default-model'" in caplog.text


def test_make_chat_agent_disables_thinking_when_model_does_not_support_it(monkeypatch):
    app_config = _make_app_config([_make_model("non-thinking-model", supports_thinking=False)])

    captured: dict[str, object] = {}

    def _fake_create_chat_model(*, name, thinking_enabled, reasoning_effort=None, app_config=None):
        captured["thinking_enabled"] = thinking_enabled
        return object()

    monkeypatch.setattr(chat_agent_module, "create_chat_model", _fake_create_chat_model)
    monkeypatch.setattr(chat_agent_module, "create_agent", lambda **kwargs: kwargs)

    chat_agent_module.make_chat_agent(
        {
            "context": {
                "model_name": "non-thinking-model",
                "thinking_enabled": True,
                "app_config": app_config,
            }
        }
    )

    assert captured["thinking_enabled"] is False


def test_build_middlewares_always_includes_thread_data(monkeypatch):
    app_config = _make_app_config([_make_model("any-model")], memory_enabled=False)

    middlewares = chat_agent_module._build_middlewares(
        agent_name=None,
        memory_enabled=False,
        app_config=app_config,
    )

    assert any(isinstance(m, ThreadDataMiddleware) for m in middlewares)
    # Empty memory config + memory_enabled=False -> no MemoryMiddleware
    assert not any(isinstance(m, MemoryMiddleware) for m in middlewares)


def test_build_middlewares_includes_memory_when_both_flags_enabled():
    app_config = _make_app_config([_make_model("any-model")], memory_enabled=True)

    middlewares = chat_agent_module._build_middlewares(
        agent_name="my-agent",
        memory_enabled=True,
        app_config=app_config,
    )

    assert any(isinstance(m, MemoryMiddleware) for m in middlewares)


def test_build_middlewares_omits_memory_when_request_disables_it():
    app_config = _make_app_config([_make_model("any-model")], memory_enabled=True)

    middlewares = chat_agent_module._build_middlewares(
        agent_name=None,
        memory_enabled=False,
        app_config=app_config,
    )

    assert not any(isinstance(m, MemoryMiddleware) for m in middlewares)


def test_build_middlewares_omits_memory_when_global_config_disabled():
    app_config = _make_app_config([_make_model("any-model")], memory_enabled=False)

    middlewares = chat_agent_module._build_middlewares(
        agent_name=None,
        memory_enabled=True,
        app_config=app_config,
    )

    assert not any(isinstance(m, MemoryMiddleware) for m in middlewares)


def test_build_middlewares_includes_title_middleware():
    app_config = _make_app_config([_make_model("any-model")])

    middlewares = chat_agent_module._build_middlewares(
        agent_name=None,
        memory_enabled=False,
        app_config=app_config,
    )

    assert any(isinstance(m, TitleMiddleware) for m in middlewares)


def test_build_middlewares_token_usage_follows_config():
    app_config_off = _make_app_config([_make_model("any-model")], token_usage_enabled=False)
    middlewares_off = chat_agent_module._build_middlewares(
        agent_name=None, memory_enabled=False, app_config=app_config_off
    )
    assert not any(isinstance(m, TokenUsageMiddleware) for m in middlewares_off)

    app_config_on = _make_app_config([_make_model("any-model")], token_usage_enabled=True)
    middlewares_on = chat_agent_module._build_middlewares(
        agent_name=None, memory_enabled=False, app_config=app_config_on
    )
    assert any(isinstance(m, TokenUsageMiddleware) for m in middlewares_on)


def test_make_chat_agent_raises_when_no_models_configured(monkeypatch):
    app_config = _make_app_config([])

    monkeypatch.setattr(chat_agent_module, "get_app_config", lambda: app_config)

    with pytest.raises(ValueError, match="No chat models are configured"):
        chat_agent_module.make_chat_agent({"context": {"model_name": "anything"}})
