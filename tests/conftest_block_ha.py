"""Block problematic HA imports during pytest collection for mutmut."""
import sys

# Block bleak/dbus_fast before pytest_homeassistant_custom_component loads them
class _Blocker:
    _modules = {
        'dbus_fast', 'dbus_fast.service', 'dbus_fast.service.dbus_property',
        'dbus_fast.service.dbus_property', 'dbus_fast.types',
        'habluetooth', 'bleak', 'bleak_retry_connector',
        'bleak.backends', 'bleak.backends.bluezdbus',
        'bleak.backends.bluezdbus.manager',
        'bleak.backends.bluezdbus.advertisement_monitor',
    }
    def find_module(self, name, path=None):
        if name in self._modules or any(name.startswith(m + '.') for m in self._modules):
            if name not in sys.modules:
                sys.modules[name] = type(sys)(name)
            return self
        return None
    def load_module(self, name):
        if name not in sys.modules:
            sys.modules[name] = type(sys)(name)
        return sys.modules[name]

# Install the blocker BEFORE pytest loads any plugins
sys.meta_path.insert(0, _Blocker())
