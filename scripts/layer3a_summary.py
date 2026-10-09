"""Summarize the tracked antipattern checker's report for the CI smoke test."""

import json
import sys
from pathlib import Path


def main(report_path: str) -> int:
    """Return 0 for clean checks, 1 for findings and 2 for an invalid report."""
    try:
        summary = json.loads(Path(report_path).read_text(encoding="utf-8"))[
            "tier_a_summary"
        ]
        passed = int(summary["passed"])
        failed = int(summary["failed"])
        total = int(summary["total"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Invalid Layer 3A report: {error}", file=sys.stderr)
        return 2
    print(f"Tier A antipattern checks: {passed}/{total} passed, {failed} with findings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
