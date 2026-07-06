"""Stable ID helpers."""

from __future__ import annotations

import hashlib


def stable_id(prefix: str, *parts: object, length: int = 12) -> str:
    """
    Build a deterministic ID from stable source parts.

    Args:
            prefix (str): Stable identifier prefix segment (for example ``art`` or ``evt``).
            length (int): Hex digest length for :func:`~tolkien._util.ids.stable_id`. Keyword-only.

    Returns:
            Deterministic identifier ``{prefix}_{digest}``.
    """

    payload = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"
