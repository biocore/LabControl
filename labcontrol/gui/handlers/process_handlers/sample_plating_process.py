# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.study import Study
from labcontrol.db.process import SamplePlatingProcess
from labcontrol.db.plate import PlateConfiguration, Plate


class SamplePlatingProcessNotes(BaseHandler):
    @authenticated
    def post(self):
        process = SamplePlatingProcess(self.get_argument('process_id'))
        process.notes = self.get_argument('notes')
        self.finish()


class SamplePlatingProcessListHandler(BaseHandler):
    @authenticated
    def post(self):
        user = self.current_user
        plate_config_id = self.get_argument('plate_configuration')
        plate_ext_id = self.get_argument('plate_name')

        spp = SamplePlatingProcess.create(
            user, PlateConfiguration(plate_config_id), plate_ext_id)

        self.write({'plate_id': spp.plate.id, 'process_id': spp.id})


def sample_plating_process_handler_patch_request(
        user, process_id, req_op, req_path, req_value, req_from):
    """Performs the patch operation on the sample plating process

    Parameters
    ----------
    user: labcontrol.db.user.User
        User performing the request
    process_id: int
        The SamplePlatingProcess to apply the patch operation
    req_op: string
        JSON PATCH op parameter
    req_path: string
        JSON PATCH path parameter
    req_value: string
        JSON PATCH value parameter
    req_from: string
        JSON PATCH from parameter

    Returns
    -------
    dict
        The results of the patch operation

    Raises
    ------
    HTTPError
        400: If req_op is not a supported operation
        400: If req_path is incorrect
    """
    if req_op == 'replace':
        req_path = [v for v in req_path.split('/') if v]
        if len(req_path) != 5:
            raise HTTPError(400, 'Incorrect path parameter')
        attribute = req_path[0]

        if attribute == 'well':
            row = req_path[1]
            col = req_path[2]
            study_id = int(req_path[3])
            well_attribute = req_path[4]

            # The default values of the variables sample_id and
            # blank_or_unknown are set before the try, and these are the values
            # that are used if either (a) study_id is not 0 OR (b) the try
            # fails with a ValueError (see comment in try below). If the try
            # fails with anything other than a ValueError then the entire
            # function bails, so it doesn't matter what these variables are set
            # to. If and only if the try succeeds are these variables set to
            # the values within the try.
            sample_id = req_value
            blank_or_unknown = True

            # It actually IS possible to plate a plate without specifying
            # separate study id(s); can plate just all blanks, or can provide
            # the fully qualified sample id(s)--i.e., <studyid>.<sampleid>.
            if study_id != 0:
                try:
                    # Note that the try fails iff the
                    # Study(study_id).specimen_id_to_sample_id() call fails,
                    # as the blank_or_unknown = False can't really fail ...
                    # this assures that we can't realistically end up in an
                    # inconsistent situation where sample_id has been set
                    # during the try but blank_or_unknown has not.
                    #
                    # Thus, the ordering of these two statements within the try
                    # is really important: do not change it unless you
                    # understand all of the above!
                    the_study = Study(study_id)
                    sample_id = the_study.specimen_id_to_sample_id(
                        req_value)
                    blank_or_unknown = False
                except ValueError:
                    pass
                # end try/except
            # end if

            if well_attribute == 'sample':
                if req_value is None or not req_value.strip():
                    raise HTTPError(
                        400, 'A new value for the well should be provided')

                plates = Plate.search(samples=[sample_id])
                process = SamplePlatingProcess(process_id)
                plates = set(plates) - {process.plate}
                prev_plates = [{'plate_id': p.id, 'plate_name': p.external_id}
                               for p in plates]
                content, sample_ok = process.update_well(row, col, sample_id)

                if blank_or_unknown:
                    req_value = content

                return {'sample_id': req_value, 'previous_plates': prev_plates,
                        'sample_ok': sample_ok}
            elif well_attribute == 'notes':
                if req_value is not None:
                    # If the user provides an empty string, just store None
                    # in the database
                    req_value = (req_value.strip()
                                 if req_value.strip() else None)
                SamplePlatingProcess(process_id).comment_well(
                    row, col, req_value)
                return {'comment': req_value}
            else:
                raise HTTPError(
                    404, 'Well attribute %s not found' % well_attribute)
        else:
            raise HTTPError(404, 'Attribute %s not found' % attribute)

    else:
        raise HTTPError(400, 'Operation %s not supported. Current supported '
                             'operations: replace' % req_op)


class SamplePlatingProcessHandler(BaseHandler):
    @authenticated
    def patch(self, process_id):
        req_op = self.get_argument('op')
        req_path = self.get_argument('path')
        req_value = self.get_argument('value', None)
        req_from = self.get_argument('from', None)

        res = sample_plating_process_handler_patch_request(
            self.current_user, process_id, req_op, req_path,
            req_value, req_from)
        self.write(res)
        self.finish()
