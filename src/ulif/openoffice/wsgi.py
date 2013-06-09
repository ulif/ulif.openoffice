##
## wsgi.py
##
## Copyright (C) 2013 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
"""
RESTful WSGI app
"""
import os
from routes import Mapper
from webob import Response, exc
from webob.dec import wsgify
from ulif.openoffice.cachemanager import CacheManager

mydocs = {}


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
        pass

    def new(self, req):
        # get a form to create a new doc
        template = open(
            os.path.join(self.template_dir, 'form_new.tpl')).read()
        return Response(template)

    def update(self, req):
        # put/update an existing doc
        pass

    def delete(self, req):
        # delete a doc
        pass

    def edit(self, req):
        # edit a doc
        pass

    def show(self, req):
        # show a doc
        pass


docconverter_app = RESTfulDocConverter


def make_docconverter_app(global_conf, **local_conf):
    return RESTfulDocConverter(**local_conf)
