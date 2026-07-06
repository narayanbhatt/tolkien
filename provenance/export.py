"""Bundle exporters for run provenance (RO-Crate stub)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

from tolkien.provenance.context import ProvenanceContext
from tolkien.provenance.step import StepProvenanceRecord


class ProvenanceBundleExporter(ABC):
    """Export run provenance records to an external bundle format."""

    @abstractmethod
    def export(
        self,
        ctx: ProvenanceContext,
        records: Sequence[StepProvenanceRecord],
        out_path: Path,
    ) -> None:
        """
        Write bundle artifact to ``out_path``.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                records (Sequence[StepProvenanceRecord]): Step provenance records included in an export bundle.
                out_path (Path): Output file path for an exported bundle or report artifact.

        Returns:
                None.
        """

        raise NotImplementedError


class RocrateProvenanceExporter(ProvenanceBundleExporter):
    """Minimal JSON-LD stub using schema.org CreateAction (Phase I)."""

    def export(
        self,
        ctx: ProvenanceContext,
        records: Sequence[StepProvenanceRecord],
        out_path: Path,
    ) -> None:
        """
        Write a minimal schema.org JSON-LD stub to ``out_path``.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                records (Sequence[StepProvenanceRecord]): Step provenance records included in an export bundle.
                out_path (Path): Output file path for an exported bundle or report artifact.

        Returns:
                None.
        """

        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "@context": "https://schema.org/",
            "@graph": [
                {
                    "@type": "CreateAction",
                    "identifier": ctx.run_id,
                    "name": ctx.workflow_name,
                    "agent": {
                        "@type": "SoftwareApplication",
                        "name": ctx.agent_default.source_name,
                        "version": ctx.agent_default.source_version,
                    },
                    "object": [{"@type": "Thing", "identifier": ref.entity_id} for r in records for ref in r.used_entities],
                    "result": [{"@type": "Thing", "identifier": ref.entity_id} for r in records for ref in r.generated_entities],
                }
            ],
        }
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
