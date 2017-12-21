# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from os.path import dirname, join
from base64 import b64encode
from uuid import uuid4

import tornado

from labman.gui.handlers.base import IndexHandler, NotFoundHandler
from labman.gui.handlers.auth import LoginHandler, LogoutHandler
from labman.gui.handlers.plate import (
    PlateMapHandler, PlateNameHandler, PlateHandler, PlateLayoutHandler)
from labman.gui.handlers.study import (
    StudyListHandler, StudyHandler, StudySamplesHandler)
from labman.gui.handlers.sample import ControlSamplesHandler
from labman.gui.handlers.process_handlers import PROCESS_ENDPOINTS


class Application(tornado.web.Application):
    def __init__(self):
        # Get the path to the folder that contain the templates and the static
        # files (such as images, css and js)
        dirpath = dirname(__file__)
        templates_path = join(dirpath, 'templates')
        static_path = join(dirpath, 'static')

        handlers = [(r"/", IndexHandler),
                    (r"/static/(.*)", tornado.web.StaticFileHandler,
                    {"path": static_path}),
                    # Authorization handlers
                    (r"/auth/login/", LoginHandler),
                    (r"/auth/logout/", LogoutHandler),
                    # Plate handlers
                    (r"/plate/(.*)/layout", PlateLayoutHandler),
                    (r"/plate/(.*)/", PlateHandler),
                    (r"/plate", PlateMapHandler),
                    (r"/platename", PlateNameHandler),
                    # Study handlers
                    (r"/study_list", StudyListHandler),
                    (r"/study/(.*)/samples", StudySamplesHandler),
                    (r"/study/(.*)/", StudyHandler),
                    # Sample handlers
                    (r"/sample/control", ControlSamplesHandler)]

        # Add the process endpoints
        handlers.extend(PROCESS_ENDPOINTS)

        # Add the not found handler - it should always be the last one
        handlers.append((r".*", NotFoundHandler))

        settings = {
            "template_path": templates_path,
            # Currently setting debug to True, this can be changed to be
            # sourced from a config file
            "debug": True,
            # We are generating the cookie_secret every time that the webserver
            # is being reloaded, this can be sourced from the config file so
            # webserver reboots doesn't log out the users
            "cookie_secret": "b64encode(uuid4().bytes + uuid4().bytes)",
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers, **settings)
