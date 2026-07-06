"""Structured clinical CSV adapter for the second modality path.

Expected input columns:
- patient_uid
- event_type
- observation_code

Optional columns include study_uid, event_label, event_time_anchor,
time_offset_days, observation_label, value_text, value_numeric, value_unit,
source_system, source_event_id, and source_observation_id.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tolkien.adapters.base import AdapterResult, BaseAdapter
from tolkien.adapters.patient_time_fields import (
    MODALITY_OBSERVATION_FIELDS,
    PATIENT_EVENT_FIELDS,
)


class ClinicalCsvAdapter(BaseAdapter):
    """Map structured clinical CSV rows to patient-time canonical tables."""

    adapter_name = "clinical_csv"

    def adapt(self, input_csv: Path) -> AdapterResult:
        """
        Read clinical CSV and emit ``patient_events`` + ``modality_observations`` rows.

        Args:
                input_csv (Path): Source-native CSV path consumed by an adapter.

        Returns:
            :class:`~tolkien.adapters.base.AdapterResult` grouped by target master table.
        """

        source_rows = self.read_csv(input_csv)
        self.require_columns(source_rows, {"patient_uid", "event_type", "observation_code"}, input_csv.name)

        events = []
        observations = []
        for row in source_rows:
            source_system = row.get("source_system") or self.source_name
            source_event_id = row.get("source_event_id") or self.stable_uid(
                "src_evt",
                row["patient_uid"],
                row.get("study_uid", ""),
                row["event_type"],
                row.get("time_offset_days", ""),
            )
            event_uid = self.stable_uid("evt", source_system, source_event_id)

            events.append(
                {
                    "event_uid": event_uid,
                    "patient_uid": row["patient_uid"],
                    "study_uid": row.get("study_uid", ""),
                    "event_type": row["event_type"],
                    "event_label": row.get("event_label", ""),
                    "event_time_anchor": row.get("event_time_anchor") or "index",
                    "time_offset_days": row.get("time_offset_days", ""),
                    "time_offset_unit": row.get("time_offset_unit") or "days",
                    "source_system": source_system,
                    "source_event_id": source_event_id,
                    **self.lifecycle_fields(),
                }
            )

            source_observation_id = row.get("source_observation_id") or self.stable_uid(
                "src_obs",
                source_event_id,
                row["observation_code"],
                row.get("value_text", ""),
                row.get("value_numeric", ""),
            )
            observations.append(
                {
                    "observation_uid": self.stable_uid("obs", source_system, source_observation_id),
                    "event_uid": event_uid,
                    "patient_uid": row["patient_uid"],
                    "file_uid": row.get("file_uid", ""),
                    "modality_family": "clinical_table",
                    "modality": row.get("modality", "clinical"),
                    "observation_code": row["observation_code"],
                    "observation_label": row.get("observation_label", ""),
                    "value_text": row.get("value_text", ""),
                    "value_numeric": row.get("value_numeric", ""),
                    "value_unit": row.get("value_unit", ""),
                    "value_json": row.get("value_json", ""),
                    "source_system": source_system,
                    "source_observation_id": source_observation_id,
                    **self.lifecycle_fields(),
                }
            )

        result = AdapterResult()
        result.add_rows("patient_events", events)
        result.add_rows("modality_observations", observations)
        return result


def main() -> None:
    """
    CLI: convert a clinical CSV into staging patient-time tables.
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description="Convert a structured clinical CSV into canonical rows.")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/staging/clinical_csv_adapter"))
    parser.add_argument("--source-name", default="clinical_csv_adapter")
    parser.add_argument("--source-version", default="v1")
    parser.add_argument("--write", action="store_true", help="Write staging CSV outputs.")
    args = parser.parse_args()

    adapter = ClinicalCsvAdapter(args.source_name, args.source_version)
    result = adapter.adapt(args.input_csv)

    if args.write:
        adapter.write_csv(args.output_dir / "patient_events.csv", result.rows_by_table["patient_events"], PATIENT_EVENT_FIELDS)
        adapter.write_csv(
            args.output_dir / "modality_observations.csv",
            result.rows_by_table["modality_observations"],
            MODALITY_OBSERVATION_FIELDS,
        )

    summary = {table: len(rows) for table, rows in result.rows_by_table.items()}
    print(json.dumps({"summary": summary, "output_dir": str(args.output_dir)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
