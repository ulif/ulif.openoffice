# tests for client module
import filecmp
import os
import pytest
import shutil
import tempfile
import unittest
from ulif.openoffice.client import convert_doc, Client, main
from ulif.openoffice.options import ArgumentParserError
from ulif.openoffice.testing import ConvertLogCatcher


class ClientTestsSetup(unittest.TestCase):
    # a setup for client tests
    def setUp(self):
        self.rootdir = tempfile.mkdtemp()
        self.srcdir = os.path.join(self.rootdir, 'src')
        os.mkdir(self.srcdir)
        self.cachedir = os.path.join(self.rootdir, 'cache')
        os.mkdir(self.cachedir)
        self.resultdir = None
        self.src_doc = os.path.join(self.srcdir, 'sample.txt')
        with open(self.src_doc, 'w') as fd:
            fd.write('Hi there.')
        self.entry_wd = os.getcwd()
        self.log_catcher = ConvertLogCatcher()

    def tearDown(self):
        try:
            if os.getcwd() != self.entry_wd:
                os.chdir(self.entry_wd)
        except OSError:
            # might happen if resultdir was deleted already
            os.chdir(self.entry_wd)
        shutil.rmtree(self.rootdir)
        if self.resultdir is not None:
            shutil.rmtree(self.resultdir)


class TestConvertDoc(object):
    # tests for convert_doc function

    def test_basename_only_input(self, workdir, conv_logger, lo_server):
        # also source paths with a basename only are accepted
        options = {'meta-procord': 'oocp',
                   'oocp-out-fmt': 'pdf'}
        # change to the dir where the src doc resides
        workdir.join('src').chdir()
        src_doc = workdir.join('src').join('sample.txt')
        result_path, cache_key, metadata = convert_doc(
            os.path.basename(str(src_doc)), options=options, cache_dir=None)
        assert "Cmd result: 0" in conv_logger.getvalue()
        assert os.path.basename(result_path) == "sample.pdf"
        assert metadata == {'error': False, 'oocp_status': 0}
        # the original source doc still exists
        assert src_doc.exists()

    def test_nocache(self, workdir, conv_logger, lo_server):
        # by default we get a zip'd HTML representation
        workdir.join('src').chdir()
        src_doc = workdir.join('src').join('sample.txt')
        result_path, cache_key, metadata = convert_doc(
            os.path.basename(str(src_doc)), options={}, cache_dir=None)
        assert 'Cmd result: 0' in conv_logger.getvalue()
        assert os.path.basename(result_path) == "sample.html.zip"
        assert cache_key is None  # no cache, no cache_key
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_cached(self, workdir, conv_logger, lo_server):
        # with a cache_dir, the result is cached
        workdir.join('src').chdir()
        src_doc = workdir.join('src').join('sample.txt')
        result_path, cache_key, metadata = convert_doc(
            os.path.basename(str(src_doc)), options={},
            cache_dir=str(workdir / "cache"))
        assert os.path.basename(result_path) == "sample.html.zip"
        # cache keys are same for equal input files
        assert cache_key == '396199333edbf40ad43e62a1c1397793_1_1'
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_options(self, workdir, lo_server):
        # options given are respected
        workdir.join('src').chdir()
        src_doc = workdir.join('src').join('sample.txt')
        options = {'meta-procord': 'unzip,oocp',
                   'oocp-out-fmt': 'pdf'}
        result_path, cache_key, metadata = convert_doc(
            os.path.basename(str(src_doc)), options=options, cache_dir=None)
        assert os.path.basename(result_path) == "sample.pdf"
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_only_one_file_considered_as_input(self, workdir, lo_server):
        # we only consider one input file, not other files in same dir
        options = {
            'meta-procord': 'oocp',
            'oocp-out-fmt': 'html'
            }
        workdir.join('src').chdir()
        src_doc = workdir.join('src').join('sample.txt')
        workdir.join('src').join('other.foo').write('some-content')
        result_path, cache_key, metadata = convert_doc(
            os.path.basename(str(src_doc)), options=options, cache_dir=None)
        result_list = str(os.listdir(os.path.dirname(result_path)))
        assert 'other.foo' not in result_list
        assert 'sample.html' in result_list


class ClientEnv(object):
    def __init__(self, workdir):
        self.workdir = workdir
        self.src_doc = str(workdir / 'src' / 'sample.txt')
        self.cache_dir = str(workdir / 'cache')


@pytest.fixture
def client_env(workdir, lo_server):
    return ClientEnv(workdir)


class TestClient(object):
    # tests for API Client

    def test_convert(self, client_env):
        client = Client()
        result_path, cache_key, metadata = client.convert(client_env.src_doc)
        assert result_path.endswith('/sample.html.zip')
        assert os.path.isfile(result_path)
        assert cache_key is None  # no cache, no cache_key
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_get_cached_no_file(self, client_env):
        # when asking for cached files we cope with nonexistent docs
        client = Client(cache_dir=client_env.cache_dir)
        assert client.get_cached(
            '396199333edbf40ad43e62a1c1397793_1_1') is None

    def test_get_cached(self, client_env):
        # we can get an already cached doc
        client = Client(cache_dir=client_env.cache_dir)
        result_path, cache_key, metadata = client.convert(client_env.src_doc)
        assert cache_key == '396199333edbf40ad43e62a1c1397793_1_1'
        cached_path = client.get_cached(cache_key)
        assert filecmp.cmp(result_path, cached_path, shallow=False)
        assert client_env.cache_dir in cached_path

    def test_options(self, client_env):
        # we can pass in options
        client = Client()
        options = {'oocp-out-fmt': 'pdf', 'meta-procord': 'oocp'}
        result_path, cache_key, metadata = client.convert(
            client_env.src_doc, options=options)
        assert result_path.endswith('/sample.pdf')
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_argument_error(self, client_env):
        # wrong args lead to ArgumentErrors
        client = Client()
        # illegal output format and not existing processors
        options = {'oocp-out-fmt': 'foo', 'meta-procord': 'foo,bar'}
        with pytest.raises(ArgumentParserError):
            client.convert(client_env.src_doc, options=options)


class ClientTests(ClientTestsSetup):
    # tests for API Client

    def test_argument_error(self):
        # wrong args lead to ArgumentErrors
        client = Client()
        options = {'oocp-out-fmt': 'foo', 'meta-procord': 'foo,bar'}
        self.assertRaises(
            ArgumentParserError,
            client.convert, self.src_doc, options=options)

    def test_get_cached_by_source_no_file(self):
        # we cannot get a cached file not cached before
        client = Client(cache_dir=self.cachedir)
        cached_path, cache_key = client.get_cached_by_source(self.src_doc)
        assert cached_path is None
        assert cache_key is None

    def test_get_cached_by_source_no_cache_dir(self):
        # we cannot get a cached file if w/o cache_dir set
        client = Client()
        cached_path, cache_key = client.get_cached_by_source(self.src_doc)
        assert cached_path is None
        assert cache_key is None

    def test_get_cached_by_source(self):
        # we can get a file when cached and by source/options
        client = Client(cache_dir=self.cachedir)
        result_path, cache_key, metadata = client.convert(self.src_doc)
        self.resultdir = os.path.dirname(result_path)  # for cleanup
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'
        cached_path, cache_key = client.get_cached_by_source(self.src_doc)
        assert filecmp.cmp(result_path, cached_path, shallow=False)
        assert self.cachedir in cached_path
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'


class MainClientTests(ClientTestsSetup):
    # tests for the client modules `main` function

    @pytest.fixture(autouse=True)
    def mycapsys(self, capsys):
        self.mycapsys = capsys

    def test_convert_regular(self):
        # we can do a regular conversion
        main(
            [
                '-meta-procord', 'oocp',
                '-oocp-out-fmt', 'pdf',
                self.src_doc
            ])
        out, err = self.mycapsys.readouterr()
        outfile_path = out[10:-1]
        self.resultdir = os.path.dirname(outfile_path)   # for cleanup
        assert out.startswith('RESULT in')
        assert os.path.exists(outfile_path)
        assert os.path.isfile(outfile_path)
        assert outfile_path.endswith('/sample.pdf')

    def test_help(self):
        # we can get help
        try:
            main(['--help'])
        except SystemExit:
            pass  # help causes sys.exit(1)
        out, err = self.mycapsys.readouterr()
        assert out[:43] == u"usage: oooclient [-h] [--cachedir CACHEDIR]"

    def test_argument_error(self):
        # argument errors are shown and explained
        try:
            main(['--not-existing-arg', self.src_doc])
        except SystemExit:
            pass  # errors cause sys.exit()
        out, err = self.mycapsys.readouterr()
        assert err.endswith(
            'error: unrecognized arguments: --not-existing-arg\n')
