# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from os.path import dirname, join
from base64 import b64encode
from uuid import uuid4

import tornado

from labcontrol.gui.handlers.base import IndexHandler, NotFoundHandler
from labcontrol.gui.handlers.auth import LoginHandler, LogoutHandler, AccessHandler
from labcontrol.gui.handlers.plate import (
    PlateMapHandler, PlateNameHandler, PlateHandler, PlateLayoutHandler,
    PlateSearchHandler, PlateListHandler, PlateListingHandler,
    PlateProcessHandler)
from labcontrol.gui.handlers.pool import (
    PoolListHandler, PoolHandler, PoolListingHandler)
from labcontrol.gui.handlers.study import (
    StudyListHandler, StudyHandler, StudySamplesHandler, StudyListingHandler,
    StudySummaryHandler)
from labcontrol.gui.handlers.sequence import (
    SequenceRunListingHandler, SequenceRunListHandler)
from labcontrol.gui.handlers.sample import (
    ControlSamplesHandler, ManageControlsHandler)
from labcontrol.gui.handlers.process_handlers import PROCESS_ENDPOINTS
from labcontrol.gui.handlers.composition_handlers import COMPOSITION_ENDPOINTS


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
                    (r"/auth/access/", AccessHandler),
                    # Plate handlers
                    (r"/plate_list", PlateListHandler),
                    (r"/plate/(.*)/layout", PlateLayoutHandler),
                    (r"/plate/(.*)/process", PlateProcessHandler),
                    (r"/plate/(.*)/", PlateHandler),
                    (r"/plates$", PlateListingHandler),
                    (r"/plate_search", PlateSearchHandler),
                    (r"/plate$", PlateMapHandler),
                    (r"/platename", PlateNameHandler),
                    # Pool handlers
                    (r"/pool_list$", PoolListHandler),
                    (r"/pool/(.*)/", PoolHandler),
                    (r"/pools$", PoolListingHandler),
                    # Sequence handlers
                    (r"/sequence_run_list$", SequenceRunListHandler),
                    (r"/sequence_runs$", SequenceRunListingHandler),
                    # Study handlers
                    (r"/study_list", StudyListHandler),
                    (r"/study/(.*)/samples", StudySamplesHandler),
                    (r"/study/(.*)/", StudyHandler),
                    (r"/studies$", StudyListingHandler),
                    (r"/study/([0-9]+)/summary", StudySummaryHandler),
                    # Sample handlers
                    (r"/sample/control", ControlSamplesHandler),
                    (r"/sample/manage_controls", ManageControlsHandler)]

        # Add the process endpoints
        handlers.extend(PROCESS_ENDPOINTS)

        # Add the composition endpoints
        handlers.extend(COMPOSITION_ENDPOINTS)

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
            "cookie_secret": b64encode(uuid4().bytes + uuid4().bytes),
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers, **settings)
