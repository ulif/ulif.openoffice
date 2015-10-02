# tests for wsgi module
import os
import pytest
import shutil
import tempfile
import unittest
import zipfile
from paste.deploy import loadapp
from webob import Request
from ulif.openoffice.cachemanager import get_marker
from ulif.openoffice.wsgi import (
    RESTfulDocConverter, FileIterator, FileIterable, get_mimetype
    )

pytestmark = pytest.mark.wsgi


@pytest.fixture(scope="function")
def iter_path(tmpdir):
    tmpdir.join("iter.test").write(b"0123456789")
    return str(tmpdir.join("iter.test"))


def is_zipfile_with_file(workdir, content, filename="sample.html"):
    """Assert that `content` contains a zipfile containing `filename`.

    `workdir` should be a `py.local` path where we can create files in.
    """
    content_file = workdir / "myresult.zip"
    content_file.write_binary(content)
    assert zipfile.is_zipfile(str(content_file))
    return filename in zipfile.ZipFile(str(content_file), "r").namelist()


class TestGetMimetype(object):
    # tests for get_mimetype()
    def test_nofilename(self):
        assert get_mimetype(None) == 'application/octet-stream'

    def test_nofile(self):
        assert get_mimetype('not-a-file') == 'application/octet-stream'

    def test_txtfile(self):
        assert get_mimetype('file.txt') == 'text/plain'

    def test_jpgfile(self):
        assert get_mimetype('file.jpg') == 'image/jpeg'

    def test_zipfile(self):
        assert get_mimetype('file.zip') == 'application/zip'

    def test_unknownfile(self):
        assert get_mimetype('unknown.type') == 'application/octet-stream'


class TestFileIterator(object):

    def test_empty_file(self, tmpdir):
        tmpdir.join("iter.test").write("")
        fi = FileIterator(str(tmpdir / "iter.test"), None, None)
        with pytest.raises(StopIteration):
            next(iter(fi))

    def test_start(self, iter_path):
        fi = FileIterator(iter_path, 4, None)
        assert b'456789' == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_stop(self, iter_path):
        fi = FileIterator(iter_path, 0, 4)
        assert b'0123' == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_start_and_stop(self, iter_path):
        fi = FileIterator(iter_path, 2, 6)
        assert b'2345' == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_multiple_reads(self, iter_path):
        block = b'x' * FileIterator.chunk_size
        with open(iter_path, 'wb') as fd:
            fd.write(2 * block)
        fi = FileIterator(iter_path)
        assert block == next(fi)
        assert block == next(fi)
        with pytest.raises(StopIteration):
            next(fi)

    def test_start_bigger_than_end(self, iter_path):
        fi = FileIterator(iter_path, 2, 1)
        with pytest.raises(StopIteration):
            next(fi)

    def test_end_is_zero(self, iter_path):
        fi = FileIterator(iter_path, 0, 0)
        with pytest.raises(StopIteration):
            next(fi)


class TestFileIterable(object):

    def test_range(self, iter_path):
        fi = FileIterable(iter_path)
        assert [b'234'] == list(fi.app_iter_range(2, 5))
        assert [b'67'] == list(fi.app_iter_range(6, 8))


class TestDocConverterFunctional(object):

    def test_restful_doc_converter(self):
        # we can create a RESTful sample app
        app = RESTfulDocConverter()
        req = Request.blank('http://localhost/test.html')
        resp = app(req)
        assert resp.status == "404 Not Found"

    def test_restful_doc_converter_simple_get(self):
        # RESTful sample app handles simple GET
        app = RESTfulDocConverter()
        req = Request.blank('http://localhost/docs')
        resp = app(req)
        req = Request.blank('http://localhost/docs')
        resp = app(req)
        assert resp.status == "200 OK"

    def test_paste_deploy_loader(self, docconv_env):
        # we can find the docconverter via paste.deploy plugin
        app = loadapp('config:%s' % (docconv_env / "sample1.ini"))
        assert isinstance(app, RESTfulDocConverter)
        assert app.cache_dir is None

    def test_paste_deploy_options(self, docconv_env):
        # we can set options via paste.deploy
        app = loadapp('config:%s' % (docconv_env / "paste.ini"))
        assert isinstance(app, RESTfulDocConverter)
        assert app.cache_dir == str(docconv_env / "cache")

    def test_new(self, docconv_env):
        # we can get a form for sending new docs
        app = RESTfulDocConverter(cache_dir=str(docconv_env / "cache"))
        req = Request.blank('http://localhost/docs/new')
        resp = app(req)
        assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert b'action="/docs"' in resp.body

    def test_create_with_cache(self, docconv_env):
        # we can trigger conversions that will be cached
        app = RESTfulDocConverter(cache_dir=str(docconv_env / "cache"))
        req = Request.blank(
            'http://localhost/docs',
            POST=dict(doc=('sample.txt', 'Hi there!'),
                      CREATE='Send',
                      )
            )
        resp = app(req)
        # we get a location header
        assert resp.headers['Location'] == (
            'http://localhost:80/docs/396199333edbf40ad43e62a1c1397793_1_1')
        assert resp.status == "201 Created"
        assert resp.headers['Content-Type'] == 'application/zip'
        assert is_zipfile_with_file(docconv_env, resp.body)

    def test_create_without_cache(self, docconv_env):
        # we can convert docs without cache but won't get a GET location
        app = RESTfulDocConverter(cache_dir=None)
        req = Request.blank(
            'http://localhost/docs',
            POST=dict(doc=('sample.txt', 'Hi there!'),
                      CREATE='Send',
                      )
            )
        resp = app(req)
        assert "Location" not in resp.headers
        # instead of 201 Created we get 200 Ok
        assert resp.status.lower() == "200 ok"
        assert resp.headers["Content-Type"] == "application/zip"
        assert is_zipfile_with_file(docconv_env, resp.body)

    def test_create_out_fmt_respected(self, docconv_env):
        # a single out_fmt option will result in appropriate output format
        # (the normal option name would be 'oocp.out_fmt')
        app = RESTfulDocConverter(cache_dir=str(docconv_env / "cache"))
        myform = dict(
            doc=('sample.txt', 'Hi there!'),
            CREATE='Send', out_fmt='pdf',
            )
        req = Request.blank('http://localhost/docs', POST=myform)
        resp = app(req)
        # we get a location header
        assert resp.headers["Location"] == (
            'http://localhost:80/docs/396199333edbf40ad43e62a1c1397793_1_1')
        assert resp.status == "201 Created"
        assert resp.headers['Content-Type'] == 'application/zip'
        assert is_zipfile_with_file(
            docconv_env, resp.body, filename="sample.pdf")

    def test_show_yet_uncached_doc(self, docconv_env):
        # a yet uncached doc results in 404
        app = RESTfulDocConverter(cache_dir=str(docconv_env / "cache"))
        url = 'http://localhost/docs/NOT-A-VALID-DOCID'
        resp = app(Request.blank(url))
        assert resp.status == "404 Not Found"

    def test_show_with_cache(self, docconv_env):
        # we can retrieve cached files
        app = RESTfulDocConverter(cache_dir=str(docconv_env / "cache"))
        docconv_env.join("sample_in.txt").write("Fake source.")
        docconv_env.join("sample_out.pdf").write("Fake result.")
        marker = get_marker(dict(foo='bar', bar='baz'))
        doc_id = app.cache_manager.register_doc(
            source_path=str(docconv_env.join("sample_in.txt")),
            to_cache=str(docconv_env.join("sample_out.pdf")),
            repr_key=marker)
        assert doc_id == '3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1'
        url = 'http://localhost/docs/3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1'
        req = Request.blank(url)
        resp = app(req)
        assert resp.status == "200 OK"
        assert resp.content_type == "application/pdf"


@pytest.fixture(scope="function")
def docconv_env(tmpdir):
    paste_conf1 = open(os.path.join(
        os.path.dirname(__file__), "input", "sample1.ini")).read()
    tmpdir.join("sample1.ini").write(paste_conf1)
    cache_dir = tmpdir / "cache"
    paste_conf2 = open(os.path.join(
        os.path.dirname(__file__), "input", "sample2.ini")).read()
    tmpdir.join("paste.ini").write(
        paste_conf2.replace("/tmp/mycache", str(cache_dir)))
    return tmpdir

class DocConverterFunctionalTestCase(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.cachedir = os.path.join(self.workdir, 'cache')
        self.inputdir = os.path.join(os.path.dirname(__file__), 'input')
        self.paste_conf1 = os.path.join(self.inputdir, 'sample1.ini')
        self.paste_conf2 = os.path.join(self.inputdir, 'sample2.ini')
        # create local paste conf with local cachedir set
        self.paste_conf_tests = os.path.join(self.workdir, 'paste.ini')
        paste_conf = open(self.paste_conf2, 'r').read().replace(
            '/tmp/mycache', self.cachedir)
        with open(self.paste_conf_tests, 'w') as fd:
            fd.write(paste_conf)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_show_with_cache(self):
        # we can retrieve cached files
        app = RESTfulDocConverter(cache_dir=self.cachedir)
        fake_src = os.path.join(self.workdir, 'sample_in.txt')
        fake_result = os.path.join(self.workdir, 'sample_out.pdf')
        with open(fake_src, 'w') as fd:
            fd.write('Fake source.')
        with open(fake_result, 'w') as fd:
            fd.write('Fake result.')
        marker = get_marker(dict(foo='bar', bar='baz'))
        doc_id = app.cache_manager.register_doc(
            source_path=fake_src, to_cache=fake_result, repr_key=marker)
        self.assertEqual('3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1', doc_id)
        doc_id = '%s_%s' % (doc_id, marker)
        url = 'http://localhost/docs/3fe6f0d4c5e62ff9a1deca0a8a65fe8d_1_1'
        req = Request.blank(url)
        resp = app(req)
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.content_type, 'application/pdf')
