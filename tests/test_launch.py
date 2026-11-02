"""Default launch behaviour without opening a window or starting a receiver."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tray_app.app import App, parse_launch_args


class LaunchTests(unittest.TestCase):
    def app(self, interface):
        app = App.__new__(App)
        app.config = {'interface': interface}
        app.root = SimpleNamespace(after=Mock())
        app.settings_dialog = Mock()
        app.run_operation = Mock()
        return app

    def run_scheduled(self, app):
        for call in app.root.after.call_args_list:
            call.args[1]()

    def test_normal_launch_defaults_to_start(self):
        self.assertTrue(parse_launch_args([]).autostart)
        self.assertFalse(parse_launch_args(['--no-autostart']).autostart)

    def test_configured_launch_starts_without_opening_settings(self):
        app = self.app('{lan}')
        app.schedule_startup(show_settings=False, autostart=True)
        self.run_scheduled(app)
        app.run_operation.assert_called_once_with('start')
        app.settings_dialog.assert_not_called()

    def test_missing_interface_opens_settings_then_starts_once_after_save(self):
        app = self.app('')
        app.schedule_startup(show_settings=False, autostart=True)
        self.run_scheduled(app)
        app.settings_dialog.assert_called_once_with()
        app.run_operation.assert_not_called()
        app.config['interface'] = '{lan}'
        app.start_after_settings()
        app.start_after_settings()
        app.run_operation.assert_called_once_with('start')

    def test_opening_settings_does_not_suppress_default_start(self):
        app = self.app('{lan}')
        app.schedule_startup(show_settings=True, autostart=True)
        self.run_scheduled(app)
        app.settings_dialog.assert_called_once_with()
        app.run_operation.assert_called_once_with('start')

    def test_explicit_no_autostart_opens_only_requested_settings(self):
        app = self.app('{lan}')
        app.schedule_startup(show_settings=True, autostart=False)
        self.run_scheduled(app)
        app.settings_dialog.assert_called_once_with()
        app.run_operation.assert_not_called()
