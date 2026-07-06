"""Destination adapters for lineage edges."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from tolkien.lineage.lineage import LineageEdge, append_lineage_edges


class ProvenanceSink(ABC):
    """Destination for lineage edges emitted by provenanced steps."""

    @abstractmethod
    def append_edges(self, edges: Iterable[LineageEdge]) -> None:
        """
        Persist or forward lineage edges.

        Args:
                edges (Iterable[LineageEdge]): Lineage edges to append or forward.

        Returns:
                None.
        """

        raise NotImplementedError


class NullSink(ProvenanceSink):
    """Discard lineage edges (default runner sink)."""

    def append_edges(self, edges: Iterable[LineageEdge]) -> None:
        """
        Discard lineage edges without persisting them.
        
        Args:
        edges (Iterable[LineageEdge]): Lineage edges to append or forward.
        
        Returns:
        None.
        """
        _ = tuple(edges)


class CsvLineageSink(ProvenanceSink):
    """Append edges to ``lineage_edges.csv`` via :func:`~tolkien.lineage.append_lineage_edges`."""

    def __init__(self, csv_path: Path) -> None:
        """
        Append emitted edges to the given ``lineage_edges.csv`` path.
        
        Args:
        csv_path (Path): CSV file path; parent directories are created on write when needed.
        
        Returns:
        None.
        """
        self._csv_path = csv_path

    def append_edges(self, edges: Iterable[LineageEdge]) -> None:
        """
        Append materialized edges via :func:`~tolkien.lineage.append_lineage_edges`.
        
        Args:
        edges (Iterable[LineageEdge]): Lineage edges to append or forward.
        
        Returns:
        None.
        """
        materialized = list(edges)
        if materialized:
            append_lineage_edges(self._csv_path, materialized)
