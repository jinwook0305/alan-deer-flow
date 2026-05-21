"""Per-user skill enable-state overrides.

A user's skill enable state is stored at
``{base_dir}/users/{user_id}/skills_enabled.json``.  Each skill listed in the
file carries an explicit ``enabled`` boolean.  Skills *not* listed inherit the
global default from ``extensions_config.json``.

The global ``extensions_config.json`` is therefore treated as the
admin-managed default; this module layers per-user opt-in / opt-out overrides
on top of it without mutating the shared file.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)

CURRENT_VERSION = 1


def _enabled_file(user_id: str) -> Path:
    return get_paths().user_skills_enabled_file(user_id)


def _empty_payload() -> dict[str, Any]:
    return {"version": CURRENT_VERSION, "skills": {}}


def _parse_payload(raw: Any) -> dict[str, bool]:
    """Extract a clean ``{skill_name: enabled}`` mapping from a loaded JSON payload.

    Unknown fields are ignored; malformed entries are skipped with a warning so
    a partially corrupted file does not break skill loading entirely.
    """
    if not isinstance(raw, dict):
        logger.warning("skills_enabled payload is not a JSON object; ignoring")
        return {}

    skills = raw.get("skills")
    if not isinstance(skills, dict):
        return {}

    overrides: dict[str, bool] = {}
    for skill_name, state in skills.items():
        if not isinstance(skill_name, str) or not skill_name:
            continue
        if isinstance(state, bool):
            # Tolerate the shorthand form: ``{"foo": true}``.
            overrides[skill_name] = state
            continue
        if isinstance(state, dict):
            enabled = state.get("enabled")
            if isinstance(enabled, bool):
                overrides[skill_name] = enabled
                continue
        logger.warning("skills_enabled entry for %r has unsupported shape; skipping", skill_name)
    return overrides


def read_user_skill_overrides(user_id: str) -> dict[str, bool]:
    """Return the user's explicit overrides as ``{skill_name: enabled}``.

    Returns an empty dict when the file does not exist or is unreadable; a
    corrupt file is logged and treated as "no overrides" so that one bad write
    cannot strand a user with no skills.
    """
    path = _enabled_file(user_id)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read skills_enabled for user %r: %s", user_id, exc)
        return {}
    return _parse_payload(raw)


def get_user_skill_override(user_id: str, skill_name: str) -> bool | None:
    """Return the user's explicit override for *skill_name*, or ``None`` to inherit."""
    return read_user_skill_overrides(user_id).get(skill_name)


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
    ) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def set_user_skill_override(user_id: str, skill_name: str, enabled: bool) -> None:
    """Persist an explicit ``enabled`` decision for *skill_name* for *user_id*."""
    if not skill_name:
        raise ValueError("skill_name must be a non-empty string")
    path = _enabled_file(user_id)
    payload: dict[str, Any]
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = _empty_payload()
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Resetting corrupt skills_enabled for user %r: %s", user_id, exc)
            payload = _empty_payload()
    else:
        payload = _empty_payload()

    payload.setdefault("version", CURRENT_VERSION)
    skills = payload.setdefault("skills", {})
    if not isinstance(skills, dict):
        skills = {}
        payload["skills"] = skills
    skills[skill_name] = {"enabled": bool(enabled)}
    _atomic_write(path, payload)


def clear_user_skill_override(user_id: str, skill_name: str) -> None:
    """Remove the user's explicit override for *skill_name* so it inherits the global default.

    No-op if the file is missing or no override exists for the given skill.
    """
    path = _enabled_file(user_id)
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read skills_enabled while clearing override for user %r: %s", user_id, exc)
        return
    if not isinstance(payload, dict):
        return
    skills = payload.get("skills")
    if not isinstance(skills, dict) or skill_name not in skills:
        return
    skills.pop(skill_name, None)
    _atomic_write(path, payload)


__all__ = [
    "CURRENT_VERSION",
    "clear_user_skill_override",
    "get_user_skill_override",
    "read_user_skill_overrides",
    "set_user_skill_override",
]
