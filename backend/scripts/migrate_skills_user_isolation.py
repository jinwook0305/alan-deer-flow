"""One-time migration: move legacy custom skills into per-user layout.

Before this migration, custom skills lived at::

    <skills_root>/custom/<skill_name>/SKILL.md
    <skills_root>/custom/.history/<skill_name>.jsonl

After the migration they are scoped per-user::

    {base_dir}/users/<user_id>/skills/custom/<skill_name>/SKILL.md
    {base_dir}/users/<user_id>/skills/custom/.history/<skill_name>.jsonl

Public skills are *not* touched — they remain admin-managed at the global
``<skills_root>/public/`` location.

Skill enable state (``extensions_config.json`` ``skills.<name>.enabled``) is
intentionally left in place; the global config keeps acting as the default and
per-user overrides only appear when a user explicitly toggles a skill via the
gateway.

Usage::

    PYTHONPATH=. python scripts/migrate_skills_user_isolation.py [--dry-run] [--user-id USER_ID]

The script is idempotent — re-running it after a successful migration is a
no-op, since the legacy ``custom/`` directory is removed only when empty.
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

from deerflow.config import get_app_config
from deerflow.config.paths import Paths, get_paths

logger = logging.getLogger(__name__)

_HISTORY_DIR_NAME = ".history"


def _skills_root() -> Path:
    """Return the configured skills root directory (host path)."""
    config = get_app_config()
    return config.skills.get_skills_path()


def migrate_custom_skills(
    paths: Paths,
    skills_root: Path,
    user_id: str = "default",
    *,
    dry_run: bool = False,
) -> list[dict]:
    """Move legacy custom skill directories into the per-user layout.

    Args:
        paths: Paths instance providing the target ``users/<user_id>/skills/custom/`` dir.
        skills_root: Source skills root that hosts the legacy ``custom/`` subtree.
        user_id: Target user to claim un-owned legacy custom skills (defaults to
            ``"default"``).  In multi-user installs, set this to the operator
            account that should inherit the legacy artifacts.
        dry_run: If True, only log what would happen — no filesystem writes.

    Returns:
        Report rows (one per legacy skill directory).
    """
    report: list[dict] = []
    legacy_custom = skills_root / "custom"
    if not legacy_custom.exists():
        logger.info("No legacy custom skills directory found at %s — nothing to migrate.", legacy_custom)
        return report

    target_root = paths.user_custom_skills_dir(user_id)

    for entry_path in sorted(legacy_custom.iterdir()):
        # ``.history/`` is handled separately so we can merge per-skill JSONL
        # files into the destination location.
        if entry_path.name == _HISTORY_DIR_NAME:
            continue
        if not entry_path.is_dir():
            continue
        skill_name = entry_path.name
        dest = target_root / skill_name
        entry = {"skill": skill_name, "user_id": user_id, "action": ""}

        if dest.exists():
            conflicts_dir = paths.base_dir / "migration-conflicts" / "skills" / skill_name
            entry["action"] = f"conflict -> {conflicts_dir}"
            if not dry_run:
                conflicts_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry_path), str(conflicts_dir))
            logger.warning("Conflict for skill %s: moved legacy copy to %s", skill_name, conflicts_dir)
        else:
            entry["action"] = f"moved -> {dest}"
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry_path), str(dest))
            logger.info("Migrated custom skill %s -> user %s", skill_name, user_id)

        report.append(entry)

    return report


def migrate_skill_history(
    paths: Paths,
    skills_root: Path,
    user_id: str = "default",
    *,
    dry_run: bool = False,
) -> list[dict]:
    """Move legacy ``custom/.history/<name>.jsonl`` files into the per-user layout.

    Each ``.jsonl`` is moved individually so that:

    * A skill whose body was already migrated previously can still get its
      history attached on a follow-up run.
    * A user who has already started accruing history (collision on the
      destination filename) is preserved — the legacy file is sidelined to
      ``migration-conflicts/skills/.history/<name>.jsonl``.
    """
    report: list[dict] = []
    legacy_history = skills_root / "custom" / _HISTORY_DIR_NAME
    if not legacy_history.exists():
        return report

    target_history_root = paths.user_custom_skills_dir(user_id) / _HISTORY_DIR_NAME

    for history_file in sorted(legacy_history.iterdir()):
        if not history_file.is_file() or not history_file.name.endswith(".jsonl"):
            continue
        dest = target_history_root / history_file.name
        entry = {"history": history_file.name, "user_id": user_id, "action": ""}

        if dest.exists():
            conflicts_path = paths.base_dir / "migration-conflicts" / "skills" / _HISTORY_DIR_NAME / history_file.name
            entry["action"] = f"conflict -> {conflicts_path}"
            if not dry_run:
                conflicts_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(history_file), str(conflicts_path))
            logger.warning("Conflict for skill history %s: moved legacy copy to %s", history_file.name, conflicts_path)
        else:
            entry["action"] = f"moved -> {dest}"
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(history_file), str(dest))
            logger.info("Migrated history %s -> user %s", history_file.name, user_id)

        report.append(entry)

    return report


def cleanup_empty_legacy_dirs(skills_root: Path, *, dry_run: bool = False) -> None:
    """Remove the legacy ``custom/`` (and its ``.history/``) once they are empty.

    Leaves the directories in place if anything remains so the operator can
    re-inspect leftover content.
    """
    if dry_run:
        return
    legacy_history = skills_root / "custom" / _HISTORY_DIR_NAME
    if legacy_history.exists() and not any(legacy_history.iterdir()):
        legacy_history.rmdir()
    legacy_custom = skills_root / "custom"
    if legacy_custom.exists() and not any(legacy_custom.iterdir()):
        legacy_custom.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate DeerFlow custom skills to per-user layout")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without making changes")
    parser.add_argument(
        "--user-id",
        default="default",
        metavar="USER_ID",
        help=("User ID to claim legacy custom skills. Defaults to 'default' (matching DEFAULT_USER_ID for no-auth setups). In multi-user installs, set this to the operator account that should inherit the legacy custom skills."),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    paths = get_paths()
    skills_root = _skills_root()
    logger.info("Base directory: %s", paths.base_dir)
    logger.info("Skills root: %s", skills_root)
    logger.info("Dry run: %s", args.dry_run)
    logger.info("Claiming legacy custom skills for user_id=%s", args.user_id)

    skills_report = migrate_custom_skills(paths, skills_root, user_id=args.user_id, dry_run=args.dry_run)
    history_report = migrate_skill_history(paths, skills_root, user_id=args.user_id, dry_run=args.dry_run)
    cleanup_empty_legacy_dirs(skills_root, dry_run=args.dry_run)

    if skills_report:
        logger.info("Custom skill migration report:")
        for entry in skills_report:
            logger.info("  skill=%s user=%s action=%s", entry["skill"], entry["user_id"], entry["action"])
    else:
        logger.info("No custom skills to migrate.")

    if history_report:
        logger.info("Skill history migration report:")
        for entry in history_report:
            logger.info("  history=%s user=%s action=%s", entry["history"], entry["user_id"], entry["action"])

    if skills_report:
        logger.warning(
            "%d legacy custom skill(s) were assigned to '%s'. If those skills belonged to other users, move them manually under {base_dir}/users/<user_id>/skills/custom/.",
            len(skills_report),
            args.user_id,
        )


if __name__ == "__main__":
    main()
