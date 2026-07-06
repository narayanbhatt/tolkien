"""Cryptographic helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """
    Return the SHA-256 hex digest of a file (streamed in 1 MiB chunks).

    Args:
            path (Path): Filesystem path to read, write, or fingerprint.

    Returns:
            Lowercase hex SHA-256 digest of the file contents.
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
