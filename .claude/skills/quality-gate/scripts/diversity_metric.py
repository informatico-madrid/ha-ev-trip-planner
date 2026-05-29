#!/usr/bin/env python3
"""
Diversity Metric — Calculate test diversity using Levenshtein edit distance.

Detects test cases that are essentially copy-paste with minimal changes,
which indicates low-value test duplication.

Usage:
    python3 diversity_metric.py <tests_dir>
    # For layered test structure, run per layer:
    python3 diversity_metric.py tests/unit
    python3 diversity_metric.py tests/integration

Output:
    JSON with diversity_score, min/max edit distance, and similar pairs.
"""

import ast
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def get_test_body_text(test_node: ast.FunctionDef, source: str) -> str:
    """Extract the body of a test function as normalized text."""
    lines = source.split("\n")
    start = test_node.lineno - 1
    end = test_node.end_lineno if hasattr(test_node, "end_lineno") and test_node.end_lineno else start + 20
    return " ".join(lines[start:end])


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def analyze_test_file(filepath: Path) -> list[dict[str, Any]]:
    """Extract test functions from a file with their body text."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    tests = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            body_text = get_test_body_text(node, content)
            normalized = " ".join(body_text.split())  # Normalize whitespace
            tests.append({
                "name": node.name,
                "lineno": node.lineno,
                "body_text": normalized,
                "body_length": len(normalized),
            })

    return tests


def _compare_pairs_chunk(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[list[dict[str, Any]], int, int]:
    """Compare a chunk of (t1, t2) pairs. Runs in a worker process."""
    similar_pairs: list[dict[str, Any]] = []
    min_dist = 10**9
    max_dist = 0

    for t1, t2 in pairs:
        if t1["body_length"] < 20 or t2["body_length"] < 20:
            continue
        dist = levenshtein_distance(t1["body_text"], t2["body_text"])
        max_len = max(t1["body_length"], t2["body_length"])
        if max_len == 0:
            continue
        similarity = 1.0 - (dist / max_len)
        min_dist = min(min_dist, dist)
        max_dist = max(max_dist, dist)
        if similarity > 0.8:
            similar_pairs.append({
                "file": t1["file"],
                "test1": t1["name"],
                "test2": t2["name"],
                "edit_distance": dist,
                "similarity": round(similarity, 3),
            })

    return similar_pairs, min_dist, max_dist


def main(tests_dir: str) -> None:
    tests_path = Path(tests_dir)

    all_tests: list[dict[str, Any]] = []
    for test_file in tests_path.rglob("test_*.py"):
        if "__pycache__" in str(test_file):
            continue
        tests = analyze_test_file(test_file)
        for t in tests:
            t["file"] = str(test_file.relative_to(tests_path))
            all_tests.append(t)

    tests_by_file: dict[str, list[dict[str, Any]]] = {}
    for t in all_tests:
        tests_by_file.setdefault(t["file"], []).append(t)

    # Generate all within-file pairs upfront, then split into even chunks
    all_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for file_tests in tests_by_file.values():
        for i, t1 in enumerate(file_tests):
            for t2 in file_tests[i + 1:]:
                all_pairs.append((t1, t2))

    cpu_count = os.cpu_count() or 4
    chunk_size = max(1, len(all_pairs) // (cpu_count * 4))
    chunks = [all_pairs[i:i + chunk_size] for i in range(0, len(all_pairs), chunk_size)]

    min_distance = float("inf")
    max_distance = 0
    similar_pairs: list[dict[str, Any]] = []

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(_compare_pairs_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            pairs, fmin, fmax = future.result()
            similar_pairs.extend(pairs)
            if pairs or fmin < 10**9:
                min_distance = min(min_distance, fmin)
                max_distance = max(max_distance, fmax)

    if min_distance == float("inf"):
        min_distance = 0
        max_distance = 0
        diversity_score = 1.0
    else:
        # Diversity score: 1.0 = all tests are unique, 0.0 = all tests are identical
        diversity_score = round(max(0.0, 1.0 - len(similar_pairs) / max(len(all_tests), 1)), 3)

    result = {
        "total_tests": len(all_tests),
        "diversity_score": diversity_score,
        "min_edit_distance": min_distance,
        "max_edit_distance": max_distance,
        "similar_pairs": sorted(similar_pairs, key=lambda x: x["similarity"], reverse=True)[:10],
        "summary": {
            "high_diversity": diversity_score >= 0.7,
            "low_diversity": diversity_score < 0.3,
            "similar_pair_count": len(similar_pairs),
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: diversity_metric.py <tests_dir>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
