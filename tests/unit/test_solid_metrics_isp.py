"""Test that solid_metrics.py implements max_unused_methods_ratio ISP check.

Verifies the file contains actual implementation logic (AST walk + stub detection
for ABC methods), not just a docstring mention.

Requirement: AC-4.7 (max_unused_methods_ratio ISP threshold)
Design: §2 (ISP mechanism)
"""

import ast
from pathlib import Path

SOLID_METRICS = (
    Path(__file__).resolve()
    .parents[2]
    / ".agents"
    / "skills"
    / "quality-gate"
    / "scripts"
    / "solid_metrics.py"
)


def test_solid_metrics_contains_max_unused_methods_ratio_logic():
    """solid_metrics.py MUST contain AST-walk logic for max_unused_methods_ratio.

    The max_unused_methods_ratio check must be implemented in the source code
    (not only documented in a docstring). It should walk AST classes, collect
    methods, and flag those not overridden in concrete subclasses.
    """
    source = SOLID_METRICS.read_text(encoding="utf-8")

    tree = ast.parse(source)

    # Gather all identifiers (variable names, function names) in the module
    identifiers: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            identifiers.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    identifiers.add(target.id)
                elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            identifiers.add(elt.id)
        elif isinstance(node, ast.Name):
            identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Capture the attribute name (e.g. max_unused_methods_ratio)
            identifiers.add(node.attr)

    # The implementation must reference max_unused_methods_ratio somewhere
    assert "max_unused_methods_ratio" in identifiers, (
        "solid_metrics.py must reference 'max_unused_methods_ratio' as a "
        "variable, function, or attribute. It is only mentioned in the "
        "module docstring; the actual ISP check implementation is missing."
    )


def test_solid_metrics_max_unused_methods_ratio_is_not_only_in_docstring():
    """max_unused_methods_ratio must appear outside the docstring.

    A docstring-only mention is insufficient — the check must be implemented.
    """
    source = SOLID_METRICS.read_text(encoding="utf-8")

    # Strip the module docstring by finding the first non-docstring statement
    tree = ast.parse(source)
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        # Remove the docstring from source by slicing past it
        docstring_end = tree.body[0].end_lineno  # type: ignore[union-attr]
        code_without_docstring = "\n".join(source.split("\n")[docstring_end:])
    else:
        code_without_docstring = source

    assert "max_unused_methods_ratio" in code_without_docstring, (
        "solid_metrics.py mentions 'max_unused_methods_ratio' only in the "
        "module docstring. The actual implementation (AST walk + stub detection "
        "for ABC methods) must be in the code body."
    )
