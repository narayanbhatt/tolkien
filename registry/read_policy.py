"""Read policy and permissions stub for master table access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


@dataclass(frozen=True)
class DatastoreReadPolicy:
    """Controls master-table read behavior. Enforcement is stubbed for now."""

    role: str = "default"
    active_only_default: bool = True
    allowed_tables: frozenset[str] | None = None


class DatastorePermissions:
    """Permission gate invoked before every master-table read."""

    @staticmethod
    def assert_can_read(stem: str, policy: DatastoreReadPolicy) -> None:
        """
        Stub: no-op today; future allowlist, role checks, and audit logging.

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).
                policy (DatastoreReadPolicy): :class:`~tolkien.registry.read_policy.DatastoreReadPolicy` applied before reads.

        Returns:
                None; stub permission gate (no-op today).
        """

        _ = stem, policy


def known_table_stems(schema_root: Path) -> frozenset[str]:
    """
    Union of table names declared in schema contract YAML files.

    Args:
            schema_root (Path): Directory containing master schema contract YAML files.

    Returns:
            Table stems declared in master schema contract YAML files.
    """

    stems: set[str] = set()
    for name in ("master_table_contracts.yaml", "patient_time_contracts.yaml"):
        path = schema_root / name
        if not path.is_file():
            continue
        if yaml is None:
            continue
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        stems.update((data.get("tables") or {}).keys())
    return frozenset(stems)
