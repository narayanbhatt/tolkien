"""Specification for registering a payload path as an Artifact (+ optional primitives)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tolkien.artifacts.spec import BuildArtifactSpec


@dataclass
class ArtifactPersistSpec:
    """Fields passed to ``build_artifact`` after payload materialization."""

    artifact_type: str
    artifact_role: str
    artifact_id: str = ""
    entity_id: str = ""
    uri: str = ""
    media_type: str = ""
    format: str = ""
    schema_ref: str = ""
    version: str = "1"
    status: str = "active"
    created_by_event_id: str = ""
    created_by_run_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "artifact_register"
    source_version: str = "v1"
    name: str = ""
    create_entity: bool = True

    def to_build_spec(self, repo_root: Path, path_rel_posix: str) -> BuildArtifactSpec:
        """
        Convert persist spec + resolved path into a :class:`BuildArtifactSpec`.

        Args:
                repo_root (Path): Repository root; relative paths resolve against this directory.
                path_rel_posix (str): Normalized POSIX ``path_rel`` under ``repo_root``.

        Returns:
            ``BuildArtifactSpec`` ready for :func:`~tolkien.artifacts.register.build_artifact`.
        """

        rid = self.created_by_run_id.strip()
        if not rid:
            rid = os.environ.get("GENFEAT_RUN_ID", "").strip()

        return BuildArtifactSpec(
            repo_root=repo_root.resolve(),
            artifact_id=self.artifact_id,
            entity_id=self.entity_id,
            artifact_type=self.artifact_type,
            artifact_role=self.artifact_role,
            path_rel=path_rel_posix,
            uri=self.uri,
            media_type=self.media_type,
            format=self.format,
            schema_ref=self.schema_ref,
            created_by_event_id=self.created_by_event_id,
            created_by_run_id=rid,
            version=self.version,
            status=self.status,
            metadata=dict(self.metadata),
            source_name=self.source_name,
            source_version=self.source_version,
            name=self.name,
            create_entity=self.create_entity,
        )
