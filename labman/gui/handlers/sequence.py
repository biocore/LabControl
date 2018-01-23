# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.exceptions import LabmanUnknownIdError
from labman.db.process import SequencingProcess


class SequenceRunListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('sequence_run_list.html')


class SequenceRunListHandler(BaseHandler):
    @authenticated
    def get(self):
        res = {"data": [[p['process_id'],
                         p['run_name'],
                         p['experiment'],
                         p['assay'],
                         p['principal_investigator'],
                         p['sequencing_process_id']]
                        for p in SequencingProcess.list_sequencing_runs()]}
        self.write(res)


class SequenceRunHandler(BaseHandler):
    @authenticated
    def get(self, pool_id):
        try:
            pool = PoolComposition(int(pool_id))
        except LabmanUnknownIdError:
            raise HTTPError(404, 'Pool %s doesn\'t exist' % pool_id)

        result = {'pool_id': pool.id,
                  'pool_name': pool.container.external_id,
                  'num_components': len(pool.components)}
        self.write(result)
        self.finish()
