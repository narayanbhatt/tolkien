"""Abstract provenanced steps, records, and composite helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

from tolkien.lineage.lineage import LineageEdge
from tolkien.provenance.context import ProvenanceContext


class StepOutcome(Enum):
    """Terminal or retry disposition for a provenanced workflow step."""

    SUCCESS = "success"
    STOP_WORKFLOW = "stop_workflow"
    FAIL = "fail"
    RETRY_STEP = "retry_step"


@dataclass(frozen=True)
class ProvenanceEntityRef:
    """Lightweight handle to an entity used or produced by a step."""

    entity_id: str
    entity_type: str = "artifact"
    role: str = ""
    uri_or_path: str = ""


@dataclass(frozen=True)
class StepProvenanceRecord:
    """Outcome and provenance payload returned by a :class:`ProvenancedStep`."""

    outcome: StepOutcome
    summary: dict[str, Any] = field(default_factory=dict)
    used_entities: tuple[ProvenanceEntityRef, ...] = ()
    generated_entities: tuple[ProvenanceEntityRef, ...] = ()
    edges: tuple[LineageEdge, ...] = ()


@runtime_checkable
class WorkflowNode(Protocol):
    """Anything the runner can schedule (leaf step or composite)."""

    @property
    def node_id(self) -> str:
        """
        Stable identifier used for scheduling and checkpoints.

        Returns:
                Node identifier string.
        """
        ...

    def run(self, ctx: ProvenanceContext) -> StepProvenanceRecord:
        """
        Execute leaf work and return provenance for the runner.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.

        Returns:
            :class:`~tolkien.provenance.step.StepProvenanceRecord` describing step outcome and entities.
        """
        ...

    @property
    def children(self) -> Sequence[WorkflowNode] | None:
        """
        If non-empty sequence, runner expands composite (LIFO) without calling run.

        Returns:
                Child workflow nodes, or ``None`` for leaf steps.
        """
        ...


class ProvenancedStep(ABC):
    """Leaf step: implement run(); optional checkpoint_after."""

    def __init__(self, step_id: str, *, checkpoint_after: bool = False) -> None:
        """
        Bind step identifier and optional post-success checkpoint flag.

        Args:
                step_id (str): Logical provenanced step identifier and manifest step name.
                checkpoint_after (bool): When ``True``, persist a checkpoint after a successful leaf execution. Keyword-only.

        Returns:
                None.
        """
        self.step_id = step_id
        self.checkpoint_after = checkpoint_after

    @property
    def node_id(self) -> str:
        """
        Alias of ``step_id`` for :class:`~tolkien.provenance.step.WorkflowNode`.

        Returns:
                Node identifier string.
        """
        return self.step_id

    @property
    def children(self) -> Sequence[WorkflowNode] | None:
        """
        Leaf steps have no composite children.

        Returns:
            ``None``.
        """
        return None

    @abstractmethod
    def run(self, ctx: ProvenanceContext) -> StepProvenanceRecord:
        """
        Execute work; return declared inputs/outputs and optional edges.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.

        Returns:
            :class:`~tolkien.provenance.step.StepProvenanceRecord` describing step outcome and entities.
        """
        ...


class SequenceStep:
    """Composite: children run in order (runner expands via LIFO stack)."""

    def __init__(self, node_id: str, children: Sequence[WorkflowNode]) -> None:
        """
        Composite node that expands ``children`` instead of executing ``run``.

        Args:
                node_id (str): Logical workflow step or composite node identifier.
                children (Sequence[WorkflowNode]): Child workflow nodes expanded depth-first by the runner.

        Returns:
                None.
        """
        self._node_id = node_id
        self._children = tuple(children)

    @property
    def node_id(self) -> str:
        """
        Composite node identifier.

        Returns:
                Node identifier string.
        """
        return self._node_id

    @property
    def children(self) -> Sequence[WorkflowNode] | None:
        """
        Ordered child nodes pushed onto the runner stack.

        Returns:
                Child workflow nodes for the runner to expand.
        """
        return self._children

    def run(self, ctx: ProvenanceContext) -> StepProvenanceRecord:
        """
        Placeholder; the runner expands children instead of calling this.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.

        Returns:
                Placeholder success record; the runner expands ``children`` instead.
        """
        del ctx
        return StepProvenanceRecord(
            outcome=StepOutcome.SUCCESS,
            summary={"note": "SequenceStep expanded by runner; run() not used."},
        )


class ValidatedStep(ProvenancedStep):
    """Runs inner step then validation step when inner is not FAIL."""

    def __init__(
        self,
        step_id: str,
        inner: ProvenancedStep,
        validation: ProvenancedStep,
        *,
        checkpoint_after: bool = False,
    ) -> None:
        """
        Wrap an inner step with a post-step validation leaf.

        Args:
                step_id (str): Logical provenanced step identifier and manifest step name.
                inner (ProvenancedStep): Inner :class:`~tolkien.provenance.step.ProvenancedStep` executed before validation.
                validation (ProvenancedStep): Validation :class:`~tolkien.provenance.step.ProvenancedStep` executed after inner success.
                checkpoint_after (bool): When ``True``, persist a checkpoint after a successful leaf execution. Keyword-only.

        Returns:
                None.
        """
        super().__init__(step_id, checkpoint_after=checkpoint_after)
        self._inner = inner
        self._validation = validation

    def run(self, ctx: ProvenanceContext) -> StepProvenanceRecord:
        """
        Run inner step, then validation unless inner failed or stopped.

        Args:
                ctx (ProvenanceContext): Run-scoped :class:`~tolkien.provenance.context.ProvenanceContext`.

        Returns:
            :class:`~tolkien.provenance.step.StepProvenanceRecord` merged from inner and validation steps.
        """
        inner_rec = self._inner.run(ctx)
        summary: dict[str, Any] = {"inner": inner_rec.summary}
        used = list(inner_rec.used_entities)
        generated = list(inner_rec.generated_entities)
        edges = list(inner_rec.edges)

        if inner_rec.outcome == StepOutcome.FAIL:
            return StepProvenanceRecord(
                outcome=StepOutcome.FAIL,
                summary=summary,
                used_entities=tuple(used),
                generated_entities=tuple(generated),
                edges=tuple(edges),
            )

        if inner_rec.outcome == StepOutcome.RETRY_STEP:
            return StepProvenanceRecord(
                outcome=StepOutcome.RETRY_STEP,
                summary=summary,
                used_entities=tuple(used),
                generated_entities=tuple(generated),
                edges=tuple(edges),
            )

        if inner_rec.outcome == StepOutcome.STOP_WORKFLOW:
            return StepProvenanceRecord(
                outcome=StepOutcome.STOP_WORKFLOW,
                summary=summary,
                used_entities=tuple(used),
                generated_entities=tuple(generated),
                edges=tuple(edges),
            )

        val_rec = self._validation.run(ctx)
        summary["validation"] = val_rec.summary
        used.extend(val_rec.used_entities)
        generated.extend(val_rec.generated_entities)
        edges.extend(val_rec.edges)

        if val_rec.outcome == StepOutcome.RETRY_STEP:
            return StepProvenanceRecord(
                outcome=StepOutcome.RETRY_STEP,
                summary=summary,
                used_entities=tuple(used),
                generated_entities=tuple(generated),
                edges=tuple(edges),
            )

        if val_rec.outcome == StepOutcome.FAIL:
            return StepProvenanceRecord(
                outcome=StepOutcome.FAIL,
                summary=summary,
                used_entities=tuple(used),
                generated_entities=tuple(generated),
                edges=tuple(edges),
            )

        if val_rec.outcome == StepOutcome.STOP_WORKFLOW:
            return StepProvenanceRecord(
                outcome=StepOutcome.STOP_WORKFLOW,
                summary=summary,
                used_entities=tuple(used),
                generated_entities=tuple(generated),
                edges=tuple(edges),
            )

        return StepProvenanceRecord(
            outcome=StepOutcome.SUCCESS,
            summary=summary,
            used_entities=tuple(used),
            generated_entities=tuple(generated),
            edges=tuple(edges),
        )
