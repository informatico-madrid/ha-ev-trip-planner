#!/bin/bash
# Run mutmut with the patched PytestRunner.run_stats
# Applies pluginmanager.register() fix for stats collection
set -euo pipefail
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner

# Patch mutmut before running, then exec mutmut with same args
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from patch_mutmut_stats import apply
apply()

# Monkey-patch the CLI entry point to use patched runner before mutmut CLI runs
import mutmut.__main__ as mm
original_run = mm.run_mutation_testing

def patched_run(*args, **kwargs):
    return original_run(*args, **kwargs)

mm.run_mutation_testing = patched_run
"

# Now exec mutmut with the original arguments
exec python3 -m mutmut "$@"
