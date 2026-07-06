"""Workflow runner: LIFO stack scheduling, sink flush, manifests."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from tolkien.provenance.checkpoint import CheckpointStore
from tolkien.provenance.context import ProvenanceContext
from tolkien.provenance.sinks import NullSink, ProvenanceSink
from tolkien.provenance.step import (
    ProvenanceEntityRef,
    StepOutcome,
    StepProvenanceRecord,
    WorkflowNode,
)
from tolkien.registry import run_manifest
from tolkien.registry.layout import DatastorePaths


@dataclass
class WorkflowRunResult:
    """Outcome of a full workflow execution (one run_id)."""

    run_id: str
    status: str
    manifest_path: Path | None
    step_records: tuple[StepProvenanceRecord, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class WorkflowRunner(ABC):
    """Orchestrates workflow nodes with centralized provenance sinking."""

    @abstractmethod
    def run(
        self,
        ctx: ProvenanceContext,
        nodes: Sequence[WorkflowNode],
        *,
        resume: bool = False,
        declare_outputs: list[str] | None = None,
        validation_run_ids: list[str] | None = None,
    ) -> WorkflowRunResult:
        """
        Execute workflow nodes and return run outcome plus manifest path.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                nodes (Sequence[WorkflowNode]): Top-level workflow nodes scheduled by the runner.
                resume (bool): When ``True``, load checkpoints and skip completed node iterations. Keyword-only.
                declare_outputs (list[str] | None): Output path strings recorded in the run manifest. Keyword-only.
                validation_run_ids (list[str] | None): Validation gate run IDs associated with this workflow run. Keyword-only.

        Returns:
                Final :class:`~tolkien.provenance.runner.WorkflowRunResult` for the workflow run.
        """

        raise NotImplementedError


class WorkflowEventHandler(ABC):
    """Optional hooks for workflow lifecycle observability."""

    def on_run_start(self, ctx: ProvenanceContext, nodes: Sequence[WorkflowNode]) -> None:
        """
        Hook invoked once before any node executes.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                nodes (Sequence[WorkflowNode]): Top-level workflow nodes scheduled by the runner.

        Returns:
                None.
        """
        del ctx, nodes

    def on_node_start(self, ctx: ProvenanceContext, node_id: str, iteration: int) -> None:
        """
        Hook invoked before a leaf node runs or resumes.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                node_id (str): Logical workflow step or composite node identifier.
                iteration (int): Retry or resume iteration index for ``node_id``.

        Returns:
                None.
        """
        del ctx, node_id, iteration

    def on_node_complete(
        self,
        ctx: ProvenanceContext,
        node_id: str,
        record: StepProvenanceRecord,
        iteration: int,
    ) -> None:
        """
        Hook invoked after a leaf node finishes.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                node_id (str): Logical workflow step or composite node identifier.
                record (StepProvenanceRecord): Provenance record emitted when the node completes.
                iteration (int): Retry or resume iteration index for ``node_id``.

        Returns:
                None.
        """
        del ctx, node_id, record, iteration

    def on_run_end(self, ctx: ProvenanceContext, result: WorkflowRunResult) -> None:
        """
        Hook invoked after manifest write with the final run result.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                result (WorkflowRunResult): Final :class:`~tolkien.provenance.runner.WorkflowRunResult` for the workflow run.

        Returns:
                None.
        """
        del ctx, result


class NoOpWorkflowEventHandler(WorkflowEventHandler):
    """Default event handler that performs no side effects."""

    pass


def _entity_refs_to_json(refs: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [
        {
            "entity_id": r.entity_id,
            "entity_type": r.entity_type,
            "role": r.role,
            "uri_or_path": r.uri_or_path,
        }
        for r in refs
    ]


class ProvenanceWorkflowRunner(WorkflowRunner):
    """Depth-first expansion (reverse child push), sink after each leaf, optional checkpoints."""

    def __init__(
        self,
        sink: ProvenanceSink | None = None,
        *,
        checkpoint_store: CheckpointStore | None = None,
        events: WorkflowEventHandler | None = None,
        max_step_attempts: int = 3,
        retry_on_fail: bool = False,
        backoff_seconds: float = 0.0,
        run_type: str = "provenance_workflow",
    ) -> None:
        """
        Configure sink, checkpoints, retries, and lifecycle event hooks.

        Args:
                sink (ProvenanceSink | None): :class:`~tolkien.provenance.sinks.ProvenanceSink` receiving lineage edges after each leaf step. Optional.
                checkpoint_store (CheckpointStore | None): Optional :class:`~tolkien.provenance.checkpoint.CheckpointStore` for resumable runs. Keyword-only.
                events (WorkflowEventHandler | None): Optional :class:`~tolkien.provenance.runner.WorkflowEventHandler` lifecycle hooks. Keyword-only.
                max_step_attempts (int): Maximum execution attempts per leaf step before failure. Keyword-only.
                retry_on_fail (bool): When ``True``, retry leaf steps that return ``StepOutcome.FAIL``. Keyword-only.
                backoff_seconds (float): Sleep duration in seconds between step retries. Keyword-only.
                run_type (str): Workflow category string stored as ``run_type`` in the manifest. Keyword-only.

        Returns:
                None.
        """
        self._sink = sink or NullSink()
        self._checkpoint_store = checkpoint_store
        self._events = events or NoOpWorkflowEventHandler()
        self._max_step_attempts = max(1, max_step_attempts)
        self._retry_on_fail = retry_on_fail
        self._backoff_seconds = backoff_seconds
        self._run_type = run_type

    def run(
        self,
        ctx: ProvenanceContext,
        nodes: Sequence[WorkflowNode],
        *,
        resume: bool = False,
        declare_outputs: list[str] | None = None,
        validation_run_ids: list[str] | None = None,
    ) -> WorkflowRunResult:
        """
        Expand composites on a LIFO stack, flush lineage, write run manifest.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.
                nodes (Sequence[WorkflowNode]): Top-level workflow nodes scheduled by the runner.
                resume (bool): When ``True``, load checkpoints and skip completed node iterations. Keyword-only.
                declare_outputs (list[str] | None): Output path strings recorded in the run manifest. Keyword-only.
                validation_run_ids (list[str] | None): Validation gate run IDs associated with this workflow run. Keyword-only.

        Returns:
                Final :class:`~tolkien.provenance.runner.WorkflowRunResult` for the workflow run.
        """

        stack: list[WorkflowNode] = list(reversed(nodes))
        records: list[StepProvenanceRecord] = []
        workflow_steps: list[dict[str, Any]] = []
        val_ids: list[str] = list(validation_run_ids or [])
        outputs: list[str] = list(declare_outputs or [])
        terminal_status = "completed"
        error_message: str | None = None

        self._events.on_run_start(ctx, nodes)

        while stack:
            node = stack.pop()
            children = node.children
            if children is not None and len(children) > 0:
                for child in reversed(children):
                    stack.append(child)
                continue

            iteration = ctx.iteration_for(node.node_id)
            self._events.on_node_start(ctx, node.node_id, iteration)

            record: StepProvenanceRecord | None = None
            if resume and self._checkpoint_store:
                loaded = self._checkpoint_store.load(ctx.run_id, node.node_id, iteration)
                if loaded is not None:
                    summary = dict(loaded.get("summary", {}))
                    summary.setdefault("resumed_from_checkpoint", True)
                    used_raw = loaded.get("used_entities") or []
                    gen_raw = loaded.get("generated_entities") or []
                    record = StepProvenanceRecord(
                        outcome=StepOutcome.SUCCESS,
                        summary=summary,
                        used_entities=tuple(
                            ProvenanceEntityRef(**u) if isinstance(u, dict) else u for u in used_raw
                        ),
                        generated_entities=tuple(
                            ProvenanceEntityRef(**g) if isinstance(g, dict) else g for g in gen_raw
                        ),
                    )

            if record is None:
                attempt = 0
                while attempt < self._max_step_attempts:
                    attempt += 1
                    record = node.run(ctx)
                    if record.outcome == StepOutcome.RETRY_STEP and attempt < self._max_step_attempts:
                        time.sleep(self._backoff_seconds)
                        continue
                    if record.outcome == StepOutcome.FAIL and self._retry_on_fail and attempt < self._max_step_attempts:
                        time.sleep(self._backoff_seconds)
                        continue
                    break

            assert record is not None

            if record.outcome == StepOutcome.RETRY_STEP:
                record = StepProvenanceRecord(
                    outcome=StepOutcome.FAIL,
                    summary={**record.summary, "reason": "max_retries_exceeded"},
                    used_entities=record.used_entities,
                    generated_entities=record.generated_entities,
                    edges=record.edges,
                )

            workflow_steps.append(
                {
                    "id": node.node_id,
                    "outcome": record.outcome.value,
                    "iteration": iteration,
                }
            )
            records.append(record)

            vid = record.summary.get("validation_run_id")
            if isinstance(vid, str) and vid not in val_ids:
                val_ids.append(vid)

            for ref in record.generated_entities:
                if ref.uri_or_path and ref.uri_or_path not in outputs:
                    outputs.append(ref.uri_or_path)

            if record.edges:
                self._sink.append_edges(record.edges)

            checkpoint_after = getattr(node, "checkpoint_after", False)
            if (
                record.outcome == StepOutcome.SUCCESS
                and checkpoint_after
                and self._checkpoint_store
            ):
                self._checkpoint_store.save(
                    ctx.run_id,
                    node.node_id,
                    iteration,
                    {
                        "summary": record.summary,
                        "used_entities": _entity_refs_to_json(record.used_entities),
                        "generated_entities": _entity_refs_to_json(record.generated_entities),
                    },
                )

            self._events.on_node_complete(ctx, node.node_id, record, iteration)

            if record.outcome == StepOutcome.STOP_WORKFLOW:
                terminal_status = "stopped"
                break
            if record.outcome == StepOutcome.FAIL:
                terminal_status = "failed"
                error_message = record.summary.get("reason", "step_failed")
                if not isinstance(error_message, str):
                    error_message = "step_failed"
                break

        paths = DatastorePaths(ctx.repo_root)
        manifest = run_manifest.build_manifest(
            paths=paths,
            run_type=self._run_type,
            status=terminal_status,
            parameters={"workflow_name": ctx.workflow_name},
            input_files=[],
            outputs=outputs,
            validation_run_ids=val_ids,
            run_id=ctx.run_id,
        )
        manifest["workflow_steps"] = workflow_steps
        manifest_path = run_manifest.write_manifest(paths, manifest)

        result = WorkflowRunResult(
            run_id=ctx.run_id,
            status=terminal_status,
            manifest_path=manifest_path,
            step_records=tuple(records),
            parameters=manifest.get("parameters", {}),
            error_message=error_message,
        )
        self._events.on_run_end(ctx, result)
        return result
