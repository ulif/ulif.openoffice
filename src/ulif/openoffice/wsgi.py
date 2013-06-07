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
from routes import Mapper
from webob import Response, exc
from webob.dec import wsgify


class SampleApp(object):

    def __init__(self, file_path):
        self.file_path = file_path

    @wsgify
    def __call__(self, req):
        return Response('Hi!')


mydocs = {}


class RESTfulDocConverter(object):
    """A WSGI app that caches and converts office documents via LibreOffice.

    It acts as a RESTful document store that supports HTTP actions to
    add/modify/retrieve converted documents.
    """
    # cf: http://routes.readthedocs.org/en/latest/restful.html
    #     http://blog.ianbicking.org/2010/03/12/a-webob-app-example/
    map = Mapper()
    map.resource('doc', 'docs')

    def __init__(self, global_cfg=None, local_cfg=None):
        print global_cfg, local_cfg
        self.global_cfg = global_cfg
        self.local_cfg = local_cfg

    @wsgify
    def __call__(self, req):
        results = self.map.routematch(environ=req.environ)
        if not results:
            return exc.HTTPNotFound()
        match, route = results
        print "MATCH, ROUTE: ", match  # , dir(route)
        return getattr(self, match['action'])(req)
        return 'Ho!'

    def index(self, req):
        # get index of all docs
        return Response(str(mydocs.keys()))

    def create(self, req):
        # post a new doc
        pass

    def new(self, req):
        # get a form to create a new doc
        pass

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


def restful_doc_converter_factory(global_cfg, **local_cfg):
    return RESTfulDocConverter(global_cfg, local_cfg)
