"""Minimal local workflow runner.

The runner intentionally avoids a workflow engine. It executes the commands in a
workflow YAML file, then writes a run manifest capturing table versions and
declared outputs.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import uuid
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover — PyYAML is a declared dependency
    yaml = None

from tolkien.registry.layout import DatastorePaths
from tolkien.registry.run_manifest import build_manifest, write_manifest


def load_workflow(path: Path) -> dict[str, Any]:
    """
    Load and normalize a workflow YAML file.

    Args:
            path (Path): Filesystem path to read, write, or fingerprint.

    Returns:
            Normalized workflow mapping with validated ``steps`` list.
    """
    if yaml is None:
        raise SystemExit(
            "PyYAML is required to load workflow files. Install with: pip install pyyaml"
        )

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    if data is None:
        return {"workflow_name": "local_workflow", "steps": []}
    if not isinstance(data, dict):
        raise ValueError(f"Workflow root must be a mapping, got {type(data).__name__}")

    steps_raw = data.get("steps")
    if steps_raw is None:
        steps_raw = []
    if not isinstance(steps_raw, list):
        raise ValueError("workflow key 'steps' must be a list")

    normalized_steps: list[dict[str, Any]] = []
    for i, step in enumerate(steps_raw):
        if step is None:
            continue
        if not isinstance(step, dict):
            raise ValueError(f"Step at index {i} must be a mapping, got {type(step).__name__}")

        sid = step.get("id")
        if sid is None:
            sid = f"step_{i}"
        sid_str = str(sid)

        cmd = step.get("command", "")
        if cmd is not None and not isinstance(cmd, str):
            cmd = str(cmd)
        else:
            cmd = cmd or ""
        # Fold internal whitespace so block/folded YAML commands become one argv string.
        cmd_str = " ".join(str(cmd).split())

        outs = step.get("outputs")
        if outs is None:
            outs = []
        if not isinstance(outs, list):
            raise ValueError(f"Step {sid_str!r}: 'outputs' must be a list")
        out_strs = [str(x) for x in outs]

        normalized_steps.append({"id": sid_str, "command": cmd_str, "outputs": out_strs})

    out = {**data, "steps": normalized_steps}
    return out


def main() -> None:
    """
    CLI: execute workflow YAML steps and write a run manifest.
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description="Run a simple local workflow config.")
    parser.add_argument("workflow_config", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workflow = load_workflow(args.workflow_config)
    outputs: list[str] = []
    step_results = []

    run_id = os.environ.get("GENFEAT_RUN_ID") or f"run_{uuid.uuid4().hex[:12]}"
    child_env = {**os.environ, "GENFEAT_RUN_ID": run_id}

    for step in workflow.get("steps", []):
        command = step.get("command", "")
        if not command:
            continue
        if args.dry_run:
            return_code = 0
        else:
            completed = subprocess.run(
                shlex.split(command),
                cwd=args.repo_root,
                check=False,
                env=child_env,
            )
            return_code = completed.returncode
        step_results.append({"id": step.get("id"), "command": command, "return_code": return_code})
        outputs.extend(step.get("outputs", []))
        if return_code != 0:
            break

    status = "completed" if all(step["return_code"] == 0 for step in step_results) else "failed"
    if args.dry_run:
        print(json.dumps({"status": status, "dry_run": True, "steps": step_results}, indent=2))
        if status != "completed":
            raise SystemExit(1)
        return

    paths = DatastorePaths(args.repo_root.resolve())
    manifest = build_manifest(
        paths=paths,
        run_type=str(workflow.get("workflow_name", "local_workflow")),
        status=status,
        parameters={"workflow_config": str(args.workflow_config), "dry_run": args.dry_run},
        outputs=outputs,
        run_id=run_id,
    )
    manifest["workflow_steps"] = step_results
    manifest_path = write_manifest(paths, manifest)

    print(json.dumps({"status": status, "manifest_path": str(manifest_path), "steps": step_results}, indent=2))
    if status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
