# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from itertools import chain

from tornado.web import authenticated, HTTPError
from tornado.escape import json_encode, json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.exceptions import LabmanUnknownIdError
from labman.db.plate import PlateConfiguration, Plate
from labman.db.composition import SampleComposition
from labman.db.process import (
    SamplePlatingProcess, GDNAExtractionProcess, LibraryPrep16SProcess,
    LibraryPrepShotgunProcess, NormalizationProcess,
    GDNAPlateCompressionProcess)


def _get_plate(plate_id):
    """Returns the plate object if it exists

    Parameters
    ----------
    plate_id : str
        The plate id

    Raises
    ------
    HTTPError
        404, if the plate doesn't exist
    """
    plate_id = int(plate_id)
    try:
        plate = Plate(plate_id)
    except LabmanUnknownIdError:
        raise HTTPError(404, 'Plate %s doesn\'t exist' % plate_id)
    return plate


class PlateSearchHandler(BaseHandler):
    @authenticated
    def get(self):
        control_names = SampleComposition.get_control_samples()
        self.render('plate_search.html',
                    control_names=json_encode(control_names))

    @authenticated
    def post(self):
        plate_comment_keywords = self.get_argument("plate_comment_keywords")
        well_comment_keywords = self.get_argument("well_comment_keywords")
        operation = self.get_argument("operation")
        sample_names = json_decode(self.get_argument('sample_names'))

        res = {"data": [[p.id, p.external_id]
               for p in Plate.search(samples=sample_names,
                                     plate_notes=plate_comment_keywords,
                                     well_notes=well_comment_keywords,
                                     query_type=operation)]}

        self.write(res)


class PlateListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('plate_list.html')


class PlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_type = self.get_argument('plate_type', None)
        only_quantified = self.get_argument('only_quantified', False)
        plate_type = (json_decode(plate_type)
                      if plate_type is not None else None)
        only_quantified = True if only_quantified == 'true' else False
        res = {"data": [[p['plate_id'], p['external_id'], p['studies']]
                        for p in Plate.list_plates(
                            plate_type, only_quantified=only_quantified,
                            include_study_titles=True)]}
        self.write(res)


def plate_map_handler_get_request(process_id):
    plate_id = None
    if process_id is not None:
        try:
            process = SamplePlatingProcess(process_id)
        except LabmanUnknownIdError:
            raise HTTPError(404, reason="Plating process %s doesn't exist"
                            % process_id)
        plate_id = process.plate.id

    plate_confs = [[pc.id, pc.description, pc.num_rows, pc.num_columns]
                   for pc in PlateConfiguration.iter()
                   if 'template' not in pc.description]
    cdesc = SampleComposition.get_control_samples_description()
    return {'plate_confs': plate_confs, 'plate_id': plate_id,
            'process_id': process_id, 'controls_description': cdesc}


class PlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        process_id = self.get_argument('process_id', None)
        res = plate_map_handler_get_request(process_id)
        self.render("plate.html", **res)


class PlateNameHandler(BaseHandler):
    @authenticated
    def get(self):
        new_name = self.get_argument('new-name')
        status = 200 if Plate.external_id_exists(new_name) else 404
        self.set_status(status)
        self.finish()


def plate_handler_patch_request(user, plate_id, req_op, req_path,
                                req_value, req_from):
    """Performs the patch operation on the plate

    Parameters
    ----------
    user: labman.db.user.User
        User performing the request
    plate_id: int
        The SamplePlatingProcess to apply the patch operation
    req_op: string
        JSON PATCH op parameter
    req_path: string
        JSON PATCH path parameter
    req_value: string
        JSON PATCH value parameter
    req_from: string
        JSON PATCH from parameter

    Raises
    ------
    HTTPError
        400: If req_op is not a supported operation
        400: If req_path is incorrect
    """
    plate = _get_plate(plate_id)

    if req_op == 'replace':
        req_path = [v for v in req_path.split('/') if v]
        if len(req_path) != 1:
            raise HTTPError(400, 'Incorrect path parameter')

        attribute = req_path[0]
        if attribute == 'name':
            plate.external_id = req_value
        else:
            raise HTTPError(404, 'Attribute %s not recognized' % attribute)
    else:
        raise HTTPError(400, 'Operation %s not supported. Current supported '
                             'operations: replace' % req_op)


class PlateHandler(BaseHandler):
    @authenticated
    def get(self, plate_id):
        plate = _get_plate(plate_id)
        duplicates = [
            [sample_info[0].row, sample_info[0].column, sample_info[1]]
            for sample_info in chain.from_iterable(plate.duplicates.values())]
        previous_plates = [
            [[w.row, w.column],
             [{'plate_id': p.id, 'plate_name': p.external_id} for p in plates]]
            for w, plates in plate.get_previously_plated_wells().items()]
        unknowns = [[well.row, well.column] for well in plate.unknown_samples]

        plate_config = plate.plate_configuration
        result = {'plate_id': plate.id,
                  'plate_name': plate.external_id,
                  'discarded': plate.discarded,
                  'plate_configuration': [
                        plate_config.id, plate_config.description,
                        plate_config.num_rows, plate_config.num_columns],
                  'notes': plate.notes,
                  'studies': sorted(s.id for s in plate.studies),
                  'duplicates': duplicates,
                  'previous_plates': previous_plates,
                  'unknowns': unknowns}

        self.write(result)
        self.finish()

    @authenticated
    def patch(self, plate_id):
        # Follows the JSON PATCH specification
        # https://tools.ietf.org/html/rfc6902
        req_op = self.get_argument('op')
        req_path = self.get_argument('path')
        req_value = self.get_argument('value', None)
        req_from = self.get_argument('from', None)
        plate_handler_patch_request(self.current_user, plate_id, req_op,
                                    req_path, req_value, req_from)
        self.finish()


def plate_layout_handler_get_request(plate_id):
    """Returns the plate layout

    Parameters
    ----------
    plate_id : int
        The plate id

    Returns
    -------
    list of lists of {'sample': str, 'notes': str}
    """
    plate = _get_plate(plate_id)
    plate_layout = plate.layout
    result = []
    for l_row in plate_layout:
        row = []
        for l_well in l_row:
            composition = l_well.composition
            sample = composition.content
            row.append({'sample': sample, 'notes': composition.notes})

        result.append(row)

    return result


class PlateLayoutHandler(BaseHandler):
    @authenticated
    def get(self, plate_id):
        self.write(json_encode(plate_layout_handler_get_request(plate_id)))


class PlateProcessHandler(BaseHandler):
    @authenticated
    def get(self, plate_id):
        urls = {
            SamplePlatingProcess: '/plate',
            GDNAExtractionProcess: '/process/gdna_extraction',
            LibraryPrep16SProcess: '/process/library_prep_16S',
            LibraryPrepShotgunProcess: '/process/library_prep_shotgun',
            NormalizationProcess: '/process/normalize',
            GDNAPlateCompressionProcess: '/process/gdna_compression'}
        process = Plate(plate_id).process
        self.redirect(urls[process.__class__] + '?process_id=%s' % process.id)
