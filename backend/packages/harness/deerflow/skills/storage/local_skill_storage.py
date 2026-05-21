"""Local-filesystem implementation of ``SkillStorage``."""

from __future__ import annotations

import errno
import json
import logging
import os
import shutil
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from deerflow.config.runtime_paths import resolve_path
from deerflow.skills.storage.skill_storage import SKILL_MD_FILE, SkillStorage
from deerflow.skills.types import SkillCategory

logger = logging.getLogger(__name__)

DEFAULT_SKILLS_CONTAINER_PATH = "/mnt/skills"


class LocalSkillStorage(SkillStorage):
    """Skill storage backed by the local filesystem.

    Layout::

        <root>/public/<name>/SKILL.md
        <root>/custom/<name>/SKILL.md
        <root>/custom/.history/<name>.jsonl
    """

    def __init__(
        self,
        host_path: str | None = None,
        container_path: str = DEFAULT_SKILLS_CONTAINER_PATH,
        app_config=None,
    ) -> None:
        super().__init__(container_path=container_path)
        if host_path is None:
            from deerflow.config import get_app_config

            config = app_config or get_app_config()
            self._host_root: Path = config.skills.get_skills_path()
        else:
            self._host_root = resolve_path(host_path)

    # ------------------------------------------------------------------
    # Abstract operation implementations
    # ------------------------------------------------------------------

    def get_skills_root_path(self) -> Path:
        return self._host_root

    def custom_skill_exists(self, name: str, *, user_id: str | None = None) -> bool:
        return self.get_custom_skill_file(name, user_id=user_id).exists()

    def public_skill_exists(self, name: str) -> bool:
        normalized_name = self.validate_skill_name(name)
        return (self._host_root / SkillCategory.PUBLIC.value / normalized_name / SKILL_MD_FILE).exists()

    def _iter_skill_files(self, *, user_id: str | None = None) -> Iterable[tuple[SkillCategory, Path, Path]]:
        # Public skills always come from the globally configured skills root.
        public_root = self._host_root / SkillCategory.PUBLIC.value
        if self._host_root.exists() and public_root.exists() and public_root.is_dir():
            yield from self._walk_category_dir(SkillCategory.PUBLIC, public_root)

        # Custom skills come from the per-user location when user_id is given,
        # otherwise from the legacy global location.
        custom_root = self.get_custom_skills_root(user_id=user_id)
        if custom_root.exists() and custom_root.is_dir():
            yield from self._walk_category_dir(SkillCategory.CUSTOM, custom_root)

    @staticmethod
    def _walk_category_dir(category: SkillCategory, category_path: Path) -> Iterable[tuple[SkillCategory, Path, Path]]:
        for current_root, dir_names, file_names in os.walk(category_path, followlinks=True):
            dir_names[:] = sorted(name for name in dir_names if not name.startswith("."))
            if SKILL_MD_FILE not in file_names:
                continue
            yield category, category_path, Path(current_root) / SKILL_MD_FILE

    def read_custom_skill(self, name: str, *, user_id: str | None = None) -> str:
        if not self.custom_skill_exists(name, user_id=user_id):
            raise FileNotFoundError(f"Custom skill '{name}' not found.")
        return (self.get_custom_skill_dir(name, user_id=user_id) / SKILL_MD_FILE).read_text(encoding="utf-8")

    def write_custom_skill(self, name: str, relative_path: str, content: str, *, user_id: str | None = None) -> None:
        target = self.validate_relative_path(relative_path, self.get_custom_skill_dir(name, user_id=user_id))
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(target.parent),
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        tmp_path.replace(target)

    async def ainstall_skill_from_archive(self, archive_path: str | Path, *, user_id: str | None = None) -> dict:
        import zipfile

        from deerflow.skills.installer import (
            SkillAlreadyExistsError,
            _move_staged_skill_into_reserved_target,
            _scan_skill_archive_contents_or_raise,
            resolve_skill_dir_from_archive,
            safe_extract_skill_archive,
        )
        from deerflow.skills.validation import _validate_skill_frontmatter

        logger.info("Installing skill from %s", archive_path)
        path = Path(archive_path)
        if not path.is_file():
            if not path.exists():
                raise FileNotFoundError(f"Skill file not found: {archive_path}")
            raise ValueError(f"Path is not a file: {archive_path}")
        if path.suffix != ".skill":
            raise ValueError("File must have .skill extension")

        custom_dir = self.get_custom_skills_root(user_id=user_id)
        custom_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            try:
                zf = zipfile.ZipFile(path, "r")
            except FileNotFoundError:
                raise FileNotFoundError(f"Skill file not found: {archive_path}") from None
            except (zipfile.BadZipFile, IsADirectoryError):
                raise ValueError("File is not a valid ZIP archive") from None

            with zf:
                safe_extract_skill_archive(zf, tmp_path)

            skill_dir = resolve_skill_dir_from_archive(tmp_path)

            is_valid, message, skill_name = _validate_skill_frontmatter(skill_dir)
            if not is_valid:
                raise ValueError(f"Invalid skill: {message}")
            if not skill_name or "/" in skill_name or "\\" in skill_name or ".." in skill_name:
                raise ValueError(f"Invalid skill name: {skill_name}")

            target = custom_dir / skill_name
            if target.exists():
                raise SkillAlreadyExistsError(f"Skill '{skill_name}' already exists")

            await _scan_skill_archive_contents_or_raise(skill_dir, skill_name)

            with tempfile.TemporaryDirectory(prefix=f".installing-{skill_name}-", dir=custom_dir) as staging_root:
                staging_target = Path(staging_root) / skill_name
                shutil.copytree(skill_dir, staging_target)
                _move_staged_skill_into_reserved_target(staging_target, target)
            logger.info("Skill %r installed to %s", skill_name, target)

        return {
            "success": True,
            "skill_name": skill_name,
            "message": f"Skill '{skill_name}' installed successfully",
        }

    def delete_custom_skill(self, name: str, *, history_meta: dict | None = None, user_id: str | None = None) -> None:
        self.validate_skill_name(name)
        self.ensure_custom_skill_is_editable(name, user_id=user_id)
        target = self.get_custom_skill_dir(name, user_id=user_id)
        if history_meta is not None:
            prev_content = self.read_custom_skill(name, user_id=user_id)
            try:
                self.append_history(name, {**history_meta, "prev_content": prev_content}, user_id=user_id)
            except OSError as e:
                if not isinstance(e, PermissionError) and e.errno not in {errno.EACCES, errno.EPERM, errno.EROFS}:
                    raise
                logger.warning(
                    "Skipping delete history write for custom skill %s due to readonly/permission failure; continuing with skill directory removal: %s",
                    name,
                    e,
                )
        if target.exists():
            shutil.rmtree(target)

    def append_history(self, name: str, record: dict, *, user_id: str | None = None) -> None:
        self.validate_skill_name(name)
        payload = {"ts": datetime.now(UTC).isoformat(), **record}
        history_path = self.get_skill_history_file(name, user_id=user_id)
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")

    def read_history(self, name: str, *, user_id: str | None = None) -> list[dict]:
        self.validate_skill_name(name)
        history_path = self.get_skill_history_file(name, user_id=user_id)
        if not history_path.exists():
            return []
        records: list[dict] = []
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(json.loads(line))
        return records
