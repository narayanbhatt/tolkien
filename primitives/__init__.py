"""First-class primitive objects: Entity, Event, Observation, Relation.

Primitives are storage-neutral dataclasses with ``validate()``, ``as_dict()``, and
optional ``log(registry)`` for CSV persistence via :class:`~tolkien.registry.DatastoreRegistry`.
"""

__all__: list[str] = []
