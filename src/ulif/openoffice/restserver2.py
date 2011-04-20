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

class Resource(object):

    def __init__(self, content):
        self.content = content

    exposed = True

    def GET(self, num=None):
        return self.to_html().replace('</html>', '%s</html>' % num)

    def PUT(self):
        self.content = self.from_html(cherrypy.request.body.read())

    def to_html(self):
        html_item = lambda (name,value): '<div><a href="%s">%s</a></div>' % (
            value, name)
        items = map(html_item, self.content.items())
        items = ''.join(items)
        return '<html>%s</html>' % items

    @staticmethod
    def from_html(data):
        pattern = re.compile(r'\<div\>(?P<name>.*?)\:(?P<value>.*?)\</div\>')
        items = [match.groups() for match in pattern.finditer(data)]
        return dict(items)

class ResourceIndex(Resource):
    def to_html(self):
        html_item = lambda (
            name,value
            ): '<div><a href="%s">%s</a></div>' % (
            value, name)
        items = map(html_item, self.content.items())
        items = ''.join(items)
        return '<html>%s</html>Hello World!' % items

class Root(object):
    sidewinder = Resource({'color': 'red', 'weight': 176, 'type': 'stable'})
    teebird = Resource({'color': 'green', 'weight': 173, 'type': 'overstable'})
    blowfly = Resource({'color': 'purple', 'weight': 169, 'type': 'putter'})
    index = ResourceIndex({'sidewinder': 'sidewinder',
                            'teebird': 'teebird',
                            'blowfly': 'blowfly'}
                           )

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
