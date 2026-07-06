"""Typing protocols for datastore registry integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from tolkien.artifacts.models import Artifact

if TYPE_CHECKING:
    from tolkien.registry.datastore_registry import DatastoreRegistry
    from tolkien.registry.layout import DatastorePaths


@runtime_checkable
class MasterTableReaderProtocol(Protocol):
    """Read-only access to master CSV mirrors."""

    @property
    def paths(self) -> DatastorePaths:
        """
        Canonical datastore paths for the workspace.
        
        Returns:
        Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace.
        """
        ...

    def read_table(self, stem: str) -> list[dict[str, str]]:
        """
        Read all rows from a master CSV mirror.
        
        Args:
        stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).
        
        Returns:
        All rows from ``data/master/csv/{stem}.csv`` (empty when missing).
        """
        ...

    def read_active_table(self, stem: str) -> list[dict[str, str]]:
        """
        Read rows where ``is_active`` is not false.
        
        Args:
        stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).
        
        Returns:
        Active rows only, filtered via :func:`is_active_row`.
        """
        ...


@runtime_checkable
class LogsToDatastore(Protocol):
    """Primitives (and similar) append their rows via the datastore registry."""

    def log(self, registry: DatastoreRegistry) -> dict[str, int]:
        """
        Append primitive rows and return per-table write counts.
        
        Args:
        registry (DatastoreRegistry): :class:`~tolkien.registry.datastore_registry.DatastoreRegistry` used for catalog writes.
        
        Returns:
        Mapping of primitive table names to appended row counts.
        """
        ...


@runtime_checkable
class DumpsArtifactToDatastore(Protocol):
    """Typed artifact payloads register rows via the registry."""

    def dump(self, registry: DatastoreRegistry) -> Artifact:
        """
        Register this artifact and return the persisted row.
        
        Args:
        registry (DatastoreRegistry): :class:`~tolkien.registry.datastore_registry.DatastoreRegistry` used for catalog writes.
        
        Returns:
        ``Artifact`` value.
        """
        ...
