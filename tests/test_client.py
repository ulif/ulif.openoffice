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

    def tearDown(self):
        shutil.rmtree(self.rootdir)
        if self.resultdir is not None:
            shutil.rmtree(self.resultdir)

    def test_nocache(self):
        # by default we get a zip'd HTML representation
        src_doc = os.path.join(self.srcdir, 'sample.txt')
        open(src_doc, 'w').write('Hi there.')
        result_path, cache_key, metadata = convert_doc(
            src_doc, options={}, cache_dir=None)
        self.resultdir = os.path.dirname(result_path)
        assert result_path[-16:] == '/sample.html.zip'
        assert cache_key is None  # no cache, no cache_key
        assert metadata == {'error': False, 'oocp_status': 0}
