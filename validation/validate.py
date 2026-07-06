"""Executable validation gates for canonical multimodal metadata tables."""

from __future__ import annotations

import argparse
import csv
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ModuleNotFoundError:  # Keep the validator usable in bare Python installs.
    yaml = None

from tolkien._util.time import utc_now
from tolkien.registry.layout import DatastorePaths
from tolkien.registry.master_table_reader import MasterTableReader, is_active_row


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class CheckResult:
    """Outcome of one schema validation check."""

    check_id: str
    table_name: str
    severity: str
    failure_count: int
    sample_rows: list[dict[str, str]] = field(default_factory=list)
    description: str = ""

    @property
    def passed(self) -> bool:
        """
        True when ``failure_count`` is zero.
        
        Returns:
        ``True`` when ``failure_count == 0``.
        """

        return self.failure_count == 0


def parse_project_yaml(path: Path, text: str) -> dict:
    """
    Parse the small YAML subset used by this repository's schema files.

    Args:
            path (Path): Filesystem path to read, write, or fingerprint.
            text (str): Raw YAML text to parse when PyYAML is unavailable.

    Returns:
            Parsed mapping for supported schema YAML subsets.
    """

    if path.name in {"enums.yaml", "primitive_enums.yaml"}:
        parsed: dict[str, list[str]] = {}
        current_key = ""
        for line in text.splitlines():
            if line and not line.startswith(" ") and line.endswith(":"):
                current_key = line[:-1]
                parsed[current_key] = []
            elif current_key and line.strip().startswith("- "):
                parsed[current_key].append(line.strip()[2:])
        return parsed

    if path.name == "validation_checks.yaml":
        checks = []
        current: dict[str, str] | None = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                if current:
                    checks.append(current)
                current = {"id": stripped.split(":", 1)[1].strip()}
            elif current is not None and stripped.startswith("level:"):
                current["level"] = stripped.split(":", 1)[1].strip()
            elif current is not None and stripped.startswith("description:"):
                current["description"] = stripped.split(":", 1)[1].strip()
        if current:
            checks.append(current)
        return {"checks": checks}

    if path.name == "master_table_contracts.yaml":
        tables: dict[str, dict[str, object]] = {}
        in_tables = False
        current_table = ""
        current_column: dict[str, object] | None = None

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped == "tables:":
                in_tables = True
                continue
            if not in_tables:
                continue

            table_match = re.match(r"^  ([A-Za-z0-9_]+):$", line)
            if table_match:
                if current_table and current_column:
                    tables[current_table].setdefault("columns", []).append(current_column)
                    current_column = None
                current_table = table_match.group(1)
                tables[current_table] = {"columns": []}
                continue

            if not current_table:
                continue

            if stripped.startswith("primary_key:"):
                tables[current_table]["primary_key"] = stripped.split(":", 1)[1].strip()
                continue

            inline_column = re.search(r"\{\s*name:\s*([^,}]+).*required:\s*(true|false)", stripped)
            if inline_column:
                tables[current_table].setdefault("columns", []).append(
                    {
                        "name": inline_column.group(1).strip(),
                        "required": inline_column.group(2) == "true",
                    }
                )
                continue

            if stripped.startswith("- name:"):
                if current_column:
                    tables[current_table].setdefault("columns", []).append(current_column)
                current_column = {"name": stripped.split(":", 1)[1].strip(), "required": False}
                continue

            if current_column is not None and stripped.startswith("required:"):
                current_column["required"] = stripped.split(":", 1)[1].strip() == "true"

        if current_table and current_column:
            tables[current_table].setdefault("columns", []).append(current_column)
        return {"tables": tables}

    return {}


def load_yaml(path: Path) -> dict:
    """
    Load YAML schema file (PyYAML when available, else minimal parser).

    Args:
            path (Path): Filesystem path to read, write, or fingerprint.

    Returns:
            Parsed YAML mapping (PyYAML when available).
    """

    with path.open("r", encoding="utf-8") as handle:
        text = handle.read()
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return parse_project_yaml(path, text)


def read_table(reader: MasterTableReader, table_name: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    Return column headers and rows for a master table (empty when missing).

    Args:
            reader (MasterTableReader): :class:`~tolkien.registry.master_table_reader.MasterTableReader` for master CSV reads.
            table_name (str): Master CSV table stem under validation or adapter output grouping.

    Returns:
            All rows from ``data/master/csv/{stem}.csv`` (empty when missing).
    """

    rows = reader.read_table(table_name)
    if not rows:
        return [], []
    return list(rows[0].keys()), rows


def active_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """
    Filter to rows where :func:`is_active_row` is true.

    Args:
            rows (Iterable[dict[str, str]]): Table rows represented as string-keyed dicts.

    Returns:
            Rows where :func:`~tolkien.registry.master_table_reader.is_active_row` is true.
    """

    return [row for row in rows if is_active_row(row)]


def result(
    check_id: str,
    table_name: str,
    severity: str,
    failures: list[dict[str, str]],
    description: str,
) -> CheckResult:
    """
    Build a :class:`CheckResult` from failure rows and metadata.

    Args:
            check_id (str): Validation check identifier from ``validation_checks.yaml``.
            table_name (str): Master CSV table stem under validation or adapter output grouping.
            severity (str): Check severity level (for example ``error`` or ``warning``).
            failures (list[dict[str, str]]): Rows or records that violated the check.
            description (str): Human-readable check description from the validation spec.

    Returns:
            Constructed :class:`~tolkien.validation.validate.CheckResult`.
    """

    return CheckResult(
        check_id=check_id,
        table_name=table_name,
        severity=severity,
        failure_count=len(failures),
        sample_rows=failures[:10],
        description=description,
    )


class Validator:
    """Run contract checks against master CSV mirrors under ``data/master/csv``."""

    def __init__(self, repo_root: Path) -> None:
        """
        Load schema contracts and validation specs for ``repo_root``.
        
        Args:
        repo_root (Path): Repository root; relative paths resolve against this directory.
        
        Returns:
        None.
        """
        self.paths = DatastorePaths(repo_root.resolve())
        self.repo_root = self.paths.repo_root
        self.schema_root = self.paths.schema_root
        self.reader = MasterTableReader(self.paths)
        self.csv_root = self.paths.master_csv
        self.contracts = load_yaml(self.schema_root / "master_table_contracts.yaml")
        self.validation_spec = load_yaml(self.schema_root / "validation_checks.yaml")
        self.enums = load_yaml(self.schema_root / "enums.yaml")
        self.primitive_enums = load_yaml(self.schema_root / "primitive_enums.yaml")
        self.tables: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    def table(self, table_name: str) -> tuple[list[str], list[dict[str, str]]]:
        """
        Cached read of headers and rows for a master table.

        Args:
                table_name (str): Master CSV table stem under validation or adapter output grouping.

        Returns:
                Cached ``(headers, rows)`` tuple for a master table.
        """

        if table_name not in self.tables:
            self.tables[table_name] = read_table(self.reader, table_name)
        return self.tables[table_name]

    def severity(self, check_id: str) -> tuple[str, str]:
        """
        Look up check severity level and description from validation spec.

        Args:
                check_id (str): Validation check identifier from ``validation_checks.yaml``.

        Returns:
                Tuple of ``(level, description)`` from the validation spec.
        """

        for check in self.validation_spec.get("checks", []):
            if check["id"] == check_id:
                return check["level"], check.get("description", "")
        return "error", ""

    def required_columns_present(self) -> list[CheckResult]:
        """
        Verify required columns exist per table contract.
        
        Returns:
        One :class:`~tolkien.validation.validate.CheckResult` per table checked.
        """
        severity, description = self.severity("required_columns_present")
        checks = []
        for table_name, contract in self.contracts.get("tables", {}).items():
            headers, _ = self.table(table_name)
            required = [column["name"] for column in contract.get("columns", []) if column.get("required")]
            missing = [{"missing_column": column} for column in required if column not in headers]
            checks.append(result("required_columns_present", table_name, severity, missing, description))
        return checks

    def primary_key_not_null(self) -> list[CheckResult]:
        """
        Ensure active primary key columns are non-null.
        
        Returns:
        One :class:`~tolkien.validation.validate.CheckResult` per table checked.
        """
        severity, description = self.severity("primary_key_not_null")
        checks = []
        for table_name, contract in self.contracts.get("tables", {}).items():
            pk = contract.get("primary_key")
            _, rows = self.table(table_name)
            failures = [row for row in active_rows(rows) if pk and not row.get(pk)]
            checks.append(result("primary_key_not_null", table_name, severity, failures, description))
        return checks

    def primary_key_unique(self) -> list[CheckResult]:
        """
        Ensure active primary keys are unique within each table.
        
        Returns:
        One :class:`~tolkien.validation.validate.CheckResult` per table checked.
        """
        severity, description = self.severity("primary_key_unique")
        checks = []
        for table_name, contract in self.contracts.get("tables", {}).items():
            pk = contract.get("primary_key")
            _, rows = self.table(table_name)
            seen: set[str] = set()
            failures = []
            for row in active_rows(rows):
                value = row.get(pk, "") if pk else ""
                if value in seen:
                    failures.append(row)
                seen.add(value)
            checks.append(result("primary_key_unique", table_name, severity, failures, description))
        return checks

    def fk_check(self, check_id: str, table_name: str, column: str, ref_table: str, ref_column: str, allow_empty: bool = False) -> CheckResult:
        """
        Verify foreign key column values resolve in the reference table.

        Args:
                check_id (str): Validation check identifier from ``validation_checks.yaml``.
                table_name (str): Master CSV table stem under validation or adapter output grouping.
                column (str): Foreign-key column name in the child table.
                ref_table (str): Referenced master table stem for foreign-key validation.
                ref_column (str): Referenced column name in ``ref_table``.
                allow_empty (bool): When ``True``, treat empty child foreign-key values as valid. Optional.

        Returns:
            ``CheckResult`` instance.
        """
        severity, description = self.severity(check_id)
        _, rows = self.table(table_name)
        _, ref_rows = self.table(ref_table)
        ref_values = {row.get(ref_column, "") for row in active_rows(ref_rows)}
        failures = []
        for row in active_rows(rows):
            value = row.get(column, "")
            if allow_empty and not value:
                continue
            if value not in ref_values:
                failures.append(row)
        return result(check_id, table_name, severity, failures, description)

    def crosswalk_conflict_free(self) -> CheckResult:
        """
        Detect conflicting crosswalk mappings for the same source id.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("crosswalk_conflict_free")
        _, rows = self.table("id_crosswalk")
        source_to_patient: dict[tuple[str, str], str] = {}
        failures = []
        for row in active_rows(rows):
            for key_column in ("source_subject_id", "source_study_id"):
                source_id = row.get(key_column, "")
                if not source_id:
                    continue
                key = (row.get("source_system", ""), source_id)
                patient_uid = row.get("patient_uid", "")
                if key in source_to_patient and source_to_patient[key] != patient_uid:
                    failures.append(row)
                source_to_patient[key] = patient_uid
        return result("crosswalk_conflict_free", "id_crosswalk", severity, failures, description)

    def relative_paths_only(self) -> CheckResult:
        """
        Ensure path fields are repository-relative, not absolute.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("relative_paths_only")
        failures = []
        for table_name in self.contracts.get("tables", {}):
            _, rows = self.table(table_name)
            for row in active_rows(rows):
                for key, value in row.items():
                    if key.endswith("path") or key.endswith("path_rel") or key == "path_rel":
                        path_value = value or ""
                        if path_value and Path(path_value).is_absolute():
                            failures.append({"table": table_name, "column": key, "value": path_value})
        return result("relative_paths_only", "path_columns", severity, failures, description)

    def path_exists_for_registries(self) -> CheckResult:
        """
        Verify registry path fields resolve on disk.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("path_exists_for_registries")
        failures = []
        for table_name in ("artifact_registry", "image_registry"):
            _, rows = self.table(table_name)
            for row in active_rows(rows):
                path_rel = row.get("path_rel", "")
                if path_rel and not (self.repo_root / path_rel).exists():
                    failures.append({"table": table_name, "path_rel": path_rel})
        return result("path_exists_for_registries", "registries", severity, failures, description)

    def checksum_valid_format(self) -> CheckResult:
        """
        Validate sha256 fields match expected hex format when present.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("checksum_valid_format")
        failures = []
        for table_name in ("files", "artifact_registry", "artifacts"):
            _, rows = self.table(table_name)
            for row in active_rows(rows):
                sha256 = row.get("sha256", "")
                if sha256 and not SHA256_RE.match(sha256):
                    failures.append({"table": table_name, "sha256": sha256})
        return result("checksum_valid_format", "files_and_artifacts", severity, failures, description)

    def status_in_enum(self) -> CheckResult:
        """
        Ensure status values appear in enum contracts.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("status_in_enum")
        failures = []
        analysis_status = set(self.enums.get("analysis_status", []))
        artifact_status = set(self.enums.get("artifact_status", []))
        for row in active_rows(self.table("analysis_registry")[1]):
            if row.get("status", "") not in analysis_status:
                failures.append({"table": "analysis_registry", "status": row.get("status", "")})
        for row in active_rows(self.table("artifact_registry")[1]):
            if row.get("status", "") not in artifact_status:
                failures.append({"table": "artifact_registry", "status": row.get("status", "")})
        return result("status_in_enum", "analysis_and_artifact_registries", severity, failures, description)

    def provenance_present(self) -> list[CheckResult]:
        """
        Verify standard provenance columns are populated.
        
        Returns:
        One :class:`~tolkien.validation.validate.CheckResult` per table checked.
        """
        severity, description = self.severity("provenance_present")
        required = {"source_name", "source_version", "ingested_at", "record_version", "is_active"}
        checks = []
        for table_name in self.contracts.get("tables", {}):
            _, rows = self.table(table_name)
            failures = [row for row in active_rows(rows) if any(not row.get(column) for column in required)]
            checks.append(result("provenance_present", table_name, severity, failures, description))
        return checks

    def event_time_anchor_present(self) -> CheckResult:
        """
        Ensure patient events carry a usable time anchor.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("event_time_anchor_present")
        _, rows = self.table("patient_events")
        failures = [row for row in active_rows(rows) if not row.get("event_time_anchor")]
        return result("event_time_anchor_present", "patient_events", severity, failures, description)

    def lineage_required_fields_present(self) -> CheckResult:
        """
        Verify lineage edge rows include required PROV fields.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("lineage_required_fields_present")
        required = {"run_id", "activity_type", "source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", "derivation_type"}
        _, rows = self.table("lineage_edges")
        failures = [row for row in active_rows(rows) if any(not row.get(column) for column in required)]
        return result("lineage_required_fields_present", "lineage_edges", severity, failures, description)

    def primitive_relation_refs_resolve(self) -> CheckResult:
        """
        Ensure relation endpoints resolve to existing primitive rows.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("primitive_relation_refs_resolve")
        entity_ids = {row.get("entity_id", "") for row in active_rows(self.table("entities")[1])}
        event_ids = {row.get("event_id", "") for row in active_rows(self.table("events")[1])}
        observation_ids = {row.get("observation_id", "") for row in active_rows(self.table("observations")[1])}
        relation_ids = {row.get("relation_id", "") for row in active_rows(self.table("relations")[1])}
        ids_by_type = {
            "entity": entity_ids,
            "event": event_ids,
            "observation": observation_ids,
            "relation": relation_ids,
        }

        failures = []
        _, rows = self.table("relations")
        for row in active_rows(rows):
            source_type = row.get("source_object_type", "")
            target_type = row.get("target_object_type", "")
            source_id = row.get("source_object_id", "")
            target_id = row.get("target_object_id", "")
            if source_id not in ids_by_type.get(source_type, set()):
                failures.append({"relation_id": row.get("relation_id", ""), "missing_source": source_id, "source_object_type": source_type})
            if target_id not in ids_by_type.get(target_type, set()):
                failures.append({"relation_id": row.get("relation_id", ""), "missing_target": target_id, "target_object_type": target_type})
        return result("primitive_relation_refs_resolve", "relations", severity, failures, description)

    def primitive_value_type_matches_columns(self) -> CheckResult:
        """
        Match observation value columns to declared value_type.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("primitive_value_type_matches_columns")
        allowed = set(self.primitive_enums.get("value_type", []))
        _, rows = self.table("observations")
        failures = []
        for row in active_rows(rows):
            value_type = row.get("value_type", "")
            if allowed and value_type not in allowed:
                failures.append({"observation_id": row.get("observation_id", ""), "value_type": value_type, "reason": "unknown value_type"})
                continue
            if value_type == "number" and not row.get("value_number"):
                failures.append({"observation_id": row.get("observation_id", ""), "value_type": value_type, "reason": "value_number empty"})
            elif value_type == "boolean" and str(row.get("value_boolean", "")).lower() not in {"true", "false"}:
                failures.append({"observation_id": row.get("observation_id", ""), "value_type": value_type, "reason": "value_boolean not true/false"})
            elif value_type in {"text", "json", "entity_ref", "artifact_ref"} and not row.get("value_text"):
                failures.append({"observation_id": row.get("observation_id", ""), "value_type": value_type, "reason": "value_text empty"})
        return result("primitive_value_type_matches_columns", "observations", severity, failures, description)

    def artifact_type_and_role_valid(self) -> CheckResult:
        """
        Validate artifact type/role against enum contracts.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("artifact_type_and_role_valid")
        allowed_types = set(self.primitive_enums.get("artifact_type", []))
        allowed_roles = set(self.primitive_enums.get("artifact_role", []))
        _, rows = self.table("artifacts")
        failures = []
        for row in active_rows(rows):
            artifact_type = row.get("artifact_type", "")
            artifact_role = row.get("artifact_role", "")
            if not artifact_type or (allowed_types and artifact_type not in allowed_types):
                failures.append({"artifact_id": row.get("artifact_id", ""), "artifact_type": artifact_type, "reason": "invalid artifact_type"})
            if not artifact_role or (allowed_roles and artifact_role not in allowed_roles):
                failures.append({"artifact_id": row.get("artifact_id", ""), "artifact_role": artifact_role, "reason": "invalid artifact_role"})
        return result("artifact_type_and_role_valid", "artifacts", severity, failures, description)

    def artifact_path_or_uri_present(self) -> CheckResult:
        """
        Require path_rel or uri on active artifact rows.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("artifact_path_or_uri_present")
        _, rows = self.table("artifacts")
        failures = [
            {"artifact_id": row.get("artifact_id", "")}
            for row in active_rows(rows)
            if not row.get("path_rel") and not row.get("uri")
        ]
        return result("artifact_path_or_uri_present", "artifacts", severity, failures, description)

    def artifact_path_exists(self) -> CheckResult:
        """
        Verify artifact path_rel targets exist under repo root.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("artifact_path_exists")
        _, rows = self.table("artifacts")
        failures = []
        for row in active_rows(rows):
            path_rel = row.get("path_rel", "")
            status = row.get("status", "")
            if path_rel and status in {"active", "validated"} and not (self.repo_root / path_rel).exists():
                failures.append({"artifact_id": row.get("artifact_id", ""), "path_rel": path_rel})
        return result("artifact_path_exists", "artifacts", severity, failures, description)

    def artifact_integrity_fields_valid(self) -> CheckResult:
        """
        Validate checksum and byte_size fields on artifacts.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("artifact_integrity_fields_valid")
        _, rows = self.table("artifacts")
        failures = []
        for row in active_rows(rows):
            sha256 = row.get("sha256", "")
            if sha256 and not SHA256_RE.match(sha256):
                failures.append({"artifact_id": row.get("artifact_id", ""), "sha256": sha256, "reason": "invalid sha256"})
            byte_size = row.get("byte_size", "")
            if byte_size:
                try:
                    if int(float(byte_size)) < 0:
                        failures.append({"artifact_id": row.get("artifact_id", ""), "byte_size": byte_size, "reason": "negative byte_size"})
                except ValueError:
                    failures.append({"artifact_id": row.get("artifact_id", ""), "byte_size": byte_size, "reason": "not numeric"})
        return result("artifact_integrity_fields_valid", "artifacts", severity, failures, description)

    def artifact_entity_ref_valid(self) -> CheckResult:
        """
        Ensure artifact entity_id resolves in entities table.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("artifact_entity_ref_valid")
        entity_rows = active_rows(self.table("entities")[1])
        artifact_entity_ids = {row.get("entity_id", "") for row in entity_rows if row.get("entity_type") == "artifact"}
        _, rows = self.table("artifacts")
        failures = [
            {"artifact_id": row.get("artifact_id", ""), "entity_id": row.get("entity_id", "")}
            for row in active_rows(rows)
            if row.get("entity_id", "") not in artifact_entity_ids
        ]
        return result("artifact_entity_ref_valid", "artifacts", severity, failures, description)

    def artifact_created_by_event_valid(self) -> CheckResult:
        """
        Validate created_by_event_id references when set.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("artifact_created_by_event_valid")
        event_ids = {row.get("event_id", "") for row in active_rows(self.table("events")[1])}
        _, rows = self.table("artifacts")
        failures = []
        for row in active_rows(rows):
            event_id = row.get("created_by_event_id", "")
            if event_id and event_id not in event_ids:
                failures.append({"artifact_id": row.get("artifact_id", ""), "created_by_event_id": event_id})
        return result("artifact_created_by_event_valid", "artifacts", severity, failures, description)

    def collection_artifact_contains_members(self) -> CheckResult:
        """
        Ensure collection artifacts have contains relations.
        
        Returns:
        ``CheckResult`` value.
        """
        severity, description = self.severity("collection_artifact_contains_members")
        collection_entity_ids = {
            row.get("entity_id", "")
            for row in active_rows(self.table("artifacts")[1])
            if row.get("artifact_type") == "collection_artifact"
        }
        contains_sources = {
            row.get("source_object_id", "")
            for row in active_rows(self.table("relations")[1])
            if row.get("relation_type") == "contains"
        }
        failures = [
            {"entity_id": entity_id}
            for entity_id in collection_entity_ids
            if entity_id and entity_id not in contains_sources
        ]
        return result("collection_artifact_contains_members", "artifacts", severity, failures, description)

    def run(self) -> list[CheckResult]:
        """
        Execute all registered validation checks and return results.
        
        Returns:
        All :class:`~tolkien.validation.validate.CheckResult` rows from configured checks.
        """

        checks: list[CheckResult] = []
        checks.extend(self.required_columns_present())
        checks.extend(self.primary_key_not_null())
        checks.extend(self.primary_key_unique())
        checks.append(self.fk_check("fk_file_to_series", "files", "series_uid", "series", "series_uid"))
        checks.append(self.fk_check("fk_series_to_study", "series", "study_uid", "studies", "study_uid"))
        checks.append(self.fk_check("fk_study_to_patient", "studies", "patient_uid", "patients", "patient_uid"))
        checks.append(self.fk_check("fk_event_to_patient", "patient_events", "patient_uid", "patients", "patient_uid"))
        checks.append(self.fk_check("fk_observation_to_event", "modality_observations", "event_uid", "patient_events", "event_uid"))
        checks.append(self.fk_check("fk_observation_to_file", "modality_observations", "file_uid", "files", "file_uid", allow_empty=True))
        checks.append(self.fk_check("fk_primitive_event_subject", "events", "subject_entity_id", "entities", "entity_id"))
        checks.append(self.fk_check("fk_primitive_observation_subject", "observations", "subject_entity_id", "entities", "entity_id"))
        checks.append(self.fk_check("fk_primitive_observation_event", "observations", "event_id", "events", "event_id", allow_empty=True))
        checks.append(self.crosswalk_conflict_free())
        checks.append(self.relative_paths_only())
        checks.append(self.path_exists_for_registries())
        checks.append(self.checksum_valid_format())
        checks.append(self.status_in_enum())
        checks.extend(self.provenance_present())
        checks.append(self.event_time_anchor_present())
        checks.append(self.lineage_required_fields_present())
        checks.append(self.primitive_relation_refs_resolve())
        checks.append(self.primitive_value_type_matches_columns())
        checks.append(self.artifact_type_and_role_valid())
        checks.append(self.artifact_path_or_uri_present())
        checks.append(self.artifact_path_exists())
        checks.append(self.artifact_integrity_fields_valid())
        checks.append(self.artifact_entity_ref_valid())
        checks.append(self.artifact_created_by_event_valid())
        checks.append(self.collection_artifact_contains_members())
        return checks


def write_reports(repo_root: Path, run_id: str, checks: list[CheckResult]) -> tuple[Path, Path]:
    """
    Write JSONL detail log and markdown summary under ``data/logs/validation/``.

    Args:
            repo_root (Path): Repository root; relative paths resolve against this directory.
            run_id (str): Workflow run identifier (often ``GENFEAT_RUN_ID``).
            checks (list[CheckResult]): Validation check results to serialize into reports.

    Returns:
            Tuple of ``(jsonl_path, markdown_summary_path)``.
    """

    paths = DatastorePaths(repo_root.resolve())
    timestamp = utc_now()
    output_root = paths.validation_logs_dir
    output_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_root / f"{run_id}.jsonl"
    md_path = output_root / f"{run_id}_summary.md"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for check in checks:
            payload = {
                "run_id": run_id,
                "run_timestamp": timestamp,
                "check_id": check.check_id,
                "table_name": check.table_name,
                "severity": check.severity,
                "failure_count": check.failure_count,
                "sample_rows": check.sample_rows,
                "description": check.description,
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    failures = [check for check in checks if check.failure_count]
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# Validation Summary: {run_id}\n\n")
        handle.write(f"- Timestamp: `{timestamp}`\n")
        handle.write(f"- Checks: `{len(checks)}`\n")
        handle.write(f"- Failed checks: `{len(failures)}`\n\n")
        handle.write("| Check | Table | Severity | Failures |\n")
        handle.write("|---|---|---|---:|\n")
        for check in checks:
            handle.write(f"| `{check.check_id}` | `{check.table_name}` | `{check.severity}` | {check.failure_count} |\n")

    return jsonl_path, md_path


def main() -> None:
    """
    CLI: run validation gates and write reports (exit 1 on error-level failures).
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description="Run canonical metadata validation gates.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", default=f"val_{uuid.uuid4().hex[:12]}")
    parser.add_argument("--no-write", action="store_true", help="Do not write JSONL/Markdown reports.")
    args = parser.parse_args()

    validator = Validator(args.repo_root)
    checks = validator.run()
    error_failures = [check for check in checks if check.severity == "error" and check.failure_count]

    if not args.no_write:
        jsonl_path, md_path = write_reports(args.repo_root, args.run_id, checks)
        print(json.dumps({"jsonl": str(jsonl_path), "markdown": str(md_path)}, indent=2))

    summary = {
        "run_id": args.run_id,
        "checks": len(checks),
        "failed_checks": len([check for check in checks if check.failure_count]),
        "error_failures": len(error_failures),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if error_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
