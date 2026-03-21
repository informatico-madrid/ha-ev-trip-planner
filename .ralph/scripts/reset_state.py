#!/usr/bin/env python3
"""
Reset Ralph state for a spec to force re-execution from the beginning.

Usage:
    python .ralph/scripts/reset_state.py specs/001-feature --confirm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def reset_state(spec_dir: Path, confirm: bool = False) -> int:
    """Reset state for a spec directory."""
    if not confirm:
        print("WARNING: This will reset all tasks to incomplete state!")
        print(f"Spec dir: {spec_dir}")
        print("Use --confirm to proceed")
        return 1

    # Find state file
    slug = spec_dir.name
    state_file = Path(".ralph") / f"state-{slug}.json"
    
    if not state_file.exists():
        print(f"State file not found: {state_file}")
        return 1

    # Read current state
    state = json.load(open(state_file))
    
    # Reset to initial state
    initial_state = {
        "awaitingApproval": False,
        "baseBranch": state.get("baseBranch", ""),
        "basePath": state.get("basePath", ""),
        "featureId": state.get("featureId", "000"),
        "fixTaskMap": {},
        "globalIteration": 0,
        "lastReviewAt": 0,
        "maxFixTasksPerOriginal": 3,
        "maxGlobalIterations": state.get("maxGlobalIterations", 100),
        "maxTaskIterations": state.get("maxTaskIterations", 30),
        "name": state.get("name", ""),
        "phase": "execution",
        "recoveryMode": False,
        "reviewInterval": state.get("reviewInterval", 5),
        "taskIndex": 0,
        "taskIteration": 1,
        "totalTasks": 0,
        "worktreePath": state.get("worktreePath", ""),
        "worktreeBranch": state.get("worktreeBranch", ""),
        "worktreeCreatedAt": state.get("worktreeCreatedAt", ""),
    }
    
    # Write new state
    with open(state_file, "w") as f:
        json.dump(initial_state, f, indent=2)
    
    print(f"State reset for spec: {slug}")
    print(f"State file: {state_file}")
    print("All tasks will be re-executed from the beginning")
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset Ralph state for a spec")
    parser.add_argument("spec_dir", help="Path to spec directory (e.g., specs/001-feature)")
    parser.add_argument("--confirm", action="store_true", help="Confirm the reset")
    args = parser.parse_args()

    spec_dir = Path(args.spec_dir)
    if not spec_dir.is_absolute():
        spec_dir = Path.cwd() / spec_dir
    
    return reset_state(spec_dir, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
