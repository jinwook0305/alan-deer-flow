"""Tests for per-user skill storage isolation in LocalSkillStorage.

Public skills always come from the globally configured skills root and are
shared across users. Custom skills are scoped to ``users/{user_id}/skills/custom``
when ``user_id`` is provided to the storage API, and fall back to the legacy
``<skills_root>/custom`` location when ``user_id`` is omitted.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from deerflow.config.paths import Paths
from deerflow.skills.storage import get_or_new_skill_storage

SKILL_FRONTMATTER_TEMPLATE = """---
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
    """Patch get_paths() so user-isolated paths resolve under ``base_dir``."""
    paths = Paths(base_dir)
    with patch("deerflow.config.paths.get_paths", return_value=paths):
        yield paths


def _make_public_skill(skills_root: Path, name: str) -> None:
    skill_dir = skills_root / "public" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(SKILL_FRONTMATTER_TEMPLATE.format(name=name), encoding="utf-8")


# ---------------------------------------------------------------------------
# Paths helpers
# ---------------------------------------------------------------------------


def test_user_skills_dir(base_dir: Path):
    paths = Paths(base_dir)
    assert paths.user_skills_dir("alice") == base_dir.resolve() / "users" / "alice" / "skills"


def test_user_custom_skills_dir(base_dir: Path):
    paths = Paths(base_dir)
    assert paths.user_custom_skills_dir("alice") == base_dir.resolve() / "users" / "alice" / "skills" / "custom"


def test_user_custom_skills_dir_rejects_unsafe_user_id(base_dir: Path):
    paths = Paths(base_dir)
    with pytest.raises(ValueError, match="Invalid user_id"):
        paths.user_custom_skills_dir("../escape")


# ---------------------------------------------------------------------------
# Path resolution: user_id is None (legacy) vs set
# ---------------------------------------------------------------------------


def test_custom_skill_dir_falls_back_to_legacy_root_when_no_user_id(storage, skills_root: Path):
    assert storage.get_custom_skill_dir("demo-skill") == skills_root / "custom" / "demo-skill"


def test_custom_skill_dir_resolves_under_user_when_user_id_given(storage, base_dir: Path, patched_paths):
    expected = base_dir.resolve() / "users" / "alice" / "skills" / "custom" / "demo-skill"
    assert storage.get_custom_skill_dir("demo-skill", user_id="alice") == expected


def test_custom_skill_file_uses_user_scope(storage, base_dir: Path, patched_paths):
    expected = base_dir.resolve() / "users" / "alice" / "skills" / "custom" / "demo-skill" / "SKILL.md"
    assert storage.get_custom_skill_file("demo-skill", user_id="alice") == expected


def test_skill_history_file_uses_user_scope(storage, base_dir: Path, patched_paths):
    expected = base_dir.resolve() / "users" / "alice" / "skills" / "custom" / ".history" / "demo-skill.jsonl"
    assert storage.get_skill_history_file("demo-skill", user_id="alice") == expected


# ---------------------------------------------------------------------------
# Read / write per-user isolation
# ---------------------------------------------------------------------------


def test_write_lands_in_user_scoped_dir(storage, base_dir: Path, patched_paths):
    storage.write_custom_skill("demo-skill", "SKILL.md", "# alice", user_id="alice")
    expected = base_dir.resolve() / "users" / "alice" / "skills" / "custom" / "demo-skill" / "SKILL.md"
    assert expected.read_text() == "# alice"


def test_two_users_do_not_share_custom_skills(storage, base_dir: Path, patched_paths):
    storage.write_custom_skill("demo-skill", "SKILL.md", "# alice", user_id="alice")
    storage.write_custom_skill("demo-skill", "SKILL.md", "# bob", user_id="bob")

    assert storage.read_custom_skill("demo-skill", user_id="alice") == "# alice"
    assert storage.read_custom_skill("demo-skill", user_id="bob") == "# bob"


def test_legacy_write_does_not_leak_into_user_scope(storage, skills_root: Path, base_dir: Path, patched_paths):
    storage.write_custom_skill("demo-skill", "SKILL.md", "# legacy")

    assert (skills_root / "custom" / "demo-skill" / "SKILL.md").read_text() == "# legacy"
    assert not (base_dir / "users" / "alice" / "skills" / "custom" / "demo-skill" / "SKILL.md").exists()
    assert not storage.custom_skill_exists("demo-skill", user_id="alice")


def test_user_skill_does_not_leak_into_legacy_scope(storage, skills_root: Path, base_dir: Path, patched_paths):
    storage.write_custom_skill("demo-skill", "SKILL.md", "# alice", user_id="alice")

    assert not (skills_root / "custom" / "demo-skill" / "SKILL.md").exists()
    assert not storage.custom_skill_exists("demo-skill")


# ---------------------------------------------------------------------------
# History per user
# ---------------------------------------------------------------------------


def test_history_per_user(storage, base_dir: Path, patched_paths):
    storage.write_custom_skill("demo-skill", "SKILL.md", "# alice", user_id="alice")
    storage.append_history("demo-skill", {"action": "create", "author": "alice"}, user_id="alice")

    alice_history = storage.read_history("demo-skill", user_id="alice")
    assert len(alice_history) == 1
    assert alice_history[0]["author"] == "alice"

    assert storage.read_history("demo-skill", user_id="bob") == []
    assert storage.read_history("demo-skill") == []


# ---------------------------------------------------------------------------
# load_skills picks up public globally + custom per-user
# ---------------------------------------------------------------------------


def test_load_skills_returns_public_regardless_of_user(storage, skills_root: Path, patched_paths):
    _make_public_skill(skills_root, "shared-public")

    for uid in (None, "alice", "bob"):
        skills = storage.load_skills(user_id=uid)
        names = {s.name for s in skills}
        assert "shared-public" in names, f"public skill missing for user_id={uid!r}"


def test_load_skills_isolates_custom_per_user(storage, base_dir: Path, patched_paths):
    storage.write_custom_skill("alice-skill", "SKILL.md", SKILL_FRONTMATTER_TEMPLATE.format(name="alice-skill"), user_id="alice")
    storage.write_custom_skill("bob-skill", "SKILL.md", SKILL_FRONTMATTER_TEMPLATE.format(name="bob-skill"), user_id="bob")

    alice_skills = {s.name for s in storage.load_skills(user_id="alice")}
    bob_skills = {s.name for s in storage.load_skills(user_id="bob")}
    legacy_skills = {s.name for s in storage.load_skills()}

    assert "alice-skill" in alice_skills
    assert "bob-skill" not in alice_skills
    assert "bob-skill" in bob_skills
    assert "alice-skill" not in bob_skills
    # The legacy (no user_id) scope sees neither user's custom skill.
    assert "alice-skill" not in legacy_skills
    assert "bob-skill" not in legacy_skills


# ---------------------------------------------------------------------------
# Delete per user
# ---------------------------------------------------------------------------


def test_delete_only_removes_target_user_skill(storage, base_dir: Path, patched_paths):
    storage.write_custom_skill("demo-skill", "SKILL.md", "# alice", user_id="alice")
    storage.write_custom_skill("demo-skill", "SKILL.md", "# bob", user_id="bob")

    storage.delete_custom_skill("demo-skill", user_id="alice")

    assert not storage.custom_skill_exists("demo-skill", user_id="alice")
    assert storage.custom_skill_exists("demo-skill", user_id="bob")


# ---------------------------------------------------------------------------
# ensure_safe_support_path threads user_id through
# ---------------------------------------------------------------------------


def test_ensure_safe_support_path_uses_user_scope(storage, base_dir: Path, patched_paths):
    # Pre-create the user-scoped skill dir so resolve() reflects the per-user root.
    storage.write_custom_skill("demo-skill", "SKILL.md", "# alice", user_id="alice")

    resolved = storage.ensure_safe_support_path("demo-skill", "scripts/run.py", user_id="alice")
    expected = base_dir.resolve() / "users" / "alice" / "skills" / "custom" / "demo-skill" / "scripts" / "run.py"
    assert resolved == expected
