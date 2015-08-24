#
# wsgi.py
#
# Copyright (C) 2013, 2015 Uli Fouquet
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
"""
RESTful WSGI app
"""
import os
import mimetypes
import tempfile
from routes import Mapper
from routes.util import URLGenerator
from webob import Response, exc
from webob.dec import wsgify
from ulif.openoffice.cachemanager import CacheManager
from ulif.openoffice.client import convert_doc
from ulif.openoffice.helpers import basestring


mydocs = {}


def get_mimetype(filename):
    if not isinstance(filename, basestring):
        return 'application/octet-stream'
    type, encoding = mimetypes.guess_type(filename)
    # We'll ignore encoding, even though we shouldn't really
    return type or 'application/octet-stream'


class FileIterable(object):
    """A webob compatible file iterable.

    `start` and `stop` tell where to start/stop reading. This iterable
    reads files in chunks to reduce memory load when reading large
    files.

    Supports streaming ranges.

    Cf. http://docs.webob.org/en/latest/file-example.html
    """
    def __init__(self, filename, start=0, stop=None):
        self.filename = filename
        self.start = start
        self.stop = stop

    def __iter__(self):
        return FileIterator(self.filename, self.start, self.stop)

    def app_iter_range(self, start, stop):
        return self.__class__(self.filename, start, stop)


class FileIterator(object):
    """An iterator that reads files and returns them in chunks.

    The absolute start/stop position in the file can be passed
    optionally. Used by :class:`FileIterable` to return streamed
    files.

    Cf. http://docs.webob.org/en/latest/file-example.html
    """
    #: Size of chunks read when processing files.
    chunk_size = 4096

    def __init__(self, filename, start=0, stop=None):
        self.filename = filename
        self.fileobj = open(self.filename, 'rb')
        if start:
            self.fileobj.seek(start)
        if stop is not None:
            self.length = stop - start
        else:
            self.length = None

    def __iter__(self):
        return self

    def next(self):
        if self.length is not None and self.length <= 0:
            raise StopIteration
        chunk = self.fileobj.read(self.chunk_size)
        if not chunk:
            raise StopIteration
        if self.length is not None:
            self.length -= len(chunk)
            if self.length < 0:
                # Chop off the extra:
                chunk = chunk[:self.length]
        return chunk

    __next__ = next  # py3 compat


def make_response(filename):
    res = Response(content_type=get_mimetype(filename))
    res.app_iter = FileIterable(filename)
    res.content_length = os.path.getsize(filename)
    res.last_modified = os.path.getmtime(filename)
    res.etag = '%s-%s-%s' % (
        os.path.getmtime(filename),
        os.path.getsize(filename),
        hash(filename))
    return res


class RESTfulDocConverter(object):
    """A WSGI app that caches and converts office documents via LibreOffice.

    It acts as a RESTful document store that supports HTTP actions to
    add/modify/retrieve converted documents.

    Accepted arguments:

    - `cache_dir`:
        Path to a directory, where cached files can be stored. The
        directory is created if it does not exist.

    """
    # cf: http://routes.readthedocs.org/en/latest/restful.html
    #     http://blog.ianbicking.org/2010/03/12/a-webob-app-example/
    map = Mapper()
    map.resource('doc', 'docs')

    #: A cache manager instance.
    cache_manager = None
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir
        self.cache_manager = None
        if self.cache_dir is not None:
            self.cache_manager = CacheManager(self.cache_dir)

    def _url(self, req, *args, **kw):
        """Generate an URL pointing to some REST service.

        `req` is the current request.

        Arguments and keywords are passed on to the generated
        :class:`routes.util.URLGenerator` instance. So you can use it
        like the `url` method described in the `routes` docs, except
        that you have to pass in the `req` parameter first.
        """
        url = URLGenerator(self.map, req.environ)
        return url(*args, **kw)

    @wsgify
    def __call__(self, req):
        results = self.map.routematch(environ=req.environ)
        if not results:
            return exc.HTTPNotFound()
        match, route = results
        return getattr(self, match['action'])(req)

    def index(self, req):
        # get index of all docs
        return Response(str(mydocs.keys()))

    def create(self, req):
        # post a new doc
        options = dict([(name, val) for name, val in req.params.items()
                        if name not in ('CREATE', 'doc', 'docid')])
        if 'out_fmt' in req.params.keys():
            options['oocp-out-fmt'] = options['out_fmt']
            del options['out_fmt']
        if 'CREATE' in req.params.keys():
            if options.get('oocp-out-fmt', 'html') == 'pdf':
                options['meta-procord'] = 'unzip,oocp,zip'
        doc = req.POST['doc']
        # write doc to filesystem
        tmp_dir = tempfile.mkdtemp()
        src_path = os.path.join(tmp_dir, doc.filename)
        with open(src_path, 'wb') as f:
            for chunk in iter(lambda: doc.file.read(8 * 1024), b''):
                f.write(chunk)
        # do the conversion
        result_path, id_tag, metadata = convert_doc(
            src_path, options, self.cache_dir)
        # deliver the created file
        resp = make_response(result_path)
        if id_tag is not None:
            # we can only signal new resources if cache is enabled
            resp.status = '201 Created'
            resp.location = self._url(req, 'doc', id=id_tag, qualified=True)
        return resp

    def new(self, req):
        # get a form to create a new doc
        template = open(
            os.path.join(self.template_dir, 'form_new.tpl')).read()
        template = template.format(target_url=self._url(req, 'docs'))
        return Response(template)

    def update(self, req):
        # put/update an existing doc
        pass  # pragma: no cover

    def delete(self, req):
        # delete a doc
        pass  # pragma: no cover

    def edit(self, req):
        # edit a doc
        pass  # pragma: no cover

    def show(self, req):
        # show a doc
        doc_id = req.path.split('/')[-1]
        result_path = self.cache_manager.get_cached_file(doc_id)
        if result_path is None:
            return exc.HTTPNotFound()
        return make_response(result_path)


docconverter_app = RESTfulDocConverter


def make_docconverter_app(global_conf, **local_conf):
    return RESTfulDocConverter(**local_conf)
