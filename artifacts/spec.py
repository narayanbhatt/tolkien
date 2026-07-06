"""Domain spec for building artifact registry rows."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BuildArtifactSpec:
    """Storage-neutral inputs for ``build_artifact``."""

    repo_root: Path
    artifact_type: str
    artifact_role: str
    path_rel: str = ""
    uri: str = ""
    artifact_id: str = ""
    entity_id: str = ""
    media_type: str = ""
    format: str = ""
    schema_ref: str = ""
    sha256: str = ""
    created_by_event_id: str = ""
    created_by_run_id: str = ""
    version: str = "1"
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "artifact_register"
    source_version: str = "v1"
    name: str = ""
    create_entity: bool = False

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> BuildArtifactSpec:
        """
        Build a spec from CLI ``argparse`` namespace fields.

        Args:
                args (argparse.Namespace): Parsed CLI namespace produced by ``argparse``.

        Returns:
            ``BuildArtifactSpec`` populated from CLI namespace fields.
        """

        metadata_raw = getattr(args, "metadata_json", "{}")
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw or "{}")
        else:
            metadata = metadata_raw or {}

        return cls(
            repo_root=args.repo_root,
            artifact_id=getattr(args, "artifact_id", "") or "",
            entity_id=getattr(args, "entity_id", "") or "",
            artifact_type=args.artifact_type,
            artifact_role=args.artifact_role,
            path_rel=getattr(args, "path_rel", "") or "",
            uri=getattr(args, "uri", "") or "",
            media_type=getattr(args, "media_type", "") or "",
            format=getattr(args, "format", "") or "",
            schema_ref=getattr(args, "schema_ref", "") or "",
            sha256=getattr(args, "sha256", "") or "",
            created_by_event_id=getattr(args, "created_by_event_id", "") or "",
            created_by_run_id=getattr(args, "created_by_run_id", "") or "",
            version=getattr(args, "version", "1") or "1",
            status=getattr(args, "status", "active") or "active",
            metadata=metadata,
            source_name=getattr(args, "source_name", "artifact_register") or "artifact_register",
            source_version=getattr(args, "source_version", "v1") or "v1",
            name=getattr(args, "name", "") or "",
            create_entity=bool(getattr(args, "create_entity", False)),
        )

    def with_run_id_from_env(self) -> BuildArtifactSpec:
        """
        Return a copy with ``created_by_run_id`` filled from ``GENFEAT_RUN_ID`` when empty.
        
        Returns:
        Copy with ``created_by_run_id`` filled from ``GENFEAT_RUN_ID`` when empty.
        """

        rid = self.created_by_run_id.strip()
        if not rid:
            rid = os.environ.get("GENFEAT_RUN_ID", "").strip()
        if rid == self.created_by_run_id:
            return self
        return BuildArtifactSpec(
            repo_root=self.repo_root,
            artifact_type=self.artifact_type,
            artifact_role=self.artifact_role,
            path_rel=self.path_rel,
            uri=self.uri,
            artifact_id=self.artifact_id,
            entity_id=self.entity_id,
            media_type=self.media_type,
            format=self.format,
            schema_ref=self.schema_ref,
            sha256=self.sha256,
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
