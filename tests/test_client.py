# tests for client module
import os
import shutil
import tempfile
import unittest
from ulif.openoffice.client import convert_doc


class ConvertDocTests(unittest.TestCase):
    # tests for convert_doc function

    def setUp(self):
        self.rootdir = tempfile.mkdtemp()
        self.srcdir = os.path.join(self.rootdir, 'src')
        os.mkdir(self.srcdir)
        self.cachedir = os.path.join(self.rootdir, 'cache')
        os.mkdir(self.cachedir)
        self.resultdir = None
        self.src_doc = os.path.join(self.srcdir, 'sample.txt')
        open(self.src_doc, 'w').write('Hi there.')

    def tearDown(self):
        shutil.rmtree(self.rootdir)
        if self.resultdir is not None:
            shutil.rmtree(self.resultdir)

    def test_nocache(self):
        # by default we get a zip'd HTML representation
        result_path, cache_key, metadata = convert_doc(
            self.src_doc, options={}, cache_dir=None)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-16:] == '/sample.html.zip'
        assert cache_key is None  # no cache, no cache_key
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_cached(self):
        # with a cache_dir, the result is cached
        result_path, cache_key, metadata = convert_doc(
            self.src_doc, options={}, cache_dir=self.cachedir)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-16:] == '/sample.html.zip'
        # cache keys are same for equal input files
        assert cache_key == '164dfcf01584bd0e3595b62fb53cf12c_1_1'
        assert metadata == {'error': False, 'oocp_status': 0}

    def test_options(self):
        # options given are respected
        options = {'meta-procord': 'unzip,oocp',
                   'oocp-out-fmt': 'pdf'}
        result_path, cache_key, metadata = convert_doc(
            self.src_doc, options=options, cache_dir=None)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-11:] == '/sample.pdf'
        assert metadata == {'error': False, 'oocp_status': 0}
