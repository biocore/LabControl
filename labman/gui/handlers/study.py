# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
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
            self.render('study.html', study_id=study.id,
                        study_title=study.title,
                        total_samples=study.num_samples,
                        num_amplicon_amplified=study.num_amplicon_amplified,
                        num_amplicon_quantified=study.num_amplicon_quantified,
                        num_amplicon_plated=study.num_amplicon_plated,
                        num_amplicon_pooled=study.num_amplicon_pooled,
                        num_amplicon_sequenced=study.num_amplicon_sequenced,
                        num_shotgun_amplified=study.num_shotgun_amplified,
                        num_shotgun_quantified=study.num_shotgun_quantified,
                        num_shotgun_plated=study.num_shotgun_plated,
                        num_shotgun_pooled=study.num_shotgun_pooled,
                        num_shotgun_sequenced=study.num_shotgun_sequenced)
        except LabmanUnknownIdError:
            self.set_status(404)
        self.finish()
