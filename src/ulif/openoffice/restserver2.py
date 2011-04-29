##
## restserver2.py
## Login : <uli@pu.smp.net>
## Started on  Wed Apr 20 03:01:13 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
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
RESTful server (cherry.py flavour)
"""
import cherrypy
from ulif.openoffice.cachemanager import CacheManager

#class Resource(object):
#
#    def __init__(self, content):
#        self.content = content
#
#    exposed = True
#
#    def GET(self, num=None):
#        return self.to_html().replace('</html>', '%s</html>' % num)
#        return """
#        <html><body>
#            <form action="pdf" method="post" enctype="multipart/form-data">
#            filename: <input type="file" name="myFile"/><br/>
#            <input type="submit"/>
#            </form>
#        </body></html>
#        """

#        return self.to_html().replace('</html>', '%s</html>' % num)

#    def PUT(self):
#        self.content = self.from_html(cherrypy.request.body.read())

#    def to_html(self):
#        html_item = lambda (name,value): '<div><a href="%s">%s</a></div>' % (
#            value, name)
#        items = map(html_item, self.content.items())
#        items = ''.join(items)
#        return '<html>%s</html>' % items

#    @staticmethod
#    def from_html(data):
#        pattern = re.compile(r'\<div\>(?P<name>.*?)\:(?P<value>.*?)\</div\>')
#        items = [match.groups() for match in pattern.finditer(data)]
#        return dict(items)

#class ResourceIndex(Resource):
#    def to_html(self):
#        html_item = lambda (
#            name,value
#            ): '<div><a href="%s">%s</a></div>' % (
#            value, name)
#        items = map(html_item, self.content.items())
#        items = ''.join(items)
#        return '<html>%s</html>Hello World!' % items

#from cherrypy import cpg

#class Upload(object):
#    def to_html(self, myFile=None):
#        return """
#        <html><body>
#            myFile length: %s<br/>
#            myFile filename: %s<br/>
#            myFile mime-type: %s
#        </body></html>
#        """ % (
#            dir(myFile), myFile.filename, myFile.content_type
#            #cpg.request.filenameMap['myFile'],
#            #cpg.request.fileTypeMap['myFile']
#            )
#    def POST(self, myFile):
#        self.stuff = self.to_html(myFile=myFile)
#        return self.stuff
#        pass
#        #self.content = self.from_html(cherrypy.request.body.read())


        
        
#class PDFResource(object):
#    exposed = True
#    def __init__(self, content):
#        self.content = content

#    def POST(self, *args, **kw):
        
#        html_item = lambda (name,value): '<div><a href="%s">%s</a></div>' % (
#            value, name)
#        #items = map(html_item, self.content.items())
#        a = ('args', '%s %s' % (args, kw))
#        #print a
#        items = map(html_item, [('args', a)])
#        items = ''.join(items)
#        #import pdb; pdb.set_trace()
#        return '<html>%s</html>' % items #cherrypy.request.params #items

#    @staticmethod
#    def from_html(data):
#        pattern = re.compile(r'\<div\>(?P<name>.*?)\:(?P<value>.*?)\</div\>')
#        items = [match.groups() for match in pattern.finditer(data)]
#        return dict(items)

class DocumentRoot(object):
    exposed = True
    doc_ids = ['0', '23', '42']

    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        return

    def _cp_dispatch(self, vpath):
        if vpath:
            doc_id = vpath.pop(0)
            #cherrypy.request.params['doc_id'] = doc_id
            if doc_id == 'index':
                return DocumentIndex(cache_manager = self.cache_manager)
            return Document(doc_id, cache_manager=self.cache_manager)
            #if doc_id in self.doc_ids:
            #    return Document(doc_id)
            #elif doc_id == 'index':
            #    return DocumentIndex(self.doc_ids)
        if vpath:
            return getattr(self, vpath[0], None)
        return

    def GET(self):
        print 
        return "Hi from doc root"

    def POST(self, doc=None, SUBMIT=None):
        self.doc_ids.append(doc)
        return "Got %s" % self.doc_ids

class Document(object):
    def _cp_dispatch(self, vpath):
        return getattr(self, vpath[0], None)
    exposed = True

    def __init__(self, doc_id, cache_manager=None):
        self.cache_manager = None
        self.doc_id = doc_id
        return

    def GET(self):
        return "Hi from doc %s" % self.doc_id

class DocumentIndex(object):
    exposed = True
    def _cp_dispatch(self, vpath):
        return getattr(self, vpath[0], None)

    def __init__(self, cache_manager=None):
        self.ids = ids
        self.cache_manager = cache_manager

    def GET(self):
        return """
          <html>
           <body>
           Available IDs: %s <br />
           <form action="/docs" method="POST">
             ID: <input type="text" name="doc_id"> <br />
             <input type="submit" name="SUBMIT" value="Add">
           </form>
           </body>
          </html>
          """ % self.ids

class Root(object):
        
#    sidewinder = Resource({'color': 'red', 'weight': 176, 'type': 'stable'})
#    teebird = Resource({'color': 'green', 'weight': 173, 'type': 'overstable'})
#    blowfly = Resource({'color': 'purple', 'weight': 169, 'type': 'putter'})
#    index = ResourceIndex({'sidewinder': 'sidewinder',
#                            'teebird': 'teebird',
#                            'blowfly': 'blowfly'}
#                           )
#    pdf = PDFResource({})
    @property
    def docs(self):
        return DocumentRoot(cache_manager=self.cache_manager)
    #docs = DocumentRoot()

    def __init__(self, cachedir=None):
        self.cache_manager = None
        if cachedir is None:
            return
        self.cache_manager = CacheManager(cachedir)
        return
        
    #def default(self, doc_id=None):
    #    return 'Hi from default'

root = Root()
    
conf = {
    'global': {
        'server.socket_host': 'localhost',
        'server.socket_port': 8000,
        },
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }

def main():

    cherrypy.quickstart(Root(), '/', conf)
