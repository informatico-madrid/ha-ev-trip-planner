"""Test that pyproject.toml uses the correct import-linter config key.

Import-linter reads its config from [tool.importlinter] (no hyphen).
A hyphenated key [tool.import-linter] is silently ignored by the tool.

Requirement: FR-3.5
Design: §4.4 (lint-imports Contracts TOML)
"""

from pathlib import Path

import tomllib

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_pyproject_uses_non_hyphenated_importlinter_key():
    """pyproject.toml MUST contain [tool.importlinter] (no hyphen).

    The import-linter CLI reads config from the ``[tool.importlinter]`` TOML table.
    A hyphenated key ``[tool.import-linter]`` is a *different* TOML table and
    is silently ignored — meaning no contracts would ever be enforced.
    """
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)

    tools = data.get("tool", {})

    # The correct key: no hyphen
    assert "importlinter" in tools, (
        "pyproject.toml must contain [tool.importlinter] (no hyphen). "
        "A hyphenated [tool.import-linter] table is silently ignored by "
        "the import-linter CLI."
    )

    # The hyphenated key must NOT be the one used for config
    assert "import-linter" not in tools, (
        "pyproject.toml should not use [tool.import-linter] (with hyphen). "
        "Use [tool.importlinter] instead; the hyphenated key is silently ignored."
    )
