"""Integration tests exercising the full per-user skill isolation flow.

Covers the surface that PR 3 wired up:

* :func:`deerflow.tools.skill_manage_tool.skill_manage_tool` writes to the
  user-scoped custom directory when an authenticated user is in context.
* :func:`deerflow.agents.lead_agent.prompt.get_skills_prompt_section` honours
  the same per-user override file when assembling the system prompt.
* The gateway ``PUT /api/skills/{name}`` route persists toggle decisions to
  the per-user override file rather than mutating the shared
  ``extensions_config.json``.
* :class:`deerflow.sandbox.local.local_sandbox_provider.LocalSandboxProvider`
  surfaces the calling user's custom skills under ``/mnt/skills/custom`` and
  keeps another user's skills invisible.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import skills as skills_router
from deerflow.config.paths import Paths
from deerflow.skills.enabled_state import read_user_skill_overrides

skill_manage_module = importlib.import_module("deerflow.tools.skill_manage_tool")


SKILL_BODY = """---
name: {name}
description: A test skill named {name}.
---

# {name}
"""


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_config(skills_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        skills=SimpleNamespace(
            get_skills_path=lambda: skills_root,
            container_path="/mnt/skills",
            use="deerflow.skills.storage.local_skill_storage:LocalSkillStorage",
        ),
        skill_evolution=SimpleNamespace(enabled=True, moderation_model_name=None),
    )


async def _allow_scan(*_args, **_kwargs):
    from deerflow.skills.security_scanner import ScanResult

    return ScanResult(decision="allow", reason="ok")


async def _noop_refresh():
    return None


@pytest.fixture()
def base_dir(tmp_path: Path) -> Path:
    return tmp_path / "deer-flow-data"


@pytest.fixture()
def skills_root(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    (root / "public").mkdir(parents=True)
    (root / "custom").mkdir(parents=True)
    return root


@pytest.fixture()
def patch_paths(base_dir: Path):
    paths = Paths(base_dir)
    with (
        patch("deerflow.config.paths.get_paths", return_value=paths),
        patch("deerflow.skills.enabled_state.get_paths", return_value=paths),
    ):
        yield paths


@pytest.fixture()
def patched_config(monkeypatch, skills_root: Path):
    config = _make_config(skills_root)
    monkeypatch.setattr("deerflow.config.get_app_config", lambda: config)
    monkeypatch.setattr("deerflow.skills.security_scanner.get_app_config", lambda: config)
    monkeypatch.setattr(skill_manage_module, "scan_skill_content", _allow_scan)
    monkeypatch.setattr(skill_manage_module, "refresh_skills_system_prompt_cache_async", _noop_refresh)
    yield config


# ---------------------------------------------------------------------------
# 1. skill_manage tool writes to per-user paths
# ---------------------------------------------------------------------------


@pytest.mark.no_auto_user
def test_skill_manage_tool_writes_to_user_scoped_dir(base_dir: Path, skills_root: Path, patch_paths, patched_config):
    """A request authenticated as alice persists her new skill under her bucket."""
    runtime = SimpleNamespace(
        context={"thread_id": "thread-1", "user_id": "alice"},
        config={"configurable": {"thread_id": "thread-1"}},
    )

    result = anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        runtime,
        "create",
        "alice-skill",
        SKILL_BODY.format(name="alice-skill"),
    )
    assert "Created custom skill" in result

    expected = base_dir.resolve() / "users" / "alice" / "skills" / "custom" / "alice-skill" / "SKILL.md"
    assert expected.exists()

    # The legacy global custom dir must remain untouched for an auth'd write.
    assert not (skills_root / "custom" / "alice-skill").exists()


@pytest.mark.no_auto_user
def test_skill_manage_tool_two_users_do_not_see_each_others_writes(base_dir: Path, patch_paths, patched_config):
    """Alice and Bob can each have a skill with the same name, isolated on disk."""
    alice_runtime = SimpleNamespace(
        context={"thread_id": "thread-1", "user_id": "alice"},
        config={"configurable": {"thread_id": "thread-1"}},
    )
    bob_runtime = SimpleNamespace(
        context={"thread_id": "thread-2", "user_id": "bob"},
        config={"configurable": {"thread_id": "thread-2"}},
    )

    anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        alice_runtime,
        "create",
        "shared-name",
        SKILL_BODY.format(name="shared-name") + "\n# alice variant\n",
    )
    anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        bob_runtime,
        "create",
        "shared-name",
        SKILL_BODY.format(name="shared-name") + "\n# bob variant\n",
    )

    alice_md = (base_dir.resolve() / "users" / "alice" / "skills" / "custom" / "shared-name" / "SKILL.md").read_text()
    bob_md = (base_dir.resolve() / "users" / "bob" / "skills" / "custom" / "shared-name" / "SKILL.md").read_text()
    assert "alice variant" in alice_md
    assert "bob variant" in bob_md
    assert "bob variant" not in alice_md
    assert "alice variant" not in bob_md


# ---------------------------------------------------------------------------
# 2. Lead-agent system prompt is per-user
# ---------------------------------------------------------------------------


@pytest.mark.no_auto_user
def test_system_prompt_excludes_other_users_skills(monkeypatch, base_dir: Path, skills_root: Path, patch_paths, patched_config):
    """The prompt builder pins skill visibility to the calling user."""
    # Two users, each with a distinct custom skill.
    alice_runtime = SimpleNamespace(
        context={"thread_id": "thread-1", "user_id": "alice"},
        config={"configurable": {"thread_id": "thread-1"}},
    )
    bob_runtime = SimpleNamespace(
        context={"thread_id": "thread-2", "user_id": "bob"},
        config={"configurable": {"thread_id": "thread-2"}},
    )
    anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        alice_runtime,
        "create",
        "alice-only",
        SKILL_BODY.format(name="alice-only"),
    )
    anyio.run(
        skill_manage_module.skill_manage_tool.coroutine,
        bob_runtime,
        "create",
        "bob-only",
        SKILL_BODY.format(name="bob-only"),
    )

    from deerflow.agents.lead_agent.prompt import get_skills_prompt_section

    alice_section = get_skills_prompt_section(app_config=patched_config, user_id="alice")
    bob_section = get_skills_prompt_section(app_config=patched_config, user_id="bob")

    assert "alice-only" in alice_section
    assert "bob-only" not in alice_section
    assert "bob-only" in bob_section
    assert "alice-only" not in bob_section


# ---------------------------------------------------------------------------
# 3. Gateway PUT /api/skills/{name} writes a per-user override
# ---------------------------------------------------------------------------


def _make_test_app(config) -> FastAPI:
    app = FastAPI()
    app.state.config = config
    app.include_router(skills_router.router)
    return app


@pytest.fixture()
def auth_user_alice():
    """Mirror the autouse fixture but pin the user to ``alice`` for these tests."""
    from deerflow.runtime.user_context import reset_current_user, set_current_user

    token = set_current_user(SimpleNamespace(id="alice", email="alice@example.com"))
    try:
        yield
    finally:
        reset_current_user(token)


@pytest.mark.no_auto_user
def test_update_skill_writes_per_user_override(monkeypatch, base_dir: Path, skills_root: Path, patch_paths, patched_config, auth_user_alice):
    """Toggling a skill for alice persists to her override file, not the global config."""
    public_dir = skills_root / "public" / "deep-research"
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "SKILL.md").write_text(SKILL_BODY.format(name="deep-research"), encoding="utf-8")

    # Stub out the global config writer so we can assert it was *not* touched.
    global_writes: list[Path] = []

    real_open = open

    def _tracking_open(path, *args, **kwargs):
        if isinstance(path, (str, Path)) and "extensions_config.json" in str(path) and "w" in args[0] if args else False:
            global_writes.append(Path(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("app.gateway.routers.skills.refresh_skills_system_prompt_cache_async", _noop_refresh)

    app = _make_test_app(patched_config)
    with TestClient(app) as client:
        response = client.put("/api/skills/deep-research", json={"enabled": False})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "deep-research"
    assert body["enabled"] is False

    # Per-user override file is created.
    overrides = read_user_skill_overrides("alice")
    assert overrides == {"deep-research": False}

    # The global extensions_config.json is NOT touched.
    assert global_writes == []


# ---------------------------------------------------------------------------
# 4. Sandbox path mapping is per-user
# ---------------------------------------------------------------------------


@pytest.mark.no_auto_user
def test_sandbox_acquire_maps_custom_skills_per_user(monkeypatch, base_dir: Path, skills_root: Path, patch_paths, patched_config, auth_user_alice):
    """LocalSandboxProvider.acquire() exposes the calling user's custom dir at /mnt/skills/custom."""
    from deerflow.sandbox.local.local_sandbox_provider import LocalSandboxProvider

    # Pre-create alice's custom dir so the mapping points at an existing path.
    alice_custom = base_dir.resolve() / "users" / "alice" / "skills" / "custom"
    alice_custom.mkdir(parents=True, exist_ok=True)

    provider = LocalSandboxProvider()
    sandbox_id = provider.acquire("thread-1")
    sandbox = provider.get(sandbox_id)
    assert sandbox is not None

    mapping = next((m for m in sandbox.path_mappings if m.container_path == "/mnt/skills/custom"), None)
    assert mapping is not None
    assert Path(mapping.local_path) == alice_custom


@pytest.mark.no_auto_user
def test_sandbox_acquire_without_auth_uses_legacy_skills_mapping(monkeypatch, base_dir: Path, skills_root: Path, patch_paths, patched_config):
    """Without an authenticated user, /mnt/skills/custom is served via the legacy static mapping."""
    from deerflow.sandbox.local.local_sandbox_provider import LocalSandboxProvider

    provider = LocalSandboxProvider()
    sandbox_id = provider.acquire("thread-1")
    sandbox = provider.get(sandbox_id)
    assert sandbox is not None

    # No per-thread /mnt/skills/custom mapping is added.
    per_thread_custom = next((m for m in sandbox.path_mappings if m.container_path == "/mnt/skills/custom"), None)
    assert per_thread_custom is None

    # The static /mnt/skills mapping pointing at the legacy root is still present.
    static = next((m for m in sandbox.path_mappings if m.container_path == "/mnt/skills"), None)
    assert static is not None
    assert Path(static.local_path) == skills_root
