#!/usr/bin/env python3
"""Wrapper for mutmut that applies the pluginmanager.register() patch.

This fixes the stats collection bug where pytest_homeassistant_custom_component
overrides pytest_runtest_teardown, causing 0 entries in tests_by_mangled_function_name.
"""

from __future__ import annotations

import sys

from patch_mutmut_stats import apply

apply()

# Now invoke mutmut's CLI
import mutmut.__main__

if __name__ == "__main__":
    sys.exit(mutmut.__main__.main())
else:
    # Called as library, don't exit
    pass
