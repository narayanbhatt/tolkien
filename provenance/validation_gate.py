"""Validation as a provenanced step (in-process validator)."""

from __future__ import annotations

import uuid
from pathlib import Path

from tolkien.provenance.context import ProvenanceContext
from tolkien.provenance.step import (
    ProvenanceEntityRef,
    ProvenancedStep,
    StepOutcome,
    StepProvenanceRecord,
)
from tolkien.validation.validate import Validator, write_reports


class ValidationProvenanceStep(ProvenancedStep):
    """Runs ``tolkien.validation.validate`` Validator and writes reports unless disabled."""

    def __init__(
        self,
        step_id: str,
        *,
        fail_closed: bool = True,
        write_reports_to_disk: bool = True,
        checkpoint_after: bool = False,
    ) -> None:
        """
        Configure fail-closed validation and optional on-disk reports.

        Args:
                step_id (str): Logical provenanced step identifier and manifest step name.
                fail_closed (bool): When ``True``, error-level validation failures fail the provenanced step. Keyword-only.
                write_reports_to_disk (bool): When ``True``, write JSONL and markdown validation reports to disk. Keyword-only.
                checkpoint_after (bool): When ``True``, persist a checkpoint after a successful leaf execution. Keyword-only.

        Returns:
                None.
        """
        super().__init__(step_id, checkpoint_after=checkpoint_after)
        self._fail_closed = fail_closed
        self._write_reports_to_disk = write_reports_to_disk

    def run(self, ctx: ProvenanceContext) -> StepProvenanceRecord:
        """
        Run schema validation and optionally write JSONL/markdown reports.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.

        Returns:
            :class:`~tolkien.provenance.step.StepProvenanceRecord` with validation summary and report refs.
        """

        validation_run_id = f"val_{uuid.uuid4().hex[:12]}"
        validator = Validator(ctx.repo_root)
        checks = validator.run()
        error_failures = [c for c in checks if c.severity == "error" and c.failure_count]

        jsonl_path: Path | None = None
        md_path: Path | None = None
        if self._write_reports_to_disk:
            jsonl_path, md_path = write_reports(ctx.repo_root, validation_run_id, checks)

        summary: dict = {
            "validation_run_id": validation_run_id,
            "checks": len(checks),
            "failed_checks": len([c for c in checks if c.failure_count]),
            "error_failures": len(error_failures),
        }

        generated: list[ProvenanceEntityRef] = []
        if jsonl_path is not None:
            generated.append(
                ProvenanceEntityRef(
                    entity_id=validation_run_id,
                    entity_type="validation_log",
                    role="validation_jsonl",
                    uri_or_path=str(jsonl_path.relative_to(ctx.repo_root)),
                )
            )
        if md_path is not None:
            generated.append(
                ProvenanceEntityRef(
                    entity_id=f"{validation_run_id}_md",
                    entity_type="validation_log",
                    role="validation_markdown",
                    uri_or_path=str(md_path.relative_to(ctx.repo_root)),
                )
            )

        if self._fail_closed and error_failures:
            return StepProvenanceRecord(
                outcome=StepOutcome.FAIL,
                summary=summary,
                generated_entities=tuple(generated),
            )

        return StepProvenanceRecord(
            outcome=StepOutcome.SUCCESS,
            summary=summary,
            generated_entities=tuple(generated),
        )


class ValidationGate(ValidationProvenanceStep):
    """Standalone validation node."""
