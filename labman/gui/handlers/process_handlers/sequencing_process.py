# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler
from labman.db.user import User
from labman.db.composition import PoolComposition
from labman.db.equipment import Equipment
from labman.db.process import SequencingProcess


class SequencingProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        model2lanes = {
            'HiSeq4000': 8,
            'HiSeq3000': 8,
            'HiSeq2500': 2,
            'HiSeq1500': 2,
            'MiSeq': 1,
            'MiniSeq': 1,
            'NextSeq': 1,
            'NovaSeq': 1}
        sequencers = []
        for model, lanes in model2lanes.items():
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
        text = process.format_sample_sheet()

        self.set_header('Content-Description', 'text/csv')
        self.set_header('Expires', '0')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Content-Disposition', 'attachment; '
                        'filename=SampleSheet_%s.csv' % process.run_name)
        self.write(text)
        self.finish()
