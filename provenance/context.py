"""Run-scoped provenance context and agent metadata."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tolkien.registry.run_manifest import git_commit


@dataclass(frozen=True)
class ProvenanceAgent:
    """Software or human agent attributed to workflow activities."""

    agent_type: str
    agent_id: str
    source_name: str = "tolkien"
    source_version: str = "v1"


@dataclass(frozen=True)
class ProvenanceContext:
    """Immutable handle passed to every provenanced step for one workflow run."""

    run_id: str
    repo_root: Path
    workflow_name: str
    code_ref: str
    agent_default: ProvenanceAgent
    plan_uri: str | None = None
    _iterations: dict[str, int] = field(default_factory=dict, repr=False)
    _slots: dict[str, Any] = field(default_factory=dict, repr=False)

    def iteration_for(self, node_id: str) -> int:
        """
        Return retry iteration count for ``node_id`` (default 0).

        Args:
                node_id (str): Logical workflow step or composite node identifier.

        Returns:
                Current retry iteration counter for ``node_id`` (default ``0``).
        """

        return self._iterations.get(node_id, 0)

    def with_iteration(self, node_id: str, value: int) -> ProvenanceContext:
        """
        Return a copy with updated iteration counter for ``node_id``.

        Args:
                node_id (str): Logical workflow step or composite node identifier.
                value (int): Cell value to match, or slot value to store.

        Returns:
                New context copy with updated iteration counter for ``node_id``.
        """

        next_iters = dict(self._iterations)
        next_iters[node_id] = value
        return ProvenanceContext(
            run_id=self.run_id,
            repo_root=self.repo_root,
            workflow_name=self.workflow_name,
            code_ref=self.code_ref,
            agent_default=self.agent_default,
            plan_uri=self.plan_uri,
            _iterations=next_iters,
            _slots=dict(self._slots),
        )

    def get_slot(self, key: str, default: Any = None) -> Any:
        """
        Read an arbitrary per-run slot value.

        Args:
                key (str): Column name or per-run context slot key.
                default (Any): Value returned when a context slot key is absent. Optional.

        Returns:
                Stored per-run slot value, or ``default`` when absent.
        """

        return self._slots.get(key, default)

    def with_slot(self, key: str, value: Any) -> ProvenanceContext:
        """
        Return a copy with an updated per-run slot.

        Args:
                key (str): Column name or per-run context slot key.
                value (Any): Cell value to match, or slot value to store.

        Returns:
                New context copy with updated per-run slot value.
        """

        next_slots = dict(self._slots)
        next_slots[key] = value
        return ProvenanceContext(
            run_id=self.run_id,
            repo_root=self.repo_root,
            workflow_name=self.workflow_name,
            code_ref=self.code_ref,
            agent_default=self.agent_default,
            plan_uri=self.plan_uri,
            _iterations=dict(self._iterations),
            _slots=next_slots,
        )


def provenance_context_from_env(
    repo_root: Path | None = None,
    *,
    workflow_name: str = "local_workflow",
    run_id: str | None = None,
    plan_uri: str | None = None,
    agent_default: ProvenanceAgent | None = None,
) -> ProvenanceContext:
    """
    Build run context from env (``GENFEAT_RUN_ID``) and repo root.

    Args:
            repo_root (Path | None): Repository root; relative paths resolve against this directory. Optional.
            workflow_name (str): Human-readable workflow name stored in context and manifest metadata. Keyword-only.
            run_id (str | None): Workflow run identifier (often ``GENFEAT_RUN_ID``). Keyword-only.
            plan_uri (str | None): Optional URI referencing an external experiment plan document. Keyword-only.
            agent_default (ProvenanceAgent | None): Default :class:`~tolkien.provenance.context.ProvenanceAgent` attributed to activities. Keyword-only.

    Returns:
            Immutable :class:`~tolkien.provenance.context.ProvenanceContext` for the run.
    """

    root = repo_root or Path.cwd()
    rid = run_id or os.environ.get("GENFEAT_RUN_ID") or f"run_{uuid.uuid4().hex[:12]}"
    agent = agent_default or ProvenanceAgent(agent_type="pipeline", agent_id=workflow_name)
    return ProvenanceContext(
        run_id=rid,
        repo_root=root.resolve(),
        workflow_name=workflow_name,
        code_ref=git_commit(root),
        agent_default=agent,
        plan_uri=plan_uri,
    )
