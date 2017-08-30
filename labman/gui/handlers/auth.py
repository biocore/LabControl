# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.escape import json_encode

from labman.gui.handlers.base import BaseHandler
from labman.db.user import User
from labman.db.exceptions import LabmanUnknownIdError, LabmanLoginError


class LoginHandler(BaseHandler):
    def post(self):
        username = self.get_argument('username', '').strip().lower()
        passwd = self.get_argument('password', '')

        error_msg = ""
        user = None
        try:
            user = User.login(username, passwd)
        except LabmanUnknownIdError:
            error_msg = "Unknown user name"
        except LabmanLoginError:
            error_msg = "Incorrect password"

        if user:
            self.set_current_user(username)
            self.redirect("/")
        else:
            self.render("index.html", message=error_msg, level='danger')

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", json_encode(user))
        else:
            self.clear_cookie("user")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect("/")
