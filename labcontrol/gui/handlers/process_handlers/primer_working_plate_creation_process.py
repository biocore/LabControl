# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import date

from tornado.web import authenticated

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.composition import PrimerSet
from labcontrol.db.process import PrimerWorkingPlateCreationProcess


class PrimerWorkingPlateCreationProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        primer_sets = PrimerSet.list_primer_sets()
        self.render('primer_plates.html', primer_sets=primer_sets)

    @authenticated
    def post(self):
        primer_set = self.get_argument('primer_set')
        master_set_order = self.get_argument('master_set_order')
        creation_date = self.get_argument('creation_date')

        month, day, year = map(int, creation_date.split('/'))
        creation_date = date(year, month, day)

        process = PrimerWorkingPlateCreationProcess.create(
            self.current_user, PrimerSet(primer_set), master_set_order,
            creation_date)
        self.write({'process': process.id})
