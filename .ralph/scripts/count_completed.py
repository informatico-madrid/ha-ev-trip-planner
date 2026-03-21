#!/usr/bin/env python3
"""
Count completed tasks in tasks.md and report which task indices are done.

Usage:
    python .ralph/scripts/count_completed.py specs/010-fix-sensor-errors-dashboard-issues/tasks.md

Output:
    {"completed": 5, "done_indices": [0, 1, 2, 3, 4]}
"""

from __future__ import annotations

import argparse
import json
import sys
import re
from pathlib import Path

TASK_LINE_RE = re.compile(r"^- \[(?P<mark>[ xX])\]\s+")


def count_completed(tasks_path: Path) -> dict:
    text = tasks_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    completed = 0
    done_indices = []

    for i, line in enumerate(lines):
        m = TASK_LINE_RE.match(line)
        if m:
            is_done = m.group("mark").lower() == "x"
            if is_done:
                completed += 1
                done_indices.append(i)

    return {
        "completed": completed,
        "done_indices": done_indices,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count completed tasks in tasks.md"
    )
    parser.add_argument("tasks_file", help="Path to tasks.md")
    args = parser.parse_args()

    task_path = Path(args.tasks_file)
    if not task_path.exists():
        print(
            json.dumps({"error": f"Tasks file not found: {task_path}"}), file=sys.stderr
        )
        return 1

    result = count_completed(task_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
