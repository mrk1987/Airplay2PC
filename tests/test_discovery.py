"""Check receiver cleanup without opening sockets or audio devices."""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest


class DiscoveryTests(unittest.TestCase):
    def unregister(self):
        receiver = Path(__file__).resolve().parents[1] / 'vendor/airplay2-receiver/ap2-receiver.py'
        tree = ast.parse(receiver.read_text(encoding='utf-8'))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'unregister_mdns')
        context = {'SCR_LOG': logging.getLogger('discovery-test'),
                   'NonUniqueNameException': type('NameConflict', (Exception,), {})}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(receiver), 'exec'), context)
        return context['unregister_mdns']

    def test_goodbye_completes_before_close(self):
        events = []
        info = object()
        service = SimpleNamespace(unregister_service=lambda value: events.append(('goodbye', value)),
                                  close=lambda: events.append(('close', None)))
        self.unregister()(service, info)
        self.assertEqual(events, [('goodbye', info), ('close', None)])

    def test_close_still_runs_when_unregister_fails(self):
        events = []
        def fail(info):
            raise OSError('test failure')
        service = SimpleNamespace(unregister_service=fail, close=lambda: events.append('closed'))
        with self.assertRaisesRegex(OSError, 'test failure'):
            self.unregister()(service, object())
        self.assertEqual(events, ['closed'])
