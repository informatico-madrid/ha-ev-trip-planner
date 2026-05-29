"""Monkey-patch mutmut PytestRunner.run_stats to use pluginmanager.register().

The default StatsCollector inner-class pattern doesn't work with pytest-homeassistant-custom-component because that plugin overrides pytest_runtest_teardown. Registering via pluginmanager ensures hooks fire regardless of other plugin overrides."""

from __future__ import annotations


import mutmut
from mutmut.__main__ import change_cwd, unused


def apply():
    """Monkey-patch mutmut.PytestRunner.run_stats in-place."""
    from mutmut.__main__ import PytestRunner

    _original_run_stats = PytestRunner.run_stats

    def patched_run_stats(self, *, tests):

        class StatsCollector:
            def pytest_runtest_logstart(self, nodeid):
                mutmut.duration_by_test[nodeid] = 0

            def pytest_runtest_makereport(self, item, call):
                mutmut.duration_by_test[item.nodeid] += call.duration

        stats_collector = StatsCollector()

        pytest_args = ["-q"]
        if tests:
            pytest_args += list(tests)
        else:
            pytest_args += self._pytest_add_cli_args_test_selection

        class TeardownHook:
            """Registered via pluginmanager to bypass pytest_homeassistant_custom_component override."""

            def pytest_configure(self, config):
                # Register teardown hook as a real plugin — fires even when
                # other plugins (pytest-homeassistant-custom-component) override
                # the conftest-level hook mechanism.
                config.pluginmanager.register(
                    _StatsTeardown(), "_mutmut_stats_teardown"
                )

        class _StatsTeardown:
            def pytest_runtest_teardown(self, item, nextitem):
                unused(nextitem)
                for function in mutmut._stats:
                    prefix = "mutants/"
                    nodeid = item._nodeid
                    if nodeid.startswith(prefix):
                        nodeid = nodeid[len(prefix):]
                    mutmut.tests_by_mangled_function_name[function].add(nodeid)
                mutmut._stats.clear()

        teardown_hook = TeardownHook()

        with change_cwd("mutants"):
            return int(
                self.execute_pytest(
                    pytest_args, plugins=[stats_collector, teardown_hook]
                )
            )

    PytestRunner.run_stats = patched_run_stats
    print("[patch_mutmut_stats] PytestRunner.run_stats patched successfully")


if __name__ == "__main__":
    apply()
