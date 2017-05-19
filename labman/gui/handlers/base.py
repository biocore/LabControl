# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import RequestHandler


class BaseHandler(RequestHandler):
    """Base class for all labman's handlers"""

    def get_current_user(self):
        """Get the current connected user"""
        # TODO: Use the coockies to obtain the current user_id and return
        # the current user object
        pass

    def write_error(self, status_code, **kwargs):
        """Tornado's error handling callback"""
        # TODO: Log error using our own logging system and render a custom
        # error page with useful error messages. This page is for unexpected
        # errors

    def head(self):
        """Adds proper response for head requests"""
        self.finish()


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html")


class NotFoundHandler(BaseHandler):
    """Handler for 404 errors"""
    def get(self):
        self.set_status(404)
        self.render("404.html")

    def head(self):
        self.set_status(404)
        self.finish()
