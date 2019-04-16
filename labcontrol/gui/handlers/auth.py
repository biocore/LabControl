# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import HTTPError, authenticated
from tornado.escape import json_encode

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.user import User
from labcontrol.db.exceptions import (
    LabmanUnknownIdError, LabmanLoginError, LabmanLoginDisabledError)


class LoginHandler(BaseHandler):
    def get(self):
        self.redirect('/')

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
        except LabmanLoginDisabledError:
            error_msg = "User not allowed on this portal"

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


class AccessHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('access.html', users=User.list_users(),
                    access_users=User.list_users(access_only=True))

    @authenticated
    def post(self):
        email = self.get_argument('email')
        op = self.get_argument('operation')

        if op == 'grant':
            User(email).grant_access()
        elif op == 'revoke':
            User(email).revoke_access()
        else:
            raise HTTPError(400, 'Operation %s not recognized')

        self.finish()
