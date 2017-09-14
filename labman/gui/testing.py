# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from urllib.parse import urlencode
from mock import Mock

from tornado.testing import AsyncHTTPTestCase

from labman.gui.webserver import Application
from labman.gui.handlers.base import BaseHandler
from labman.db.user import User


class TestHandlerBase(AsyncHTTPTestCase):
    app = Application()

    def get_app(self):
        BaseHandler.get_current_user = Mock(return_value=User("test@foo.bar"))
        self.app.settings['debug'] = False
        return self.app

    # helpers from http://www.peterbe.com/plog/tricks-asynchttpclient-tornado
    def get(self, url, data=None, headers=None, doseq=True):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data, doseq=doseq)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        return self._fetch(url, 'GET', headers=headers)

    def post(self, url, data, headers=None, doseq=True):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data, doseq=doseq)
        return self._fetch(url, 'POST', data, headers)

    def patch(self, url, data, headers=None, doseq=True):
        if isinstance(data, dict):
            data = urlencode(data, doseq=doseq)
        if '?' in url:
            url += '&%s' % data
        else:
            url += '?%s' % data
        return self._fetch(url, 'PATCH', data=data, headers=headers)

    def delete(self, url, data=None, headers=None, doseq=True):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data, doseq=doseq)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        return self._fetch(url, 'DELETE', headers=headers)

    def _fetch(self, url, method, data=None, headers=None):
        self.http_client.fetch(self.get_url(url), self.stop, method=method,
                               body=data, headers=headers)
        return self.wait(timeout=15)
