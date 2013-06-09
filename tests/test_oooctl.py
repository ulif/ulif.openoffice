# tests for oooctl module
import unittest
from ulif.openoffice.oooctl import get_options


class OOOctlTests(unittest.TestCase):

    def test_get_options(self):
        cmd, options = get_options(['fakeoooctl', 'start'])
        self.assertEqual(cmd, 'start')
        self.assertTrue(options.binarypath is not None)
        self.assertEqual(options.pidfile, '/tmp/ooodaemon.pid')
        return

    def test_get_options_no_argv(self):
        try:
            get_options(argv=[])
        except(SystemExit) as err:
            self.assertEqual(err.code, 2)
        else:
            self.fail('SystemExit exception expected.')
        return

    def test_get_options_invalid_command(self):
        try:
            get_options(argv=['fakeoooctl', 'maybestart'])
        except(SystemExit) as err:
            self.assertEqual(err.code, 2)
        else:
            self.fail('SystemExit exception expected.')
        return

    def test_get_options_too_many_args(self):
        try:
            get_options(argv=['fakeoooctl', 'too', 'much'])
        except(SystemExit) as err:
            self.assertEqual(err.code, 2)
        else:
            self.fail('SystemExit exception expected.')
        return

    def test_get_options_invalid_binpath(self):
        # we should not pass an invalid path to executable
        try:
            get_options(argv=['fakeoooctl', '-b', 'invalid-path', 'start'])
        except(SystemExit) as err:
            self.assertEqual(err.code, 2)
        else:
            self.fail('SystemExit exception expected.')
        return
