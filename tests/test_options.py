# tests for options module
import unittest
from ulif.openoffice.options import Argument


class ArgumentTests(unittest.TestCase):
    # tests for ulif.openoffice Argument
    def test_regular(self):
        # normally we pass in args and keywords
        arg = Argument(
            '-myproc-opt1', '--myproc-option1', choice=[1, 2, 3])
        assert arg.short_name == '-myproc-opt1'
        assert arg.long_name == '--myproc-option1'
        assert arg.keywords['choice'] == [1, 2, 3]

    def test_wrong_option_name_format(self):
        # we check format of options. They must start with dashes.
        # short name must have format '-XXX'
        self.assertRaises(
            ValueError, Argument, 'opt-name-wo-dash')
        # long name must have format '--XXX'
        self.assertRaises(  # missing dash in long name
            ValueError, Argument, '-myproc-opt1', '-myproc-option1')
