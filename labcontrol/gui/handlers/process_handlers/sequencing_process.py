# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import zipfile

from io import BytesIO

from tornado.web import authenticated
from tornado.escape import json_decode

from labcontrol.gui.handlers.base import BaseHandler, BaseDownloadHandler
from labcontrol.db.user import User
from labcontrol.db.composition import PoolComposition
from labcontrol.db.equipment import Equipment
from labcontrol.db.process import SequencingProcess


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


class DownloadSampleSheetHandler(BaseDownloadHandler):
    @authenticated
    def get(self, process_id):
        process = SequencingProcess(int(process_id))
        text = process.generate_sample_sheet()
        name_pieces = ["samplesheet", process.run_name]
        if not process.is_amplicon_assay:
            name_pieces.append(process.experiment)
        self.deliver_text(name_pieces, process, text, extension="csv")


class DownloadPreparationSheetsHandler(BaseDownloadHandler):
    @authenticated
    def get(self, process_id):
        process = SequencingProcess(int(process_id))
        name_pieces = ["preps", process.run_name]

        with BytesIO() as content:
            with zipfile.ZipFile(content, mode='w',
                                 compression=zipfile.ZIP_DEFLATED) as zf:

                # We anticipate that someday the generation of multiple
                # prep files for different studies may be coming back; that
                # is why this loop has not been torn out in spite of the
                # fact that, given changes in the generate_*_prep_information
                # methods, the dictionary will only have one item in it
                # so this loop will only ever execute once.
                for _, prep in process.generate_prep_information().items():
                    # NB: first piece is NOT the same as above: singular "prep"
                    # instead of plural "preps"
                    curr_name_pieces = ["prep", process.run_name]
                    name = self.generate_file_name(curr_name_pieces, process)
                    zf.writestr(name, prep)

            self.deliver_zip(name_pieces, process, content.getvalue(),
                             extension="zip")
