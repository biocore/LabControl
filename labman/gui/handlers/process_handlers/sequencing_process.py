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
        pools = [[p['pool_composition_id'], p['external_id']]
                 for p in PoolComposition.list_pools()]
        sequencers = Equipment.list_equipment('miseq')
        self.render('sequencing.html', users=User.list_users(), pools=pools,
                    sequencers=sequencers)

    @authenticated
    def post(self):
        pool_id = self.get_argument('pool')
        run_name = self.get_argument('run_name')
        sequencer_id = self.get_argument('sequencer')
        fwd_cycles = int(self.get_argument('fwd_cycles'))
        rev_cycles = int(self.get_argument('rev_cycles'))
        assay = self.get_argument('assay')
        pi = self.get_argument('principal_investigator')
        c0 = self.get_argument('contact_0')
        c1 = self.get_argument('contact_1')
        c2 = self.get_argument('contact_2')
        process = SequencingProcess.create(
            self.current_user, PoolComposition(pool_id), run_name,
            Equipment(sequencer_id), fwd_cycles, rev_cycles, assay,
            User(pi), User(c0), User(c1), User(c2))
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
