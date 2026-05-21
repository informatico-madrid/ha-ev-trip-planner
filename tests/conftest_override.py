"""Override conftest to disable pytest_homeassistant_custom_component for mutmut."""
import sys

# Clear any cached imports of problematic modules
for mod in list(sys.modules.keys()):
    if 'pytest_homeassistant' in mod or 'homeassistant.runner' in mod or 'homeassistant.bootstrap' in mod:
        del sys.modules[mod]
