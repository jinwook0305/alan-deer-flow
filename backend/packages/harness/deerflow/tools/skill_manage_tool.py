"""Tool for creating and evolving custom skills."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from weakref import WeakValueDictionary

from langchain.tools import tool

from deerflow.agents.lead_agent.prompt import refresh_skills_system_prompt_cache_async
from deerflow.skills.security_scanner import scan_skill_content
from deerflow.skills.storage import get_or_new_skill_storage
from deerflow.skills.storage.skill_storage import SkillStorage
from deerflow.skills.types import SKILL_MD_FILE
from deerflow.tools.sync import make_sync_tool_wrapper
from deerflow.tools.types import Runtime

logger = logging.getLogger(__name__)

# Locks are scoped to ``(user_id, skill_name)`` so two users can independently
# manage skills sharing the same name without serialising against each other.
# ``user_id`` is ``None`` for legacy / no-auth installations.
_skill_locks: WeakValueDictionary[tuple[str | None, str], asyncio.Lock] = WeakValueDictionary()


def _get_lock(user_id: str | None, name: str) -> asyncio.Lock:
    key = (user_id, name)
    lock = _skill_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _skill_locks[key] = lock
    return lock


def _get_thread_id(runtime: Runtime | None) -> str | None:
    if runtime is None:
        return None
    if runtime.context and runtime.context.get("thread_id"):
        return runtime.context.get("thread_id")
    return runtime.config.get("configurable", {}).get("thread_id")


def _resolve_skill_user_id(runtime: Runtime | None) -> str | None:
    """Return the effective user_id for skill storage scoping, or ``None`` for legacy.

    Resolution order:

    1. ``runtime.context["user_id"]`` — set explicitly by the gateway when an
       authenticated request enters tool execution. Survives task / thread-pool
       boundaries that may drop the auth ContextVar.
    2. The ``_current_user`` ContextVar via :func:`get_current_user` — set by
       the auth middleware at request entry.
    3. ``None`` — no auth context detected, so the storage layer should fall
       back to the legacy global ``<skills_root>/custom/`` location.

    Mirrors the semantics used in :func:`deerflow.agents.lead_agent.agent._make_lead_agent`
    so the system prompt and the ``skill_manage`` tool agree on which custom
    skill directory is being read/written.
    """
    if runtime is not None:
        context = getattr(runtime, "context", None)
        if isinstance(context, dict):
            ctx_user_id = context.get("user_id")
            if ctx_user_id:
                return str(ctx_user_id)

    from deerflow.runtime.user_context import get_current_user

    user = get_current_user()
    return str(user.id) if user is not None else None


def _history_record(*, action: str, file_path: str, prev_content: str | None, new_content: str | None, thread_id: str | None, scanner: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "author": "agent",
        "thread_id": thread_id,
        "file_path": file_path,
        "prev_content": prev_content,
        "new_content": new_content,
        "scanner": scanner,
    }


async def _scan_or_raise(content: str, *, executable: bool, location: str) -> dict[str, str]:
    result = await scan_skill_content(content, executable=executable, location=location)
    if result.decision == "block":
        raise ValueError(f"Security scan blocked the write: {result.reason}")
    if executable and result.decision != "allow":
        raise ValueError(f"Security scan rejected executable content: {result.reason}")
    return {"decision": result.decision, "reason": result.reason}


async def _to_thread(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


async def _skill_manage_impl(
    runtime: Runtime,
    action: str,
    name: str,
    content: str | None = None,
    path: str | None = None,
    find: str | None = None,
    replace: str | None = None,
    expected_count: int | None = None,
) -> str:
    """Manage custom skills under skills/custom/.

    Args:
        action: One of create, patch, edit, delete, write_file, remove_file.
        name: Skill name in hyphen-case.
        content: New file content for create, edit, or write_file.
        path: Supporting file path for write_file or remove_file.
        find: Existing text to replace for patch.
        replace: Replacement text for patch.
        expected_count: Optional expected number of replacements for patch.
    """
    name = SkillStorage.validate_skill_name(name)
    user_id = _resolve_skill_user_id(runtime)
    lock = _get_lock(user_id, name)
    thread_id = _get_thread_id(runtime)
    skill_storage = get_or_new_skill_storage()

    async with lock:
        if action == "create":
            if await _to_thread(skill_storage.custom_skill_exists, name, user_id=user_id):
                raise ValueError(f"Custom skill '{name}' already exists.")
            if content is None:
                raise ValueError("content is required for create.")
            await _to_thread(skill_storage.validate_skill_markdown_content, name, content)
            scan = await _scan_or_raise(content, executable=False, location=f"{name}/{SKILL_MD_FILE}")
            await _to_thread(skill_storage.write_custom_skill, name, SKILL_MD_FILE, content, user_id=user_id)
            await _to_thread(
                skill_storage.append_history,
                name,
                _history_record(action="create", file_path=SKILL_MD_FILE, prev_content=None, new_content=content, thread_id=thread_id, scanner=scan),
                user_id=user_id,
            )
            await refresh_skills_system_prompt_cache_async()
            return f"Created custom skill '{name}'."

        if action == "edit":
            await _to_thread(skill_storage.ensure_custom_skill_is_editable, name, user_id=user_id)
            if content is None:
                raise ValueError("content is required for edit.")
            await _to_thread(skill_storage.validate_skill_markdown_content, name, content)
            scan = await _scan_or_raise(content, executable=False, location=f"{name}/{SKILL_MD_FILE}")
            skill_file = skill_storage.get_custom_skill_file(name, user_id=user_id)
            prev_content = await _to_thread(skill_file.read_text, encoding="utf-8")
            await _to_thread(skill_storage.write_custom_skill, name, SKILL_MD_FILE, content, user_id=user_id)
            await _to_thread(
                skill_storage.append_history,
                name,
                _history_record(action="edit", file_path=SKILL_MD_FILE, prev_content=prev_content, new_content=content, thread_id=thread_id, scanner=scan),
                user_id=user_id,
            )
            await refresh_skills_system_prompt_cache_async()
            return f"Updated custom skill '{name}'."

        if action == "patch":
            await _to_thread(skill_storage.ensure_custom_skill_is_editable, name, user_id=user_id)
            if find is None or replace is None:
                raise ValueError("find and replace are required for patch.")
            skill_file = skill_storage.get_custom_skill_file(name, user_id=user_id)
            prev_content = await _to_thread(skill_file.read_text, encoding="utf-8")
            occurrences = prev_content.count(find)
            if occurrences == 0:
                raise ValueError("Patch target not found in SKILL.md.")
            if expected_count is not None and occurrences != expected_count:
                raise ValueError(f"Expected {expected_count} replacements but found {occurrences}.")
            replacement_count = expected_count if expected_count is not None else 1
            new_content = prev_content.replace(find, replace, replacement_count)
            await _to_thread(skill_storage.validate_skill_markdown_content, name, new_content)
            scan = await _scan_or_raise(new_content, executable=False, location=f"{name}/{SKILL_MD_FILE}")
            await _to_thread(skill_storage.write_custom_skill, name, SKILL_MD_FILE, new_content, user_id=user_id)
            await _to_thread(
                skill_storage.append_history,
                name,
                _history_record(action="patch", file_path=SKILL_MD_FILE, prev_content=prev_content, new_content=new_content, thread_id=thread_id, scanner=scan),
                user_id=user_id,
            )
            await refresh_skills_system_prompt_cache_async()
            return f"Patched custom skill '{name}' ({replacement_count} replacement(s) applied, {occurrences} match(es) found)."

        if action == "delete":
            await _to_thread(
                skill_storage.delete_custom_skill,
                name,
                history_meta=_history_record(
                    action="delete",
                    file_path=SKILL_MD_FILE,
                    prev_content=None,
                    new_content=None,
                    thread_id=thread_id,
                    scanner={"decision": "allow", "reason": "Deletion requested."},
                ),
                user_id=user_id,
            )
            await refresh_skills_system_prompt_cache_async()
            return f"Deleted custom skill '{name}'."

        if action == "write_file":
            await _to_thread(skill_storage.ensure_custom_skill_is_editable, name, user_id=user_id)
            if path is None or content is None:
                raise ValueError("path and content are required for write_file.")
            target = await _to_thread(skill_storage.ensure_safe_support_path, name, path, user_id=user_id)
            exists = await _to_thread(target.exists)
            prev_content = await _to_thread(target.read_text, encoding="utf-8") if exists else None
            executable = "scripts/" in path or path.startswith("scripts/")
            scan = await _scan_or_raise(content, executable=executable, location=f"{name}/{path}")
            await _to_thread(skill_storage.write_custom_skill, name, path, content, user_id=user_id)
            await _to_thread(
                skill_storage.append_history,
                name,
                _history_record(action="write_file", file_path=path, prev_content=prev_content, new_content=content, thread_id=thread_id, scanner=scan),
                user_id=user_id,
            )
            return f"Wrote '{path}' for custom skill '{name}'."

        if action == "remove_file":
            await _to_thread(skill_storage.ensure_custom_skill_is_editable, name, user_id=user_id)
            if path is None:
                raise ValueError("path is required for remove_file.")
            target = await _to_thread(skill_storage.ensure_safe_support_path, name, path, user_id=user_id)
            if not await _to_thread(target.exists):
                raise FileNotFoundError(f"Supporting file '{path}' not found for skill '{name}'.")
            prev_content = await _to_thread(target.read_text, encoding="utf-8")
            await _to_thread(target.unlink)
            await _to_thread(
                skill_storage.append_history,
                name,
                _history_record(action="remove_file", file_path=path, prev_content=prev_content, new_content=None, thread_id=thread_id, scanner={"decision": "allow", "reason": "Deletion requested."}),
                user_id=user_id,
            )
            return f"Removed '{path}' from custom skill '{name}'."

        if await _to_thread(skill_storage.public_skill_exists, name):
            raise ValueError(f"'{name}' is a built-in skill. To customise it, create a new skill with the same name under skills/custom/.")
        raise ValueError(f"Unsupported action '{action}'.")


@tool("skill_manage", parse_docstring=True)
async def skill_manage_tool(
    runtime: Runtime,
    action: str,
    name: str,
    content: str | None = None,
    path: str | None = None,
    find: str | None = None,
    replace: str | None = None,
    expected_count: int | None = None,
) -> str:
    """Manage custom skills under skills/custom/.

    Args:
        action: One of create, patch, edit, delete, write_file, remove_file.
        name: Skill name in hyphen-case.
        content: New file content for create, edit, or write_file.
        path: Supporting file path for write_file or remove_file.
        find: Existing text to replace for patch.
        replace: Replacement text for patch.
        expected_count: Optional expected number of replacements for patch.
    """
    return await _skill_manage_impl(
        runtime=runtime,
        action=action,
        name=name,
        content=content,
        path=path,
        find=find,
        replace=replace,
        expected_count=expected_count,
    )


skill_manage_tool.func = make_sync_tool_wrapper(_skill_manage_impl, "skill_manage")
