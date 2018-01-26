# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import re
import zipfile

from io import BytesIO

from tornado.web import authenticated
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.user import User
from labman.db.composition import PoolComposition
from labman.db.equipment import Equipment
from labman.db.process import SequencingProcess


class SequencingProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        sequencers = []
        for model, lanes in SequencingProcess.sequencer_lanes.items():
            for sequencer in Equipment.list_equipment(model):
                sequencer['lanes'] = lanes
                sequencers.append(sequencer)
        self.render('sequencing.html', users=User.list_users(),
                    sequencers=sequencers)

    @authenticated
    def post(self):
        pools = self.get_argument('pools')
        run_name = self.get_argument('run_name')
        experiment = self.get_argument('experiment')
        sequencer_id = self.get_argument('sequencer')
        fwd_cycles = int(self.get_argument('fwd_cycles'))
        rev_cycles = int(self.get_argument('rev_cycles'))
        pi = self.get_argument('principal_investigator')
        contacts = self.get_argument('additional_contacts')

        pools = [PoolComposition(x) for x in json_decode(pools)]
        contacts = [User(x) for x in json_decode(contacts)]

        process = SequencingProcess.create(
            self.current_user, pools, run_name, experiment,
            Equipment(sequencer_id), fwd_cycles, rev_cycles, User(pi),
            contacts)
        self.write({'process': process.id})


class DownloadSampleSheetHandler(BaseHandler):
    @authenticated
    def get(self, process_id):
        process = SequencingProcess(int(process_id))
        text = process.generate_sample_sheet()

        filename = 'SampleSheet_%s_%s.csv' % (
            re.sub('[^0-9a-zA-Z\-\_]+', '_', process.run_name), process.id)

        self.set_header('Content-Type', 'text/csv')
        self.set_header('Expires', '0')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Content-Disposition',
                        'attachment; filename=%s' % filename)
        self.write(text)
        self.finish()

class DownloadPreparationSheetsHandler(BaseHandler):
    @authenticated
    def get(self, process_id):
        process = SequencingProcess(int(process_id))

        with BytesIO() as content:

            with zipfile.ZipFile(content, mode='w',
                                 compression=zipfile.ZIP_DEFLATED) as zf:
                for study, prep in process.generate_prep_information().items():
                    name = 'PrepSheet_process_%s_study_%s.csv' % (process.id,
                                                                  study.id)
                    zf.writestr(name, prep)

            zip_name = (re.sub('[^0-9a-zA-Z\-\_]+', '_', process.run_name) +
                        '_PrepSheets.zip')

            self.set_header('Content-Type', 'application/zip')
            self.set_header('Expires', '0')
            self.set_header('Cache-Control', 'no-cache')
            self.set_header("Content-Disposition", "attachment; filename=%s" %
                            zip_name)

            self.write(content.getvalue())

        self.finish()
