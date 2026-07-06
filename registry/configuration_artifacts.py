"""Typed registration flows for configuration-style artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tolkien.artifacts.register import build_artifact
from tolkien.artifacts.spec import BuildArtifactSpec

from .datastore_registry import DatastoreRegistry


@dataclass(frozen=True)
class ConfigurationArtifactRegistration:
    """experiment YAML, cohort manifests, etc. — registers row + artifact entity."""

    path_rel: str
    artifact_role: str
    source_name: str
    media_type: str
    format: str
    metadata_extra: dict[str, Any]

    def dump(self, registry: DatastoreRegistry) -> dict[str, Any] | None:
        """
        Write artifact plus companion primitive entity unless already registered.

        Args:
                registry (DatastoreRegistry): :class:`~tolkien.registry.datastore_registry.DatastoreRegistry` used for catalog writes.

        Returns:
                Registration summary dict, or ``None`` when entity creation is disabled.
        """

        path_norm = self.path_rel.replace("\\", "/")
        existing = registry.load_artifact_by_path_rel(path_norm)
        if existing is not None:
            return {"artifact_id": existing.artifact_id, "skipped": True}

        spec = BuildArtifactSpec(
            repo_root=registry.paths.repo_root,
            artifact_type="configuration_artifact",
            artifact_role=self.artifact_role,
            path_rel=path_norm,
            media_type=self.media_type,
            format=self.format,
            metadata=dict(self.metadata_extra),
            source_name=self.source_name,
            source_version="v1",
            name=Path(path_norm).stem,
            create_entity=True,
        ).with_run_id_from_env()
        artifact, entity = build_artifact(spec)
        if entity is None:
            return None
        registry.append_artifacts([artifact])
        registry.append_primitives([entity])
        return {"artifact_id": artifact.artifact_id, "entity_id": entity.entity_id, "skipped": False}
