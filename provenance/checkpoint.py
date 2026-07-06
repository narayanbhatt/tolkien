"""Checkpoint persistence for resumable workflow nodes."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class CheckpointStore(ABC):
    """Persistence for resumable per-node workflow state."""

    @abstractmethod
    def save(
        self,
        run_id: str,
        node_id: str,
        iteration: int,
        state: dict[str, Any],
    ) -> Path:
        """
        Persist checkpoint state and return the written path.

        Args:
                run_id (str): Workflow run identifier (often ``GENFEAT_RUN_ID``).
                node_id (str): Logical workflow step or composite node identifier.
                iteration (int): Retry or resume iteration index for ``node_id``.
                state (dict[str, Any]): JSON-serializable checkpoint payload for a workflow node.

        Returns:
            ``Path`` instance.
        """

        raise NotImplementedError

    @abstractmethod
    def load(self, run_id: str, node_id: str, iteration: int) -> dict[str, Any] | None:
        """
        Load checkpoint state, or None when absent.

        Args:
                run_id (str): Workflow run identifier (often ``GENFEAT_RUN_ID``).
                node_id (str): Logical workflow step or composite node identifier.
                iteration (int): Retry or resume iteration index for ``node_id``.

        Returns:
                Checkpoint state dict, or ``None`` when absent.
        """

        raise NotImplementedError


class JsonCheckpointStore(CheckpointStore):
    """``data/artifacts/index/checkpoints/{run_id}/{node_id}[_iter{k}].json``."""

    def __init__(self, repo_root: Path) -> None:
        """
        Configure checkpoint root under ``data/artifacts/index/checkpoints/``.
        
        Args:
        repo_root (Path): Repository root; relative paths resolve against this directory.
        
        Returns:
        None.
        """
        self._root = repo_root / "data" / "artifacts" / "index" / "checkpoints"

    def _path_for(self, run_id: str, node_id: str, iteration: int) -> Path:
        suffix = "" if iteration == 0 else f"_iter{iteration}"
        return self._root / run_id / f"{node_id}{suffix}.json"

    def save(
        self,
        run_id: str,
        node_id: str,
        iteration: int,
        state: dict[str, Any],
    ) -> Path:
        """
        Write JSON checkpoint under ``data/artifacts/index/checkpoints/``.

        Args:
                run_id (str): Workflow run identifier (often ``GENFEAT_RUN_ID``).
                node_id (str): Logical workflow step or composite node identifier.
                iteration (int): Retry or resume iteration index for ``node_id``.
                state (dict[str, Any]): JSON-serializable checkpoint payload for a workflow node.

        Returns:
            ``Path`` instance.
        """

        path = self._path_for(run_id, node_id, iteration)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_id": run_id, "node_id": node_id, "iteration": iteration, **state}
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return path

    def load(self, run_id: str, node_id: str, iteration: int) -> dict[str, Any] | None:
        """
        Load JSON checkpoint when the file exists.

        Args:
                run_id (str): Workflow run identifier (often ``GENFEAT_RUN_ID``).
                node_id (str): Logical workflow step or composite node identifier.
                iteration (int): Retry or resume iteration index for ``node_id``.

        Returns:
                Checkpoint state dict, or ``None`` when absent.
        """

        path = self._path_for(run_id, node_id, iteration)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def clear(self, run_id: str, node_id: str, iteration: int) -> None:
        """
        Delete checkpoint file for the given node iteration.

        Args:
                run_id (str): Workflow run identifier (often ``GENFEAT_RUN_ID``).
                node_id (str): Logical workflow step or composite node identifier.
                iteration (int): Retry or resume iteration index for ``node_id``.

        Returns:
                None.
        """

        path = self._path_for(run_id, node_id, iteration)
        if path.exists():
            path.unlink()
