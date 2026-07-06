"""Central datastore registry, master-table reader, paths, and run manifests.

``DatastoreRegistry`` is the preferred write path for master CSV mirrors, lineage,
artifacts, and run manifest JSON. ``MasterTableReader`` is the read gateway.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ArtifactPersistSpec",
    "ConfigurationArtifactRegistration",
    "DatastoreRegistry",
    "DatastorePaths",
    "MasterTableReader",
    "MasterTableReaderProtocol",
    "build_manifest",
    "is_active_row",
    "write_manifest",
]


def __getattr__(name: str) -> Any:
    if name == "ArtifactPersistSpec":
        from tolkien.registry.persist_spec import ArtifactPersistSpec

        return ArtifactPersistSpec
    if name == "ConfigurationArtifactRegistration":
        from tolkien.registry.configuration_artifacts import ConfigurationArtifactRegistration

        return ConfigurationArtifactRegistration
    if name == "DatastoreRegistry":
        from tolkien.registry.datastore_registry import DatastoreRegistry

        return DatastoreRegistry
    if name == "DatastorePaths":
        from tolkien.registry.layout import DatastorePaths

        return DatastorePaths
    if name == "MasterTableReader":
        from tolkien.registry.master_table_reader import MasterTableReader

        return MasterTableReader
    if name == "MasterTableReaderProtocol":
        from tolkien.registry.protocols import MasterTableReaderProtocol

        return MasterTableReaderProtocol
    if name == "build_manifest":
        from tolkien.registry.run_manifest import build_manifest

        return build_manifest
    if name == "is_active_row":
        from tolkien.registry.master_table_reader import is_active_row

        return is_active_row
    if name == "write_manifest":
        from tolkien.registry.run_manifest import write_manifest

        return write_manifest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
