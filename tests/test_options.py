# tests for options module
import unittest
from ulif.openoffice.options import Options, Argument, dict_to_argtuple
from ulif.openoffice.processor import DEFAULT_PROCORDER


class HelperTests(unittest.TestCase):
    # tests for option helpers
    def test_dict_to_argtuple(self):
        # we can turn dicts into lists of arguments
        assert dict_to_argtuple(
            {'x': '1', 'y': '2'}) == ('-x', '1', '-y', '2')
        assert dict_to_argtuple(
            {'y': '2', 'x': '1'}) == ('-x', '1', '-y', '2')


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


class OptionsTests(unittest.TestCase):
    # tests for ulif.openoffice Options
    def test_avail_procs(self):
        # Options provide a list of available processor opts
        opts = Options()
        avail_procs = opts.avail_procs
        core_procs = [
            'css_cleaner', 'error', 'html_cleaner', 'meta', 'oocp', 'tidy',
            'unzip', 'zip',
            ]
        for name in core_procs:
            assert name in avail_procs

    def test_no_options(self):
        opts = Options()
        # default values are set
        assert opts['meta_processor_order'] == DEFAULT_PROCORDER
        assert opts['oocp_output_format'] == 'html'

    def test_val_dict(self):
        # we can feed Options with a dict of keys/values
        opts = Options(val_dict=dict(x=1, oocp_output_format='pdf'))
        # default options are set
        assert opts['meta_processor_order'] == DEFAULT_PROCORDER
        # default options can be overridden
        assert opts['oocp_output_format'] == 'pdf'
        # non-processor opts can be set
        assert opts['x'] == 1

    def test_string_dict(self):
        # we can feed Options with a dict of keys/string-values
        opts = Options(string_dict={'oocp-pdf-version': 'yes'})
        # default options are set
        assert opts['meta_processor_order'] == DEFAULT_PROCORDER
        # default options can be overridden
        assert opts['oocp_pdf_version'] == True

    def test_val_dict_overrides_string_dict(self):
        # val_dict values will override string_dict values
        opts = Options(
            string_dict={'oocp-out-fmt': 'txt'},
            val_dict={'oocp_output_format': 'pdf'})
        assert opts['oocp_output_format'] == 'pdf'
