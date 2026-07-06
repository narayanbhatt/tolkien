"""Single entry point for datastore writes (master CSV mirrors, manifests, lineage)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from typing import Any

from tolkien._util.csv_io import write_csv
from tolkien.artifacts.models import Artifact
from tolkien.artifacts.spec import BuildArtifactSpec
from tolkien.artifacts.writer import CsvArtifactWriter
from tolkien.lineage.lineage import LineageEdge, append_lineage_edges
from tolkien.primitives.abc import PrimitiveObject
from tolkien.primitives.models import Entity
from tolkien.primitives.writer import TABLE_BY_KIND, CsvPrimitiveWriter

from . import run_manifest
from .layout import DatastorePaths
from .master_table_reader import MasterTableReader
from .persist_spec import ArtifactPersistSpec
from .read_policy import DatastoreReadPolicy


class DatastoreRegistry:
    """Delegates to existing CSV/JSON sinks; callers should prefer this over writers."""

    def __init__(
        self,
        repo_root: Path | None = None,
        *,
        paths: DatastorePaths | None = None,
        read_policy: DatastoreReadPolicy | None = None,
    ) -> None:
        """
        Bind to a repo root or explicit :class:`DatastorePaths` layout.

        Args:
                repo_root (Path | None): Repository root; relative paths resolve against this directory. Optional.
                paths (DatastorePaths | None): Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace. Keyword-only.
                read_policy (DatastoreReadPolicy | None): DatastoreReadPolicy | None value for ``read_policy``. Keyword-only.

        Returns:
                None.
        """

        if paths is None:
            if repo_root is None:
                raise ValueError("Provide repo_root or paths")
            paths = DatastorePaths(repo_root=repo_root.resolve())
        self.paths = paths
        self.reader = MasterTableReader(paths, policy=read_policy)

    @staticmethod
    def should_append_csv(path: Path) -> bool:
        """
        Mirror existing convention: append when CSV exists with content.

        Args:
                path (Path): Filesystem path to read, write, or fingerprint.

        Returns:
            ``True`` when ``path`` exists and has non-zero size (append convention).
        """
        return path.exists() and path.stat().st_size > 0

    def read_master_csv_rows(self, stem: str) -> list[dict[str, str]]:
        """
        Read all rows from ``data/master/csv/{stem}.csv``.

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).

        Returns:
                All rows from the requested master CSV mirror.
        """

        return self.reader.read_table(stem)

    def master_csv_cell_exists(self, stem: str, key: str, value: str) -> bool:
        """
        Return True if any row in the table has ``row[key] == value``.

        Args:
                stem (str): Master CSV table stem (``data/master/csv/{stem}.csv``).
                key (str): Column name or per-run context slot key.
                value (str): Cell value to match, or slot value to store.

        Returns:
            ``True`` when any row contains ``row[key] == value``.
        """

        for row in self.read_master_csv_rows(stem):
            if row.get(key) == value:
                return True
        return False

    def append_artifacts(
        self,
        artifacts: Iterable[Artifact],
        *,
        append: bool | None = None,
        skip_validate: bool = False,
    ) -> int:
        """
        Append artifact rows to ``artifacts.csv``; infer append mode when ``append`` is None.

        Args:
                artifacts (Iterable[Artifact]): Artifact instances to validate and persist.
                append (bool | None): When ``True``, append rows; when ``False``, overwrite. ``None`` infers from existing file size. Keyword-only.
                skip_validate (bool): When ``True``, skip row validation before writing CSV output. Keyword-only.

        Returns:
                Number of artifact rows written.
        """

        output_path = self.paths.artifacts_csv
        resolved_append = self.should_append_csv(output_path) if append is None else append
        return CsvArtifactWriter(output_path).write(
            list(artifacts),
            append=resolved_append,
            skip_validate=skip_validate,
        )

    def append_primitives(
        self,
        objects: Iterable[PrimitiveObject],
        *,
        append: bool | None = None,
        skip_validate: bool = False,
    ) -> dict[str, int]:
        """
        Write primitives; default infers append per touched table.

        Args:
                objects (Iterable[PrimitiveObject]): Primitive objects to validate and persist.
                append (bool | None): When ``True``, append rows; when ``False``, overwrite. ``None`` infers from existing file size. Keyword-only.
                skip_validate (bool): When ``True``, skip row validation before writing CSV output. Keyword-only.

        Returns:
                Mapping of primitive table name to rows written.
        """

        objs = list(objects)
        if not objs:
            return {}

        grouped: dict[str, list[PrimitiveObject]] = defaultdict(list)
        for obj in objs:
            grouped[obj.object_kind].append(obj)

        writer = CsvPrimitiveWriter(self.paths.master_csv)
        totals: dict[str, int] = {}
        if append is not None:
            return writer.write(objs, append=append, skip_validate=skip_validate)

        for group in grouped.values():
            tables = {TABLE_BY_KIND[o.object_kind] for o in group}
            batch_append = False
            for table in tables:
                path = self.paths.master_csv / f"{table}.csv"
                if self.should_append_csv(path):
                    batch_append = True
                    break
            part = writer.write(group, append=batch_append, skip_validate=skip_validate)
            for table_name, count in part.items():
                totals[table_name] = totals.get(table_name, 0) + count
        return totals

    def append_lineage_edges(self, edges: Iterable[LineageEdge]) -> None:
        """
        Append lineage edges to ``lineage_edges.csv``.

        Args:
                edges (Iterable[LineageEdge]): Lineage edges to append or forward.

        Returns:
                None; appends rows and writes a header when creating the CSV.
        """

        append_lineage_edges(self.paths.lineage_edges_csv, list(edges))

    def build_run_manifest(
        self,
        run_type: str,
        status: str,
        parameters: dict[str, Any] | None = None,
        input_files: list[str] | None = None,
        outputs: list[str] | None = None,
        validation_run_ids: list[str] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a run manifest dict (delegates to :mod:`run_manifest`).

        Args:
                run_type (str): Workflow category string stored as ``run_type`` in the manifest.
                status (str): Terminal run status (for example ``completed`` or ``failed``).
                parameters (dict[str, Any] | None): JSON-serializable parameters recorded in the run manifest. Optional.
                input_files (list[str] | None): Input file paths listed in the run manifest. Optional.
                outputs (list[str] | None): Output paths declared or discovered for the run manifest. Optional.
                validation_run_ids (list[str] | None): Validation gate run IDs associated with this workflow run. Optional.
                run_id (str | None): Workflow run identifier (often ``GENFEAT_RUN_ID``). Optional.

        Returns:
                Run manifest mapping suitable for :func:`~tolkien.registry.run_manifest.write_manifest`.
        """

        return run_manifest.build_manifest(
            paths=self.paths,
            run_type=run_type,
            status=status,
            parameters=parameters,
            input_files=input_files,
            outputs=outputs,
            validation_run_ids=validation_run_ids,
            run_id=run_id,
        )

    def write_run_manifest(self, manifest: dict[str, Any]) -> Path:
        """
        Write manifest JSON under ``data/artifacts/index/run_manifests/``.

        Args:
                manifest (dict[str, Any]): Run manifest mapping written as JSON under ``run_manifests/``.

        Returns:
                Path to the written manifest JSON file.
        """

        return run_manifest.write_manifest(self.paths, manifest)

    def overwrite_master_csv(self, filename: str, rows: list[dict[str, object]], fieldnames: list[str]) -> Path:
        """
        Full-file overwrite semantics for curated tables (e.g. patient_events).

        Args:
                filename (str): Master CSV filename including the ``.csv`` extension.
                rows (list[dict[str, object]]): Table rows represented as string-keyed dicts.
                fieldnames (list[str]): Ordered CSV column headers used for writing.

        Returns:
                Path to the overwritten master CSV file.
        """

        path = self.paths.master_csv / filename
        write_csv(path, rows, fieldnames)
        return path

    def load_artifact_by_id(self, artifact_id: str) -> Artifact | None:
        """
        Resolve an artifact registry row.

        Args:
                artifact_id (str): Stable artifact registry identifier.

        Returns:
                Matching :class:`~tolkien.artifacts.models.Artifact`, or ``None``.
        """

        for row in self.read_master_csv_rows("artifacts"):
            if row.get("artifact_id") != artifact_id:
                continue
            return Artifact.from_csv_row(row)
        return None

    def load_artifact_by_path_rel(self, path_rel: str) -> Artifact | None:
        """
        Resolve the active artifact registry row for ``path_rel``.
        
        Args:
        path_rel (str): Repository-relative path to a payload or registry row locator.
        
        Returns:
        Active :class:`~tolkien.artifacts.models.Artifact` for ``path_rel``, or ``None``.
        """
        norm = path_rel.replace("\\", "/")
        for row in self.read_master_csv_rows("artifacts"):
            if row.get("path_rel", "").replace("\\", "/") != norm:
                continue
            if str(row.get("is_active", "True")).lower() == "false":
                continue
            return Artifact.from_csv_row(row)
        return None

    def write_registered_artifact(self, artifact_ns: object) -> tuple[Artifact, Entity | None]:
        """
        Build from CLI-style Namespace or ``BuildArtifactSpec`` and persist rows.

        Args:
                artifact_ns (object): ``BuildArtifactSpec`` or CLI ``Namespace`` describing artifact registration inputs.

        Returns:
                Built ``(Artifact, Entity | None)`` pair after persistence.
        """

        from tolkien.artifacts.register import build_artifact

        if isinstance(artifact_ns, BuildArtifactSpec):
            spec = artifact_ns
        else:
            spec = BuildArtifactSpec.from_namespace(artifact_ns)  # type: ignore[arg-type]
        spec.repo_root = self.paths.repo_root.resolve()
        artifact, entity = build_artifact(spec)
        self.append_artifacts([artifact])
        if entity is not None:
            self.append_primitives([entity])
        return artifact, entity

    def resolve_payload_paths(self, path_rel: str) -> tuple[str, Path]:
        """
        Return ``(POSIX path_rel under repo_root, absolute Path)``. Rejects escapes.

        Args:
                path_rel (str): Repository-relative path to a payload or registry row locator.

        Returns:
                Tuple of ``(posix_path_rel, absolute_path)`` under ``repo_root``.
        """

        stripped = path_rel.replace("\\", "/").strip()
        posix_rel = stripped.lstrip("/")
        if not posix_rel:
            raise ValueError("path_rel must be non-empty")

        posix = PurePosixPath(posix_rel)
        parts = posix.parts
        if ".." in parts:
            raise ValueError("path_rel must not contain parent segments ('..').")

        abs_path = Path(self.paths.repo_root, *parts)
        repo_resolved = self.paths.repo_root.resolve()
        resolved = abs_path.resolve()
        resolved.relative_to(repo_resolved)
        return posix_rel, resolved

    def persist_artifact(
        self,
        path_rel: str,
        spec: ArtifactPersistSpec,
        writer_fn: Callable[[Path], None] | None,
        *,
        lineage_edges: Iterable[LineageEdge] | None = None,
        extra_primitives: Iterable[PrimitiveObject] | None = None,
        force_payload_rewrite: bool = False,
    ) -> tuple[Artifact, Entity | None]:
        """
        Write payload (optional), then persist catalog rows (append ``artifacts.csv`` when registering anew).

        Args:
                path_rel (str): Repository-relative path to a payload or registry row locator.
                spec (ArtifactPersistSpec): Typed registration or persist specification.
                writer_fn (Callable[[Path], None] | None): Callable invoked with the absolute payload path to materialize bytes on disk.
                lineage_edges (Iterable[LineageEdge] | None): Optional lineage edges appended after successful registration. Keyword-only.
                extra_primitives (Iterable[PrimitiveObject] | None): Additional primitive rows appended alongside the artifact entity. Keyword-only.
                force_payload_rewrite (bool): When ``True``, re-run ``writer_fn`` even if an active artifact row already exists. Keyword-only.

        Returns:
                Registered ``(Artifact, Entity | None)`` after optional payload write.
        """

        from tolkien.artifacts.register import build_artifact

        posix_rel, abs_path = self.resolve_payload_paths(path_rel)
        existing = self.load_artifact_by_path_rel(posix_rel)

        if existing is not None:
            if force_payload_rewrite and writer_fn is not None:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                writer_fn(abs_path)
            build_spec = spec.to_build_spec(self.paths.repo_root, posix_rel)
            build_spec.artifact_id = existing.artifact_id
            build_spec.entity_id = existing.entity_id
            artifact, entity = build_artifact(build_spec)
            return artifact, entity

        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if writer_fn is not None:
            writer_fn(abs_path)
        elif not abs_path.exists():
            raise FileNotFoundError(
                f"Payload missing at {abs_path}; provide writer_fn or materialize bytes before registering."
            )

        build_spec = spec.to_build_spec(self.paths.repo_root, posix_rel)
        artifact, entity = build_artifact(build_spec)
        errors = artifact.validate()
        if errors:
            raise ValueError(f"artifact invalid before commit: {errors}")

        self.append_artifacts([artifact], skip_validate=True)
        if entity is not None:
            entity_errors = entity.validate()
            if entity_errors:
                raise ValueError(f"entity invalid before commit: {entity_errors}")
            self.append_primitives([entity], skip_validate=True)
        extras_list = list(extra_primitives or [])
        if extras_list:
            for extra in extras_list:
                extra_errors = extra.validate()
                if extra_errors:
                    raise ValueError(f"primitive invalid before commit: {extra_errors}")
            self.append_primitives(extras_list, skip_validate=True)
        if lineage_edges is not None:
            edges_materialized = list(lineage_edges)
            if edges_materialized:
                self.append_lineage_edges(edges_materialized)

        return artifact, entity
