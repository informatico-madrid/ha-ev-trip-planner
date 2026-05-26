#!/usr/bin/env python3
"""
Mutation Analyzer — Analyze mutation testing results with per-module thresholds.

Parses mutmut 3.x results via `mutmut results --all true` and produces
per-module kill statistics. Compares against thresholds defined in
pyproject.toml [tool.quality-gate.mutation].

Usage:
    # Original mode: JSON kill-map only
    python3 mutation_analyzer.py <project_root>

    # Gate mode: Compare against thresholds, output OK/NOK
    python3 mutation_analyzer.py <project_root> --gate

    # Gate mode for a single module
    python3 mutation_analyzer.py <project_root> --gate --module calculations

Output:
    JSON with mutation_kill_map per module, overall kill rate, and gate status.

Data source:
    mutmut 3.x stores results in an internal cache (not .mutmut/index.html).
    This script uses `mutmut results --all true` to get per-mutant status,
    then aggregates by module name extracted from the mutant identifier.

    Format: "custom_components.ev_trip_planner.<module>.<func>__mutmut_N: <status>"
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

PYPROJECT_TOML = "pyproject.toml"

# Module name extraction is done via dotted path splitting below.
# Regex removed: function names can contain unicode/special chars (e.g. │)
# that \w+ doesn't match.


def parse_mutmut_results(project_root: Path) -> dict[str, Any]:
    """Parse mutmut 3.x results via `mutmut results --all true`.

    Returns a dict with:
    - found: bool
    - mutation_kill_map: dict of module_name -> {killed, survived, timeout, no_tests, total, rate}
    - overall_kill_rate: float
    - overall_killed: int
    - overall_total: int
    """
    try:
        # Use string with shell=True so && chaining works correctly.
        # When shell=True with a list, only the first element is used as command
        # and rest become positional args — so we must use a single string.
        result = subprocess.run(
            ". .venv/bin/activate && mutmut results --all true",
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"error": "mutmut results command failed", "found": False}

    if result.returncode != 0:
        # Try without shell activation (venv might already be active)
        try:
            result = subprocess.run(
                ["mutmut", "results", "--all", "true"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"error": "mutmut not available", "found": False}

    # Fix: mutmut reports "no tests" (with space) but our dict key is "no_tests"

    if not result.stdout.strip():
        return {"error": "mutmut results empty — run 'mutmut run' first", "found": False}

    # Parse output: "module.submodule.func__mutmut_N: status"
    module_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"killed": 0, "survived": 0, "timeout": 0, "no_tests": 0,
                 "skipped": 0, "suspicious": 0, "runtime_error": 0, "abandoned": 0}
    )
    other_count = 0

    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if ": " not in line:
            continue

        name, status = line.rsplit(": ", 1)
        status = status.strip().lower().replace(" ", "_")

        # Extract module name from mutmut 3.x naming convention.
        # Format: "custom_components.ev_trip_planner.<module>.<func>__mutmut_N: <status>"
        # For __init__.py: "custom_components.ev_trip_planner.<func>__mutmut_N: <status>" (3 parts)
        # For regular modules: at least 4 parts (module + dotted func parts)
        # Function names may contain unicode/special chars (e.g. │), so \w+ is insufficient.
        parts = name.split(".")
        if len(parts) >= 4 and parts[0] == "custom_components" and parts[1] == "ev_trip_planner":
            module_name = parts[2]
        elif len(parts) == 3 and parts[0] == "custom_components" and parts[1] == "ev_trip_planner":
            # __init__.py: 3 parts — treat as "__init__" module
            module_name = "__init__"
        else:
            module_name = "_other"
            other_count += 1

        if status in module_stats[module_name]:
            module_stats[module_name][status] += 1

    # Build kill_map with rates
    # Kill rate uses only testable mutants: killed / (killed + survived + timeout + runtime_error)
    # no_tests = untestable code paths (tracked separately, not in kill rate)
    # skipped/abandoned = unreliable, excluded from total
    kill_map: dict[str, dict[str, Any]] = {}
    overall_killed = 0
    overall_total = 0

    for module_name, stats in sorted(module_stats.items()):
        testable_total = (stats["killed"] + stats["survived"] + stats["timeout"]
                         + stats["runtime_error"])
        if testable_total == 0:
            continue
        rate = round(stats["killed"] / testable_total, 3)
        total = testable_total + stats["no_tests"] + stats["skipped"] + stats["abandoned"]
        kill_map[module_name] = {
            "killed": stats["killed"],
            "survived": stats["survived"],
            "timeout": stats["timeout"],
            "no_tests": stats["no_tests"],
            "total": total,
            "rate": rate,
        }
        overall_killed += stats["killed"]
        overall_total += testable_total

    overall_rate = round(overall_killed / overall_total, 3) if overall_total > 0 else 0.0

    return {
        "found": True,
        "mutation_kill_map": kill_map,
        "overall_kill_rate": overall_rate,
        "overall_killed": overall_killed,
        "overall_total": overall_total,
    }


def parse_equivalents(project_root: Path) -> dict[str, int]:
    """Parse equivalent-mutants.md to extract registered equivalents per module.

    Returns a dict mapping module_name -> count of registered equivalent survivors.
    Deduplicates by function name to avoid double-counting (some entries are duplicated
    with and without 'x_' prefix).
    """
    equiv_path = project_root / "specs" / "mutation-score-ramp" / "equivalent-mutants.md"
    if not equiv_path.exists():
        return {}

    # Parse: module -> {function_name -> count} for dedup
    module_funcs: dict[str, dict[str, int]] = defaultdict(dict)
    in_table = False

    with open(equiv_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("|---"):
                in_table = True
                continue
            if in_table and stripped.startswith("| EQ-"):
                parts = [p.strip() for p in stripped.split("|") if p.strip()]
                if len(parts) >= 2:
                    loc = parts[1]
                    # Extract module name from path. Two formats:
                    # 1) Directory-based: ev_trip_planner/<module>/...  (new format)
                    # 2) File-based:      ev_trip_planner/<file>.py:...  (old format)
                    m_dir = re.search(r"ev_trip_planner/([^/]+)/", loc)
                    m_file = re.search(r"ev_trip_planner/([^/]+\.py)", loc)
                    if m_dir:
                        module = m_dir.group(1)
                    elif m_file:
                        module = m_file.group(1).replace(".py", "")
                    else:
                        continue
                    # Map filenames to module names (old-style entries)
                    module_overrides = {
                        "register_services": "services",
                        "controller": "vehicle",
                        "panel_coordinator": "panel",
                        "coordinator": "coordinator",
                        "panel": "panel",
                    }
                    if module in module_overrides:
                        module = module_overrides[module]

                    # Extract function name and count
                    # Format: "...py:? (func_name, N survived)" or "(~N mutations in func)"
                    fn_match = re.search(r"\((?:x_)?([\w]+?),\s*(\d[\d,]*)\s+survived\)", loc)
                    if fn_match:
                        raw_name = fn_match.group(1)
                        # Normalize: strip x_ and leading _ for dedup
                        func_name = re.sub(r'^x_|^_', '', raw_name)
                        count = int(fn_match.group(2).replace(",", ""))
                        # Deduplicate: keep max count per normalized function name
                        existing = module_funcs[module].get(func_name, 0)
                        module_funcs[module][func_name] = max(existing, count)
                    else:
                        # Alternative format: "(~N mutations in func)"
                        m2 = re.search(r"~?\s*(\d[\d,]*)\s+mutations?\s+in", loc)
                        if m2:
                            count = int(m2.group(1).replace(",", ""))
                            # Extract function name after "in"
                            fn_match2 = re.search(r"in\s+([\w]+)", loc)
                            func_name = re.sub(r'^x_|^_', '', fn_match2.group(1)) if fn_match2 else None
                            if func_name:
                                existing = module_funcs[module].get(func_name, 0)
                                module_funcs[module][func_name] = max(existing, count)

    # Sum up deduplicated counts per module
    equivalents_by_module: dict[str, int] = {}
    for module, funcs in module_funcs.items():
        equivalents_by_module[module] = sum(funcs.values())

    return equivalents_by_module


def load_targets_from_pyproject(project_root: Path) -> dict[str, Any]:
    """Load mutation targets from pyproject.toml [tool.quality-gate.mutation].

    Returns a dict with:
    - global_kill_threshold: float
    - fail_on_missing_module: bool
    - increment_step: float
    - target_final: float
    - modules_per_sprint: int
    - modules: dict of module_name -> {kill_threshold, status, notes}
    """
    pyproject_path = project_root / PYPROJECT_TOML
    if not pyproject_path.exists():
        return {}

    if tomllib is None:
        print("[WARN] tomllib not available — cannot read pyproject.toml. Using defaults.", file=sys.stderr)
        return {}

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    qg = data.get("tool", {}).get("quality-gate", {}).get("mutation", {})
    if not qg:
        return {}

    return {
        "global_kill_threshold": qg.get("global_kill_threshold", 0.48),
        "fail_on_missing_module": qg.get("fail_on_missing_module", False),
        "increment_step": qg.get("increment_step", 0.05),
        "target_final": qg.get("target_final", 0.80),
        "modules_per_sprint": qg.get("modules_per_sprint", 2),
        "modules": qg.get("modules", {}),
    }


def run_gate(
    project_root: Path,
    target_module: Optional[str] = None,
) -> dict[str, Any]:
    """Run mutation gate: parse results + compare against thresholds.

    Returns a dict with:
    - gate: "OK" or "NOK"
    - modules: list of per-module results
    - summary: overall statistics
    """
    # 1. Parse mutation results from mutmut 3.x
    mutmut_result = parse_mutmut_results(project_root)
    kill_map = mutmut_result.get("mutation_kill_map", {})

    if not kill_map:
        return {
            "gate": "NOK",
            "error": mutmut_result.get("error", "No mutation results found. Run 'mutmut run' first."),
            "modules": [],
            "summary": {
                "modules_checked": 0,
                "modules_passed": 0,
                "modules_failed": 0,
            },
        }

    # 2. Load targets from pyproject.toml
    targets = load_targets_from_pyproject(project_root)
    global_threshold = targets.get("global_kill_threshold", 0.48)
    fail_on_missing = targets.get("fail_on_missing_module", False)
    module_targets = targets.get("modules", {})

    # 3. Load registered equivalent mutants (subtract from survived)
    equivalents = parse_equivalents(project_root)

    # 4. Compare per-module (effective kill rate considering registered equivalents)
    modules = []
    for module_name, data in kill_map.items():
        if data["total"] == 0:
            continue

        rate = data["rate"]

        # Effective rate: subtract registered equivalents from survived
        equiv_count = equivalents.get(module_name, 0)
        effective_survived = max(0, data["survived"] - equiv_count)
        effective_testable = data["killed"] + effective_survived
        effective_rate = round(data["killed"] / effective_testable, 3) if effective_testable > 0 else 1.0

        # Get threshold for this module from [tool.quality-gate.mutation.modules.<name>]
        module_config = module_targets.get(module_name, {})
        threshold = module_config.get("kill_threshold", global_threshold)

        passed = round(effective_rate, 3) >= round(threshold, 3)

        # Hard gate: effective-MSI must be 100% (no unregistered survivors)
        effective_gate = effective_survived == 0
        effective_gate_pass = effective_gate and passed

        modules.append({
            "module": module_name,
            "killed": data["killed"],
            "survived": data["survived"],
            "equiv_registered": equiv_count,
            "effective_survived": effective_survived,
            "total": data["total"],
            "kill_rate": rate,
            "effective_rate": effective_rate,
            "threshold": threshold,
            "effective_gate": effective_gate_pass,
            "passed": passed,
            "status": module_config.get("status", "unknown"),
        })

    # Filter by module if specified
    if target_module:
        modules = [m for m in modules if target_module == m["module"]]

    # Hard gate: effective-MSI must be 100% across ALL modules
    # A module passes only when effective_survived == 0 AND it meets its threshold
    modules_passed = [m for m in modules if m["effective_gate"]]
    modules_failed = [m for m in modules if not m["effective_gate"]]

    gate = "OK" if len(modules_failed) == 0 else "NOK"

    return {
        "gate": gate,
        "modules": modules,
        "summary": {
            "modules_checked": len(modules),
            "modules_passed": len(modules_passed),
            "modules_failed": len(modules_failed),
            "overall_kill_rate": mutmut_result.get("overall_kill_rate", 0.0),
            "overall_killed": mutmut_result.get("overall_killed", 0),
            "overall_total": mutmut_result.get("overall_total", 0),
        },
    }


def print_gate_report(gate_result: dict[str, Any]) -> None:
    """Print human-readable gate report to stdout."""
    summary = gate_result["summary"]
    modules = gate_result["modules"]
    gate = gate_result["gate"]

    print("\n" + "=" * 70)
    print(" MUTATION TESTING QUALITY GATE")
    print("=" * 70)

    if not modules:
        print(f"\n {gate_result.get('error', 'No modules to check')}")
        print("\n" + "=" * 70)
        return

    # Table header
    print(f"\n {'Module':<25} {'Kill Rate':>14} {'Effective':>10} {'Threshold':>10} {'Status':>8}")
    print(f" {'-'*25} {'-'*14} {'-'*10} {'-'*10} {'-'*8}")

    for m in modules:
        rate_str = f"{m['kill_rate']*100:.1f}% ({m['killed']}/{m['total']})"
        eff_str = f"{m['effective_rate']*100:.1f}% ({m['effective_survived']} left)"
        threshold_str = f"{m['threshold']*100:.0f}%"
        status_str = "PASS" if m["effective_gate"] else "FAIL"
        print(f" {m['module']:<25} {rate_str:>14} {eff_str:>10} {threshold_str:>10} {status_str:>8}")

    # Summary
    effective_survivors = sum(m["effective_survived"] for m in modules)
    print(f"\n Overall: {summary['overall_kill_rate']*100:.1f}% "
          f"({summary['overall_killed']}/{summary['overall_total']} killed)")
    print(f" Effective-MSI survivors: {effective_survivors}")
    print(f" Modules: {summary['modules_passed']}/{summary['modules_checked']} passed")

    # Gate result
    print("\n" + "-" * 70)
    if gate == "OK":
        print(" RESULT: ✅ OK — All modules have effective-MSI = 100%")
    else:
        print(" RESULT: ❌ NOK — effective-MSI < 100% for some modules")
        failed_names = [m["module"] for m in modules if not m["effective_gate"]]
        print(f" Failed: {', '.join(failed_names)}")
        for m in modules:
            if not m["effective_gate"]:
                print(f"   {m['module']}: {m['effective_survived']} unregistered survivor(s), "
                      f"effective-MSI = {m['effective_rate']*100:.1f}%")
        print("\n 💡 FIX: Either kill survivors with better tests, or register them")
        print("    in specs/mutation-score-ramp/equivalent-mutants.md")

    print("=" * 70)


def main(project_root: str) -> None:
    """Main entry point — supports both original and gate mode."""
    root = Path(project_root)

    # Parse args for gate mode
    args = sys.argv[2:]
    gate_mode = "--gate" in args
    target_module = None

    if "--module" in args:
        idx = args.index("--module")
        if idx + 1 < len(args):
            target_module = args[idx + 1]

    if gate_mode:
        # Gate mode: compare against thresholds from pyproject.toml
        gate_result = run_gate(root, target_module=target_module)
        print_gate_report(gate_result)

        # Also output JSON to stdout
        print("\n<!-- JSON OUTPUT -->")
        print(json.dumps(gate_result, indent=2))

        sys.exit(0 if gate_result["gate"] == "OK" else 1)
    else:
        # Original mode: just parse and output JSON
        mutmut_result = parse_mutmut_results(root)

        result = {
            "mutation_kill_map": mutmut_result.get("mutation_kill_map", {}),
            "overall_kill_rate": mutmut_result.get("overall_kill_rate", 0.0),
            "overall_killed": mutmut_result.get("overall_killed", 0),
            "overall_total": mutmut_result.get("overall_total", 0),
            "found": mutmut_result.get("found", False),
        }

        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: mutation_analyzer.py <project_root> [--gate] [--module MODULE]", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
