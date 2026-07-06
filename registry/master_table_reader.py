"""Controlled read access to master CSV mirrors."""

from __future__ import annotations

from pathlib import Path

from tolkien._util.csv_io import read_csv

from .layout import DatastorePaths
from .read_policy import DatastorePermissions, DatastoreReadPolicy


def is_active_row(row: dict[str, str]) -> bool:
    """
    Return False when ``is_active`` is explicitly false (case-insensitive).

    Args:
            row (dict[str, str]): Single master-table row dict.

    Returns:
        ``False`` when ``is_active`` is explicitly false (case-insensitive).
    """

    return str(row.get("is_active", "True")).lower() != "false"


class MasterTableReader:
    """Single read gateway for ``data/master/csv/*.csv`` mirrors."""

    def __init__(
        self,
        paths: DatastorePaths,
        *,
        policy: DatastoreReadPolicy | None = None,
    ) -> None:
        """
        Attach to canonical datastore paths and optional read policy.

        Args:
                paths (DatastorePaths): Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace.
                policy (DatastoreReadPolicy | None): :class:`~tolkien.registry.read_policy.DatastoreReadPolicy` applied before reads. Keyword-only.

        Returns:
                None.
        """

        self._paths = paths
        self._policy = policy or DatastoreReadPolicy()

    @property
    def paths(self) -> DatastorePaths:
        """
        Canonical filesystem layout for this reader.
        
        Returns:
        Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace.
        """

        return self._paths

    @property
    def policy(self) -> DatastoreReadPolicy:
        """
        Read policy applied before each table access.
        
        Returns:
        ``DatastoreReadPolicy`` value.
        """

        return self._policy

    def table_path(self, stem: str) -> Path:
        """
        Path to ``data/master/csv/{stem}.csv``.

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).

        Returns:
                Absolute path to ``data/master/csv/{stem}.csv``.
        """

        return self._paths.master_csv / f"{stem}.csv"

    def table_exists(self, stem: str) -> bool:
        """
        Return True when the CSV mirror file exists.

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).

        Returns:
            ``True`` when the CSV mirror file exists.
        """

        return self.table_path(stem).is_file()

    def read_table(self, stem: str) -> list[dict[str, str]]:
        """
        Read all rows from a master CSV (empty list when missing).

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).

        Returns:
                All rows from ``data/master/csv/{stem}.csv`` (empty when missing).
        """

        DatastorePermissions.assert_can_read(stem, self._policy)
        path = self.table_path(stem)
        if not path.is_file():
            return []
        return read_csv(path)

    def read_active_table(self, stem: str) -> list[dict[str, str]]:
        """
        Return only rows where :func:`is_active_row` is true.

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).

        Returns:
                Active rows only, filtered via :func:`is_active_row`.
        """

        return [row for row in self.read_table(stem) if is_active_row(row)]
