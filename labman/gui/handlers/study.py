# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_encode

from labman.gui.handlers.base import BaseHandler
from labman.db.study import Study
from labman.db.exceptions import LabmanUnknownIdError


class StudyListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('study_list.html')


class StudyListHandler(BaseHandler):
    @authenticated
    def get(self):
        # Get all arguments that DataTables send us
        res = {"data": [
            [s['study_id'], s['study_title'], s['study_alias'], s['owner'],
             s['num_samples']] for s in Study.list_studies()]}
        self.write(res)
        self.finish()


class StudyHandler(BaseHandler):
    @authenticated
    def get(self, study_id):
        try:
            study = Study(int(study_id))
            self.write({'study_id': study.id,
                        'study_title': study.title,
                        'total_samples': study.num_samples})
        except LabmanUnknownIdError:
            self.set_status(404)
        self.finish()


class StudySamplesHandler(BaseHandler):
    @authenticated
    def get(self, study_id):
        try:
            study = Study(int(study_id))
            term = self.get_argument('term', None)
            res = list(study.samples(term, limit=20))
            self.write(json_encode(res))
        except LabmanUnknownIdError:
            self.set_status(404)
        self.finish()


class StudySummaryHandler(BaseHandler):
    @authenticated
    def get(self, study_id):
        try:
            study = Study(int(study_id))
        except LabmanUnknownIdError:
            raise HTTPError(404, reason="Study %s doesn't exist" % study_id)

        study_numbers = {
            'num_samples':
                study.num_samples,
            'number_samples_plated':
                study.number_samples_plated,
            'number_samples_extracted':
                study.number_samples_extracted,
            'number_samples_amplicon_libraries':
                study.number_samples_amplicon_libraries,
            'number_samples_amplicon_pools':
                study.number_samples_amplicon_pools,
            'number_samples_amplicon_sequencing_pools':
                study.number_samples_amplicon_sequencing_pools,
            'number_samples_amplicon_sequencing_runs':
                study.number_samples_amplicon_sequencing_runs,
            'number_samples_compressed':
                study.number_samples_compressed,
            'number_samples_normalized':
                study.number_samples_normalized,
            'number_samples_shotgun_libraries':
                study.number_samples_shotgun_libraries,
            'number_samples_shotgun_pool':
                study.number_samples_shotgun_pool,
            'number_samples_shotgun_sequencing_runs':
                study.number_samples_shotgun_sequencing_runs}
        self.render('study.html', study_id=study.id,
                    study_title=study.title, study_numbers=study_numbers)
