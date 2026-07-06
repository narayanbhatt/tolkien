"""Filesystem layout for local-first datastore (master CSV mirrors, manifests)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatastorePaths:
    """Canonical paths derived from repo root."""

    repo_root: Path

    @property
    def master_csv(self) -> Path:
        """
        Directory of canonical CSV mirrors.
        
        Returns:
        ``Path`` value.
        """

        return self.repo_root / "data" / "master" / "csv"

    @property
    def schema_root(self) -> Path:
        """
        Directory of schema contracts and validation specs.
        
        Returns:
        ``Path`` value.
        """

        return self.repo_root / "data" / "master" / "schema"

    @property
    def artifacts_root(self) -> Path:
        """
        Root for derived artifact payloads.
        
        Returns:
        ``Path`` value.
        """

        return self.repo_root / "data" / "artifacts"

    @property
    def artifacts_csv(self) -> Path:
        """
        Path to ``artifacts.csv`` master mirror.
        
        Returns:
        ``Path`` value.
        """

        return self.master_csv / "artifacts.csv"

    @property
    def lineage_edges_csv(self) -> Path:
        """
        Path to ``lineage_edges.csv`` master mirror.
        
        Returns:
        ``Path`` value.
        """

        return self.master_csv / "lineage_edges.csv"

    @property
    def run_manifests_dir(self) -> Path:
        """
        Directory for workflow run manifest JSON files.
        
        Returns:
        ``Path`` value.
        """

        return self.artifacts_root / "index" / "run_manifests"

    @property
    def cohort_manifests_dir(self) -> Path:
        """
        Directory for cohort manifest JSON files.
        
        Returns:
        ``Path`` value.
        """

        return self.artifacts_root / "cohort_manifests"

    @property
    def validation_logs_dir(self) -> Path:
        """
        Directory for validation JSONL and markdown summaries.
        
        Returns:
        ``Path`` value.
        """

        return self.repo_root / "data" / "logs" / "validation"
