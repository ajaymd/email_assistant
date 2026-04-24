"""JSON-backed user profile store.

Schema (see ``user_profiles.json``):

    {
      "users": {
        "<user_id>": {
          "name": str,
          "company": str,
          "signature": str,
          "default_tone": str,
          "drafts": [
            {"ts": str, "intent": str, "draft": dict, "edits": str}
          ]
        }
      }
    }

The store is intentionally minimal — load the whole file, mutate, write it
back atomically. Two-week capstone scope; no need for SQLite.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILE_PATH = Path(__file__).resolve().parent / "user_profiles.json"

# Maximum number of past drafts kept per user. Older entries are dropped on
# write so the file never grows unbounded.
MAX_DRAFTS_PER_USER = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_all() -> dict[str, Any]:
    if not PROFILE_PATH.exists():
        return {"users": {}}
    with open(PROFILE_PATH, "r") as fh:
        return json.load(fh)


def _write_all(data: dict[str, Any]) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write so a crash mid-write cannot corrupt the file.
    fd, tmp_path = tempfile.mkstemp(
        prefix="user_profiles.", suffix=".json", dir=str(PROFILE_PATH.parent)
    )
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, PROFILE_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def list_user_ids() -> list[str]:
    return sorted(_read_all().get("users", {}).keys())


def load_profile(user_id: str) -> dict[str, Any]:
    """Return the profile for ``user_id``, or an empty stub if absent."""
    data = _read_all()
    user = data.get("users", {}).get(user_id)
    if user is None:
        return {
            "user_id": user_id,
            "name": "",
            "company": "",
            "signature": "",
            "default_tone": "friendly",
            "drafts": [],
        }
    return {"user_id": user_id, **user}


def save_profile(profile: dict[str, Any]) -> None:
    """Upsert a profile. ``profile`` must contain a ``user_id`` key."""
    data = _read_all()
    user_id = profile["user_id"]
    stored = {k: v for k, v in profile.items() if k != "user_id"}
    stored.setdefault("drafts", [])
    data.setdefault("users", {})[user_id] = stored
    _write_all(data)


def append_draft(
    user_id: str,
    *,
    intent: str,
    draft: dict[str, Any],
    edits: str = "",
) -> None:
    """Append a draft (and any user edits) to the user's draft history."""
    data = _read_all()
    user = data.setdefault("users", {}).setdefault(
        user_id,
        {
            "name": "",
            "company": "",
            "signature": "",
            "default_tone": "friendly",
            "drafts": [],
        },
    )
    history = user.setdefault("drafts", [])
    history.append(
        {"ts": _now_iso(), "intent": intent, "draft": draft, "edits": edits}
    )
    # Trim oldest entries.
    if len(history) > MAX_DRAFTS_PER_USER:
        user["drafts"] = history[-MAX_DRAFTS_PER_USER:]
    _write_all(data)


def recent_drafts(user_id: str, *, intent: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Return the most recent drafts for a user, optionally filtered by intent."""
    profile = load_profile(user_id)
    drafts = list(profile.get("drafts", []))
    if intent:
        intent_matches = [d for d in drafts if d.get("intent") == intent]
        if intent_matches:
            drafts = intent_matches
    return drafts[-limit:]
