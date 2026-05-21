"""Tests for per-user skill enable-state overrides and load_skills merge."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from deerflow.config.extensions_config import (
    ExtensionsConfig,
    SkillStateConfig,
    reset_extensions_config,
    set_extensions_config,
)
from deerflow.config.paths import Paths
from deerflow.skills.enabled_state import (
    CURRENT_VERSION,
    clear_user_skill_override,
    get_user_skill_override,
    read_user_skill_overrides,
    set_user_skill_override,
)
from deerflow.skills.storage import get_or_new_skill_storage

SKILL_TEMPLATE = """---
name: {name}
description: A test skill named {name}.
---

# {name}
"""


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
def storage(skills_root: Path):
    return get_or_new_skill_storage(skills_path=str(skills_root))


@pytest.fixture()
def patched_paths(base_dir: Path):
    paths = Paths(base_dir)
    # Patch every module-local import of get_paths that this PR touches.
    with (
        patch("deerflow.config.paths.get_paths", return_value=paths),
        patch("deerflow.skills.enabled_state.get_paths", return_value=paths),
    ):
        yield paths


@pytest.fixture()
def empty_extensions_config():
    """Force ExtensionsConfig.from_file() to return an empty config."""
    set_extensions_config(ExtensionsConfig(mcp_servers={}, skills={}))
    with patch.object(ExtensionsConfig, "from_file", classmethod(lambda cls, config_path=None: ExtensionsConfig(mcp_servers={}, skills={}))):
        yield
    reset_extensions_config()


def _write_public_skill(skills_root: Path, name: str) -> None:
    skill_dir = skills_root / "public" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name), encoding="utf-8")


# ---------------------------------------------------------------------------
# enabled_state primitives
# ---------------------------------------------------------------------------


def test_read_returns_empty_when_file_missing(patched_paths):
    assert read_user_skill_overrides("alice") == {}


def test_set_then_read(patched_paths):
    set_user_skill_override("alice", "demo-skill", True)
    assert read_user_skill_overrides("alice") == {"demo-skill": True}


def test_set_persists_to_user_scoped_file(base_dir: Path, patched_paths):
    set_user_skill_override("alice", "demo-skill", False)
    file_path = base_dir.resolve() / "users" / "alice" / "skills_enabled.json"
    assert file_path.exists()
    payload = json.loads(file_path.read_text())
    assert payload["version"] == CURRENT_VERSION
    assert payload["skills"]["demo-skill"]["enabled"] is False


def test_set_two_skills_keeps_both(patched_paths):
    set_user_skill_override("alice", "skill-a", True)
    set_user_skill_override("alice", "skill-b", False)
    assert read_user_skill_overrides("alice") == {"skill-a": True, "skill-b": False}


def test_overwriting_a_skill_updates_only_that_entry(patched_paths):
    set_user_skill_override("alice", "skill-a", True)
    set_user_skill_override("alice", "skill-b", True)
    set_user_skill_override("alice", "skill-a", False)
    assert read_user_skill_overrides("alice") == {"skill-a": False, "skill-b": True}


def test_clear_removes_override(patched_paths):
    set_user_skill_override("alice", "skill-a", True)
    set_user_skill_override("alice", "skill-b", False)
    clear_user_skill_override("alice", "skill-a")
    assert read_user_skill_overrides("alice") == {"skill-b": False}


def test_clear_is_noop_when_file_missing(patched_paths):
    clear_user_skill_override("alice", "skill-a")
    assert read_user_skill_overrides("alice") == {}


def test_clear_is_noop_when_skill_not_overridden(patched_paths):
    set_user_skill_override("alice", "skill-a", True)
    clear_user_skill_override("alice", "skill-other")
    assert read_user_skill_overrides("alice") == {"skill-a": True}


def test_get_user_skill_override_returns_none_when_absent(patched_paths):
    set_user_skill_override("alice", "skill-a", False)
    assert get_user_skill_override("alice", "skill-a") is False
    assert get_user_skill_override("alice", "skill-b") is None


def test_set_rejects_empty_skill_name(patched_paths):
    with pytest.raises(ValueError):
        set_user_skill_override("alice", "", True)


def test_two_users_have_independent_overrides(patched_paths):
    set_user_skill_override("alice", "shared-skill", False)
    set_user_skill_override("bob", "shared-skill", True)
    assert read_user_skill_overrides("alice") == {"shared-skill": False}
    assert read_user_skill_overrides("bob") == {"shared-skill": True}


# ---------------------------------------------------------------------------
# Corruption tolerance
# ---------------------------------------------------------------------------


def test_corrupt_file_returns_empty_overrides(base_dir: Path, patched_paths):
    file_path = base_dir.resolve() / "users" / "alice" / "skills_enabled.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("{not valid json", encoding="utf-8")
    assert read_user_skill_overrides("alice") == {}


def test_set_rewrites_corrupt_file(base_dir: Path, patched_paths):
    file_path = base_dir.resolve() / "users" / "alice" / "skills_enabled.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("{not valid", encoding="utf-8")

    set_user_skill_override("alice", "skill-a", True)
    assert read_user_skill_overrides("alice") == {"skill-a": True}


def test_payload_without_skills_key_tolerated(base_dir: Path, patched_paths):
    file_path = base_dir.resolve() / "users" / "alice" / "skills_enabled.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps({"version": 1}), encoding="utf-8")
    assert read_user_skill_overrides("alice") == {}


def test_shorthand_bool_form_accepted(base_dir: Path, patched_paths):
    """File may use ``{"skills": {"foo": true}}`` as a shorthand for ``{"enabled": true}``."""
    file_path = base_dir.resolve() / "users" / "alice" / "skills_enabled.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps({"version": 1, "skills": {"foo": True, "bar": False}}),
        encoding="utf-8",
    )
    assert read_user_skill_overrides("alice") == {"foo": True, "bar": False}


# ---------------------------------------------------------------------------
# Merge into load_skills
# ---------------------------------------------------------------------------


def test_load_skills_inherits_global_default_when_no_user_override(storage, skills_root: Path, patched_paths, empty_extensions_config):
    # Empty extensions config -> default for public is True
    _write_public_skill(skills_root, "shared-public")

    skills = storage.load_skills(user_id="alice")
    shared = next(s for s in skills if s.name == "shared-public")
    assert shared.enabled is True


def test_user_override_disables_a_skill_that_global_enables(storage, skills_root: Path, patched_paths, empty_extensions_config):
    _write_public_skill(skills_root, "shared-public")
    set_user_skill_override("alice", "shared-public", False)

    skills = storage.load_skills(user_id="alice")
    shared = next(s for s in skills if s.name == "shared-public")
    assert shared.enabled is False

    # Other users still see it enabled
    skills_bob = storage.load_skills(user_id="bob")
    shared_bob = next(s for s in skills_bob if s.name == "shared-public")
    assert shared_bob.enabled is True


def test_user_override_enables_a_skill_that_global_disables(storage, skills_root: Path, patched_paths):
    _write_public_skill(skills_root, "globally-disabled")

    forced_config = ExtensionsConfig(mcp_servers={}, skills={"globally-disabled": SkillStateConfig(enabled=False)})
    set_extensions_config(forced_config)
    try:
        with patch.object(ExtensionsConfig, "from_file", classmethod(lambda cls, config_path=None: forced_config)):
            # No override yet -> global default (False) wins
            skills = storage.load_skills(user_id="alice")
            disabled = next(s for s in skills if s.name == "globally-disabled")
            assert disabled.enabled is False

            # Alice explicitly opts in
            set_user_skill_override("alice", "globally-disabled", True)
            skills = storage.load_skills(user_id="alice")
            opted_in = next(s for s in skills if s.name == "globally-disabled")
            assert opted_in.enabled is True
    finally:
        reset_extensions_config()


def test_load_skills_without_user_id_ignores_overrides(storage, skills_root: Path, patched_paths, empty_extensions_config):
    _write_public_skill(storage.get_skills_root_path(), "shared-public")
    set_user_skill_override("alice", "shared-public", False)

    # user_id=None falls back to legacy global-only behaviour
    skills = storage.load_skills()
    shared = next(s for s in skills if s.name == "shared-public")
    assert shared.enabled is True


def test_enabled_only_filter_respects_user_override(storage, skills_root: Path, patched_paths, empty_extensions_config):
    _write_public_skill(skills_root, "kept")
    _write_public_skill(skills_root, "dropped")
    set_user_skill_override("alice", "dropped", False)

    enabled_names = {s.name for s in storage.load_skills(enabled_only=True, user_id="alice")}
    assert "kept" in enabled_names
    assert "dropped" not in enabled_names
