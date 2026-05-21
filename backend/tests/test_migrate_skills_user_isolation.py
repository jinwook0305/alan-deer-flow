"""Tests for ``scripts/migrate_skills_user_isolation.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from deerflow.config.paths import Paths

# Import the migration module by path so tests don't depend on ``sys.path``
# already containing ``scripts/`` (matches how ``migrate_user_isolation``
# is imported in other regression tests).
_REPO_BACKEND = Path(__file__).resolve().parents[1]
_MIGRATE_PATH = _REPO_BACKEND / "scripts" / "migrate_skills_user_isolation.py"

spec = importlib.util.spec_from_file_location("migrate_skills_user_isolation", _MIGRATE_PATH)
assert spec is not None and spec.loader is not None
migrate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrate_module)


SKILL_BODY = """---
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
def paths(base_dir: Path) -> Paths:
    return Paths(base_dir)


def _make_legacy_skill(skills_root: Path, name: str, body: str | None = None) -> Path:
    skill_dir = skills_root / "custom" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body or SKILL_BODY.format(name=name), encoding="utf-8")
    return skill_dir


def _make_legacy_history(skills_root: Path, name: str, body: str = "{}\n") -> Path:
    history_dir = skills_root / "custom" / ".history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / f"{name}.jsonl"
    history_file.write_text(body, encoding="utf-8")
    return history_file


# ---------------------------------------------------------------------------
# migrate_custom_skills
# ---------------------------------------------------------------------------


def test_migrate_moves_legacy_custom_skill(paths: Paths, skills_root: Path):
    _make_legacy_skill(skills_root, "demo-skill")

    report = migrate_module.migrate_custom_skills(paths, skills_root, user_id="default")

    assert len(report) == 1
    assert report[0]["skill"] == "demo-skill"
    assert "moved" in report[0]["action"]

    dest = paths.user_custom_skills_dir("default") / "demo-skill" / "SKILL.md"
    assert dest.exists()
    assert "demo-skill" in dest.read_text()
    assert not (skills_root / "custom" / "demo-skill").exists()


def test_migrate_dry_run_makes_no_changes(paths: Paths, skills_root: Path):
    _make_legacy_skill(skills_root, "demo-skill")

    report = migrate_module.migrate_custom_skills(paths, skills_root, user_id="default", dry_run=True)

    assert len(report) == 1
    assert (skills_root / "custom" / "demo-skill" / "SKILL.md").exists()
    assert not paths.user_custom_skills_dir("default").exists()


def test_migrate_to_custom_user_id(paths: Paths, skills_root: Path):
    _make_legacy_skill(skills_root, "alice-skill")

    migrate_module.migrate_custom_skills(paths, skills_root, user_id="alice")

    assert (paths.user_custom_skills_dir("alice") / "alice-skill" / "SKILL.md").exists()
    assert not (paths.user_custom_skills_dir("default") / "alice-skill").exists()


def test_migrate_conflict_moves_legacy_to_conflicts_dir(paths: Paths, skills_root: Path):
    _make_legacy_skill(skills_root, "shared-name", body=SKILL_BODY.format(name="shared-name") + "\n# legacy variant\n")
    # Pre-populate the destination so the migration encounters a conflict.
    dest_root = paths.user_custom_skills_dir("default") / "shared-name"
    dest_root.mkdir(parents=True)
    (dest_root / "SKILL.md").write_text(SKILL_BODY.format(name="shared-name") + "\n# existing\n", encoding="utf-8")

    report = migrate_module.migrate_custom_skills(paths, skills_root, user_id="default")

    assert len(report) == 1
    assert "conflict" in report[0]["action"]

    conflicts_dir = paths.base_dir / "migration-conflicts" / "skills" / "shared-name"
    assert (conflicts_dir / "SKILL.md").read_text().count("legacy variant") == 1
    # Pre-existing destination remains intact.
    assert (dest_root / "SKILL.md").read_text().count("existing") == 1


def test_migrate_is_idempotent(paths: Paths, skills_root: Path):
    _make_legacy_skill(skills_root, "demo-skill")

    first = migrate_module.migrate_custom_skills(paths, skills_root, user_id="default")
    second = migrate_module.migrate_custom_skills(paths, skills_root, user_id="default")

    assert len(first) == 1
    assert len(second) == 0  # nothing left to migrate


def test_migrate_ignores_public_skills(paths: Paths, skills_root: Path):
    public_skill = skills_root / "public" / "deep-research"
    public_skill.mkdir(parents=True)
    (public_skill / "SKILL.md").write_text(SKILL_BODY.format(name="deep-research"), encoding="utf-8")

    migrate_module.migrate_custom_skills(paths, skills_root, user_id="default")

    assert (public_skill / "SKILL.md").exists()
    assert not paths.user_custom_skills_dir("default").exists()


def test_migrate_skips_history_subdir(paths: Paths, skills_root: Path):
    """``.history`` is handled by :func:`migrate_skill_history`, not the main loop."""
    _make_legacy_skill(skills_root, "demo-skill")
    _make_legacy_history(skills_root, "demo-skill")

    report = migrate_module.migrate_custom_skills(paths, skills_root, user_id="default")
    skill_names = [entry["skill"] for entry in report]
    assert ".history" not in skill_names


# ---------------------------------------------------------------------------
# migrate_skill_history
# ---------------------------------------------------------------------------


def test_migrate_history_moves_jsonl(paths: Paths, skills_root: Path):
    _make_legacy_history(skills_root, "demo-skill", body='{"action":"create"}\n')

    report = migrate_module.migrate_skill_history(paths, skills_root, user_id="default")

    assert len(report) == 1
    dest = paths.user_custom_skills_dir("default") / ".history" / "demo-skill.jsonl"
    assert dest.exists()
    assert "create" in dest.read_text()
    assert not (skills_root / "custom" / ".history" / "demo-skill.jsonl").exists()


def test_migrate_history_conflict_keeps_destination(paths: Paths, skills_root: Path):
    _make_legacy_history(skills_root, "demo-skill", body='{"action":"legacy"}\n')
    dest = paths.user_custom_skills_dir("default") / ".history" / "demo-skill.jsonl"
    dest.parent.mkdir(parents=True)
    dest.write_text('{"action":"existing"}\n', encoding="utf-8")

    report = migrate_module.migrate_skill_history(paths, skills_root, user_id="default")

    assert len(report) == 1
    assert "conflict" in report[0]["action"]
    assert dest.read_text() == '{"action":"existing"}\n'
    conflicts = paths.base_dir / "migration-conflicts" / "skills" / ".history" / "demo-skill.jsonl"
    assert conflicts.read_text() == '{"action":"legacy"}\n'


# ---------------------------------------------------------------------------
# cleanup_empty_legacy_dirs
# ---------------------------------------------------------------------------


def test_cleanup_removes_empty_legacy_custom(skills_root: Path):
    # Empty ``custom/`` (no children at all)
    legacy_custom = skills_root / "custom"
    assert legacy_custom.exists()
    migrate_module.cleanup_empty_legacy_dirs(skills_root)
    assert not legacy_custom.exists()


def test_cleanup_leaves_non_empty_legacy_custom(skills_root: Path):
    leftover = skills_root / "custom" / "leftover"
    leftover.mkdir()
    migrate_module.cleanup_empty_legacy_dirs(skills_root)
    assert (skills_root / "custom").exists()


def test_cleanup_removes_empty_history_dir_then_custom(skills_root: Path):
    history_dir = skills_root / "custom" / ".history"
    history_dir.mkdir(parents=True)
    # ``custom/`` only contains the empty ``.history/`` — both should be removed.
    migrate_module.cleanup_empty_legacy_dirs(skills_root)
    assert not history_dir.exists()
    assert not (skills_root / "custom").exists()


# ---------------------------------------------------------------------------
# End-to-end via main()
# ---------------------------------------------------------------------------


def test_main_end_to_end(monkeypatch, paths: Paths, skills_root: Path):
    _make_legacy_skill(skills_root, "demo-skill")
    _make_legacy_history(skills_root, "demo-skill")

    config = SimpleNamespace(skills=SimpleNamespace(get_skills_path=lambda: skills_root))

    with (
        patch.object(migrate_module, "get_paths", return_value=paths),
        patch.object(migrate_module, "get_app_config", return_value=config),
    ):
        monkeypatch.setattr("sys.argv", ["migrate_skills_user_isolation", "--user-id", "alice"])
        migrate_module.main()

    assert (paths.user_custom_skills_dir("alice") / "demo-skill" / "SKILL.md").exists()
    assert (paths.user_custom_skills_dir("alice") / ".history" / "demo-skill.jsonl").exists()
    assert not (skills_root / "custom").exists()  # cleanup removed the now-empty dir
