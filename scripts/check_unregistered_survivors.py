#!/usr/bin/env python3
"""
Check for unregistered mutation survivors.

A survivor is "unregistered" if it survived mutation testing
but has no corresponding entry in the equivalent-mutant registry.

This is the Phase 5 persistence gate: any new survivor must be
killed or registered (dossier + approval) before merge.

Exit code 0 = OK (no unregistered survivors)
Exit code 1 = FAIL (unregistered survivors found)
"""

import json
import os
import re
import sys
from pathlib import Path


def get_registry_entries() -> set[str]:
    """Extract registry IDs from equivalent-mutants.md."""
    registry_path = Path("specs/mutation-score-ramp/equivalent-mutants.md")
    registry_ids = set()
    if not registry_path.exists():
        return registry_ids
    with open(registry_path) as f:
        for line in f:
            m = re.match(r"\|\s*EQ-(\d+)", line)
            if m:
                registry_ids.add(f"EQ-{m.group(1)}")
    return registry_ids


def get_survivors() -> list[str]:
    """Get all survived mutant keys from meta files."""
    survivors = []
    mutants_dir = Path("mutants/custom_components/ev_trip_planner")
    if not mutants_dir.exists():
        return survivors
    for fn in os.listdir(mutants_dir):
        meta_path = mutants_dir / f"{fn}.meta"
        if not meta_path.exists():
            continue
        try:
            with open(meta_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for key, status in data["exit_code_by_key"].items():
            if status == 2:  # survived
                survivors.append(key)
    return survivors


def main() -> int:
    survivors = get_survivors()
    if not survivors:
        print("OK: No unregistered survivors")
        return 0
    print(f"FAIL: {len(survivors)} unregistered survivor(s) found:")
    for s in survivors[:20]:
        print(f"  {s}")
    if len(survivors) > 20:
        print(f"  ... and {len(survivors) - 20} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
