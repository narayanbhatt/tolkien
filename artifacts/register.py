"""Register a path or URI as an artifact and optional primitive entity."""

from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path

from tolkien._util.crypto import sha256_file
from tolkien.artifacts.models import Artifact
from tolkien.artifacts.spec import BuildArtifactSpec
from tolkien.primitives.ids import stable_id
from tolkien.primitives.models import Entity
from tolkien.registry.datastore_registry import DatastoreRegistry


def infer_format(path_or_uri: str) -> str:
    """
    Infer file format from path suffixes (e.g. ``nii.gz`` -> ``nii.gz``).

    Args:
            path_or_uri (str): Local repository path or external URI locating an artifact payload.

    Returns:
            Inferred format suffix string, or empty when no suffix is present.
    """

    suffixes = Path(path_or_uri).suffixes
    if not suffixes:
        return ""
    return "".join(suffixes).lstrip(".")


def build_artifact(spec: BuildArtifactSpec) -> tuple[Artifact, Entity | None]:
    """
    Build an :class:`Artifact` and optional companion :class:`Entity` from a spec.

    Args:
            spec (BuildArtifactSpec): Typed registration or persist specification.

    Returns:
            Built ``(Artifact, Entity | None)`` pair (entity present when ``create_entity``).
    """

    repo_root = spec.repo_root.resolve()
    path_rel = spec.path_rel or ""
    uri = spec.uri or ""
    local_path = repo_root / path_rel if path_rel else None

    byte_size = None
    sha256 = spec.sha256 or ""
    if local_path and local_path.exists():
        if local_path.is_file():
            byte_size = local_path.stat().st_size
            sha256 = sha256 or sha256_file(local_path)
        elif local_path.is_dir():
            total = 0
            for child in local_path.rglob("*"):
                if child.is_file():
                    total += child.stat().st_size
            byte_size = total

    locator = path_rel or uri
    artifact_id = spec.artifact_id or stable_id("art", spec.artifact_type, spec.artifact_role, locator, spec.version)
    entity_id = spec.entity_id or f"ent_{artifact_id}"
    media_type = spec.media_type or mimetypes.guess_type(locator)[0] or ""
    artifact_format = spec.format or infer_format(locator)

    artifact = Artifact(
        artifact_id=artifact_id,
        entity_id=entity_id,
        artifact_type=spec.artifact_type,
        artifact_role=spec.artifact_role,
        path_rel=path_rel,
        uri=uri,
        media_type=media_type,
        format=artifact_format,
        schema_ref=spec.schema_ref,
        sha256=sha256,
        byte_size=byte_size,
        created_by_event_id=spec.created_by_event_id,
        created_by_run_id=spec.created_by_run_id,
        version=spec.version,
        status=spec.status,
        metadata=dict(spec.metadata),
        source_name=spec.source_name,
        source_version=spec.source_version,
    )

    entity = None
    if spec.create_entity:
        entity = Entity(
            entity_id=entity_id,
            entity_type="artifact",
            name=spec.name or artifact_id,
            source_system=spec.source_name,
            source_id=locator,
            version=spec.version,
            status=spec.status,
            metadata={
                "artifact_id": artifact_id,
                "artifact_type": spec.artifact_type,
                "artifact_role": spec.artifact_role,
                "path_rel": path_rel,
                "uri": uri,
            },
            source_name=spec.source_name,
            source_version=spec.source_version,
        )
    return artifact, entity


def main() -> None:
    """
    CLI: register a path or URI as an artifact (optional entity + CSV write).
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description="Register a local path or URI as an artifact.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact-id", default="")
    parser.add_argument("--entity-id", default="")
    parser.add_argument("--artifact-type", required=True)
    parser.add_argument("--artifact-role", required=True)
    parser.add_argument("--path-rel", default="")
    parser.add_argument("--uri", default="")
    parser.add_argument("--media-type", default="")
    parser.add_argument("--format", default="")
    parser.add_argument("--schema-ref", default="")
    parser.add_argument("--sha256", default="")
    parser.add_argument("--created-by-event-id", default="")
    parser.add_argument("--created-by-run-id", default="")
    parser.add_argument("--version", default="1")
    parser.add_argument("--status", default="active")
    parser.add_argument("--metadata-json", default="{}")
    parser.add_argument("--source-name", default="artifact_register")
    parser.add_argument("--source-version", default="v1")
    parser.add_argument("--name", default="")
    parser.add_argument("--create-entity", action="store_true")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    artifact, entity = build_artifact(BuildArtifactSpec.from_namespace(args))
    if args.write:
        registry = DatastoreRegistry(args.repo_root)
        registry.append_artifacts([artifact], append=args.append)
        if entity is not None:
            registry.append_primitives([entity], append=args.append)

    print(
        json.dumps(
            {
                "artifact": artifact.as_dict(),
                "entity": entity.as_dict() if entity else None,
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
