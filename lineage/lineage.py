"""Helpers for W3C PROV-inspired lineage edges."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from tolkien._util.ids import stable_id
from tolkien._util.time import utc_now


LINEAGE_FIELDS = [
    "lineage_edge_id",
    "run_id",
    "activity_type",
    "activity_id",
    "source_entity_type",
    "source_entity_id",
    "source_role",
    "target_entity_type",
    "target_entity_id",
    "target_role",
    "agent_type",
    "agent_id",
    "derivation_type",
    "created_at",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]


@dataclass(frozen=True)
class LineageEdge:
    """One PROV-inspired derivation edge between source and target entities."""

    run_id: str
    activity_type: str
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    derivation_type: str = "derived_from"
    activity_id: str = ""
    source_role: str = ""
    target_role: str = ""
    agent_type: str = "script"
    agent_id: str = ""
    source_name: str = "local_workflow"
    source_version: str = "v1"

    def as_row(self) -> dict[str, object]:
        """
        Serialize to a ``lineage_edges.csv`` row dict with stable ``lineage_edge_id``.
        
        Returns:
        ``lineage_edges.csv`` row dict including generated ``lineage_edge_id``.
        """

        created_at = utc_now()
        return {
            "lineage_edge_id": stable_id(
                "lin",
                self.run_id,
                self.activity_type,
                self.source_entity_type,
                self.source_entity_id,
                self.target_entity_type,
                self.target_entity_id,
                self.derivation_type,
            ),
            "run_id": self.run_id,
            "activity_type": self.activity_type,
            "activity_id": self.activity_id,
            "source_entity_type": self.source_entity_type,
            "source_entity_id": self.source_entity_id,
            "source_role": self.source_role,
            "target_entity_type": self.target_entity_type,
            "target_entity_id": self.target_entity_id,
            "target_role": self.target_role,
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "derivation_type": self.derivation_type,
            "created_at": created_at,
            "source_name": self.source_name,
            "source_version": self.source_version,
            "ingested_at": created_at,
            "record_version": 1,
            "is_active": True,
        }


def append_lineage_edges(csv_path: Path, edges: list[LineageEdge]) -> None:
    """
    Append lineage edge rows to a CSV file (writes header when creating).

    Args:
            csv_path (Path): CSV file path; parent directories are created on write when needed.
            edges (list[LineageEdge]): Lineage edges to append or forward.

    Returns:
            None; appends rows and writes a header when creating the CSV.
    """

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LINEAGE_FIELDS)
        if not file_exists:
            writer.writeheader()
        for edge in edges:
            writer.writerow(edge.as_row())
