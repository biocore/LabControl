# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import re
from datetime import datetime
from traceback import format_exception

from tornado.web import RequestHandler, authenticated

from labman.db.user import User


class BaseHandler(RequestHandler):
    """Base class for all labman's handlers"""

    def get_current_user(self):
        """Get the current connected user"""
        username = self.get_secure_cookie("user")
        if username is not None:
            # strip off quotes added by get_secure_cookie and decode
            # becuase it is stored as character varying in the DB
            return User(username.strip(b"\"' ").decode())
        else:
            self.clear_cookie("user")
            return None

    def write_error(self, status_code, **kwargs):
        """Tornado's error handling callback"""
        # TODO: Log error using our own logging system and render a custom
        # error page with useful error messages. This page is for unexpected
        # errors
        if status_code == 404:
            # Just use the 404 page as the error
            self.render("404.html")
            return

        if "exc_info" in kwargs:
            exc_info = kwargs["exc_info"]
            trace_info = ''.join(
                ["%s<br />" % line for line in format_exception(*exc_info)])
            error = exc_info[1]
        else:
            error = "No exc_info generated. Status code: %s" % status_code
            trace_info = "Missing trace info"

        request_info = ''.join(
            ["<strong>%s</strong>: %s<br/>" % (k, self.request.__dict__[k])
             for k in self.request.__dict__.keys()])

        self.render('error.html', error=error, trace_info=trace_info,
                    request_info=request_info)

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


class BaseDownloadHandler(BaseHandler):
    @staticmethod
    def generate_file_name(name_pieces, process, extension="txt"):
        date_str = datetime.strftime(process.date,
                                     process.get_filename_date_format())
        munged_name_pieces = [re.sub('\\s+', '_', x) for x in name_pieces]
        munged_name_pieces.insert(0, date_str)
        name_str = "_".join(munged_name_pieces)
        result = name_str + "." + extension
        return result

    @authenticated
    def deliver_text(self, name_pieces, process, text, extension="txt"):
        output_name = self.generate_file_name(name_pieces, process, extension)
        self._deliver_file(text, output_name, 'text/csv')

    @authenticated
    def deliver_zip(self, name_pieces, process, archive, extension="zip"):
        output_name = self.generate_file_name(name_pieces, process, extension)
        self._deliver_file(archive, output_name, 'application/zip')

    @authenticated
    def _deliver_file(self, contents, file_name, content_type):
        self.set_header('Content-Type', content_type)
        self.set_header('Expires', '0')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Content-Disposition', 'attachment; filename='
                        '%s' % file_name)
        self.write(contents)
        self.finish()
