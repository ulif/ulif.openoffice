##
## htaccess.py
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
htaccess - Authenticate users against htaccess files

A plain WSGI middleware to authenticate users against regular
Apache-style htaccess files.

.. note:: This middleware does not support MD5 hashes.

"""
import crypt
import os
from hashlib import sha1
from paste.auth.basic import AuthBasicAuthenticator, AuthBasicHandler
from paste.httpheaders import AUTHORIZATION


def check_credentials(username, password, htaccess):
    """Check password for user `username` in `htaccess`.

    Check whether the file in path `htaccess` contains a line with a
    password for user `username`.

    The `password` is clear text, while `htaccess` contains an
    encrypted (or plain text) password.

    We support `crypt`, `SHA1` and plain text passwords in
    htaccess. `MD5` is not supported as the Apache algorithm for MD5
    in htaccess files differs significantly from standard MD5 and is
    not available in Python standard libs.

    The given `htaccess` file can be modified with the standard Apache
    `htpasswd` command (as long as you do not create MD5 entries).
    """
    if not os.path.isfile(htaccess):
        return False
    with open(htaccess, 'rb') as f:
        for line in f:
            line = line.strip().split(':', 1)
            if len(line) != 2:
                continue
            user, encrypted = line
            if user != username:
                continue
            if encrypted.startswith('{SHA}'):                  # SHA1
                hash = sha1(password).digest().encode('base64')[:-1]
                if encrypted[5:] == hash:
                    return True
                return False
            if crypt.crypt(password, encrypted) == encrypted:  # crypt
                return True
            if encrypted == password:                          # plain
                return True
            return False
    return False


class HtaccessAuthenticator(AuthBasicAuthenticator):

    def __init__(self, realm, htaccess):
        self.realm = realm
        self.htaccess = htaccess

    def authenticate(self, environ):
        authorization = AUTHORIZATION(environ)
        if not authorization:
            return self.build_authentication()
        (authmeth, auth) = authorization.split(' ', 1)
        if 'basic' != authmeth.lower():
            return self.build_authentication()
        auth = auth.strip().decode('base64')
        username, password = auth.split(':', 1)
        if check_credentials(username, password, self.htaccess):
            return username
        return self.build_authentication()

    __call__ = authenticate


class HtaccessHandler(AuthBasicHandler):

    def __init__(self, application, realm, htaccess):
        self.application = application
        self.authenticate = HtaccessAuthenticator(realm, htaccess)


htaccess_middleware = HtaccessHandler


def make_htaccess(app, global_conf, realm, htaccess, **kw):
    """`Paste` plugin providing the Htaccess evaluating middleware.

    `realm` -
        The realm for which basic auth access is granted.

    `htaccess` -
        Path to an Apache htacces-style file.
    """
    assert os.path.isfile(htaccess), "htaccess must be an existing file"
    return HtaccessHandler(app, realm, htaccess)
