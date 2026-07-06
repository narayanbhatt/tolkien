"""Abstract base classes for first-class primitive platform objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class PrimitiveObject(ABC):
    """Storage-neutral base abstraction for all primitive objects."""

    object_kind: ClassVar[str]

    @abstractmethod
    def object_id(self) -> str:
        """
        Return the stable object identifier.
        
        Returns:
        Stable object identifier string for the primitive.
        """

    @abstractmethod
    def validate(self) -> list[str]:
        """
        Return object-level validation errors.
        
        Returns:
        List of validation error messages; empty when valid.
        """

    @abstractmethod
    def as_dict(self) -> dict[str, object]:
        """
        Return a storage-neutral canonical record.
        
        Returns:
        Storage-neutral dict representation of the dataclass.
        """

    def log(self, registry: object) -> dict[str, int]:
        """
        Append this object to master primitive tables via ``DatastoreRegistry``.

        Args:
                registry (object): :class:`~tolkien.registry.datastore_registry.DatastoreRegistry` used for catalog writes.

        Returns:
                Mapping of primitive table names to appended row counts.
        """

        from tolkien.registry.datastore_registry import DatastoreRegistry

        if not isinstance(registry, DatastoreRegistry):
            raise TypeError(f"expected DatastoreRegistry, got {type(registry).__name__}")
        return registry.append_primitives([self])


class EntityBase(PrimitiveObject):
    """Primitive kind: entity."""

    object_kind = "entity"


class EventBase(PrimitiveObject):
    """Primitive kind: event."""

    object_kind = "event"


class ObservationBase(PrimitiveObject):
    """Primitive kind: observation."""

    object_kind = "observation"


class RelationBase(PrimitiveObject):
    """Primitive kind: relation."""

    object_kind = "relation"
