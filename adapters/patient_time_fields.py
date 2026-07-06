"""Shared CSV column contracts for patient_events and modality_observations tables.

These field lists are the canonical headers expected by adapters and master-table
contracts when writing patient-time spine rows.
"""

PATIENT_EVENT_FIELDS = [
    "event_uid",
    "patient_uid",
    "study_uid",
    "event_type",
    "event_label",
    "event_time_anchor",
    "time_offset_days",
    "time_offset_unit",
    "source_system",
    "source_event_id",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]

MODALITY_OBSERVATION_FIELDS = [
    "observation_uid",
    "event_uid",
    "patient_uid",
    "file_uid",
    "modality_family",
    "modality",
    "observation_code",
    "observation_label",
    "value_text",
    "value_numeric",
    "value_unit",
    "value_json",
    "source_system",
    "source_observation_id",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]
