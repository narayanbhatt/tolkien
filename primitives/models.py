"""Concrete dataclass models for primitive platform objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from tolkien._util.time import utc_now
from tolkien.primitives.abc import EntityBase, EventBase, ObservationBase, RelationBase


def required_errors(record: dict[str, Any], required: list[str]) -> list[str]:
    """
    Return validation messages for missing required fields.

    Args:
            record (dict[str, Any]): Row or object dict being validated or flattened.
            required (list[str]): Required field names that must be non-empty.

    Returns:
        List of validation error messages; empty when valid.
    """

    return [f"{field_name} is required" for field_name in required if record.get(field_name) in (None, "")]


@dataclass
class Entity(EntityBase):
    """Identifiable platform object (patient, study, artifact entity, etc.)."""

    entity_id: str
    entity_type: str
    source_system: str
    version: str = "1"
    status: str = "active"
    name: str = ""
    source_id: str = ""
    created_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "primitive_mapper"
    source_version: str = "v1"
    ingested_at: str = field(default_factory=utc_now)
    record_version: int = 1
    is_active: bool = True

    def object_id(self) -> str:
        """
        Return the stable object identifier.
        
        Returns:
            Stable object identifier string for the primitive.
        """
        return self.entity_id

    def validate(self) -> list[str]:
        """
        Return object-level validation errors.
        
        Returns:
            List of validation error messages; empty when valid.
        """
        return required_errors(asdict(self), ["entity_id", "entity_type", "source_system", "version", "status"])

    def as_dict(self) -> dict[str, object]:
        """
        Return a storage-neutral canonical record.
        
        Returns:
            Storage-neutral dict representation of the dataclass.
        """
        return asdict(self)


@dataclass
class Event(EventBase):
    """Time-anchored occurrence linked to a subject entity."""

    event_id: str
    event_type: str
    subject_entity_id: str
    source_system: str
    status: str = "active"
    time_anchor: str = ""
    time_offset: float | None = None
    time_unit: str = ""
    started_at: str = ""
    ended_at: str = ""
    source_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "primitive_mapper"
    source_version: str = "v1"
    ingested_at: str = field(default_factory=utc_now)
    record_version: int = 1
    is_active: bool = True

    def object_id(self) -> str:
        """
        Return the stable object identifier.
        
        Returns:
            Stable object identifier string for the primitive.
        """
        return self.event_id

    def validate(self) -> list[str]:
        """
        Return object-level validation errors.
        
        Returns:
            List of validation error messages; empty when valid.
        """
        return required_errors(asdict(self), ["event_id", "event_type", "subject_entity_id", "source_system", "status"])

    def as_dict(self) -> dict[str, object]:
        """
        Return a storage-neutral canonical record.
        
        Returns:
            Storage-neutral dict representation of the dataclass.
        """
        return asdict(self)


@dataclass
class Observation(ObservationBase):
    """Queryable fact, measurement, label, or reference."""

    observation_id: str
    observation_type: str
    subject_entity_id: str
    code_system: str
    code: str
    value_type: str
    source_system: str
    status: str = "active"
    event_id: str = ""
    value_text: str = ""
    value_number: float | None = None
    value_boolean: bool | None = None
    value_unit: str = ""
    method: str = ""
    source_id: str = ""
    confidence: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "primitive_mapper"
    source_version: str = "v1"
    ingested_at: str = field(default_factory=utc_now)
    record_version: int = 1
    is_active: bool = True

    def object_id(self) -> str:
        """
        Return the stable object identifier.
        
        Returns:
            Stable object identifier string for the primitive.
        """
        return self.observation_id

    def validate(self) -> list[str]:
        """
        Return object-level validation errors.
        
        Returns:
            List of validation error messages; empty when valid.
        """
        errors = required_errors(
            asdict(self),
            ["observation_id", "observation_type", "subject_entity_id", "code_system", "code", "value_type", "source_system", "status"],
        )
        if self.value_type == "number" and self.value_number is None:
            errors.append("value_number is required when value_type is number")
        if self.value_type in {"text", "entity_ref", "artifact_ref", "json"} and not self.value_text:
            errors.append(f"value_text is required when value_type is {self.value_type}")
        if self.value_type == "boolean" and self.value_boolean is None:
            errors.append("value_boolean is required when value_type is boolean")
        return errors

    def as_dict(self) -> dict[str, object]:
        """
        Return a storage-neutral canonical record.
        
        Returns:
            Storage-neutral dict representation of the dataclass.
        """
        return asdict(self)


@dataclass
class Relation(RelationBase):
    """Typed link between two primitive objects."""

    relation_id: str
    relation_type: str
    source_object_type: str
    source_object_id: str
    target_object_type: str
    target_object_id: str
    source_system: str
    status: str = "active"
    source_role: str = ""
    target_role: str = ""
    valid_from: str = ""
    valid_to: str = ""
    created_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "primitive_mapper"
    source_version: str = "v1"
    ingested_at: str = field(default_factory=utc_now)
    record_version: int = 1
    is_active: bool = True

    def object_id(self) -> str:
        """
        Return the stable object identifier.
        
        Returns:
            Stable object identifier string for the primitive.
        """
        return self.relation_id

    def validate(self) -> list[str]:
        """
        Return object-level validation errors.
        
        Returns:
            List of validation error messages; empty when valid.
        """
        return required_errors(
            asdict(self),
            ["relation_id", "relation_type", "source_object_type", "source_object_id", "target_object_type", "target_object_id", "source_system", "status"],
        )

    def as_dict(self) -> dict[str, object]:
        """
        Return a storage-neutral canonical record.
        
        Returns:
            Storage-neutral dict representation of the dataclass.
        """
        return asdict(self)
