# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode

import numpy as np

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.plate import Plate
from labcontrol.db.process import QuantificationProcess

from labcontrol.db.composition import LibraryPrepShotgunComposition
from labcontrol.db.composition import LibraryPrep16SComposition
from labcontrol.db.composition import GDNAComposition
from labcontrol.db.composition import CompressedGDNAComposition


class QuantificationProcessParseHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        self.render('parse_quantification.html', plate_ids=plate_ids)

    @authenticated
    def post(self):
        # We will receive as many files as plates the user has selected
        # The key of the self.request.files dictionary is of the form
        # plate-file-<PLATE_ID> so use the keys to know the plates
        # that we need to quantify
        plates = []
        for key in self.request.files:
            plate_id = key.rsplit('-', 1)[1]
            # The 0 is because for each key we have a single file
            file_content = self.request.files[key][0]['body'].decode('utf-8')
            plate = Plate(plate_id)
            pc = plate.plate_configuration
            concentrations = QuantificationProcess.parse(
                file_content, rows=pc.num_rows, cols=pc.num_columns)

            names = np.empty_like(plate.layout, dtype='object')
            blanks = np.zeros_like(plate.layout, dtype=bool)

            # fetch the sample names and whether or not the samples are blanks
            # by default these are set to be None and False.
            for i, full_row in enumerate(plate.layout):
                for j, well in enumerate(full_row):

                    # some wells have no compositions at all so skip those
                    if well is None:
                        continue
                    comp = well.composition

                    # cache the sample compositions to avoid extra intermediate
                    # queries
                    if isinstance(comp, GDNAComposition):
                        smp = comp.sample_composition
                    elif isinstance(comp, (CompressedGDNAComposition,
                                           LibraryPrep16SComposition)):
                        smp = comp.gdna_composition.sample_composition
                    elif isinstance(comp, LibraryPrepShotgunComposition):
                        smp = comp.normalized_gdna_composition\
                            .compressed_gdna_composition.gdna_composition\
                            .sample_composition
                    else:
                        raise ValueError('This composition type is not '
                                         'supported')

                    blanks[i][j] = smp.sample_composition_type == 'blank'
                    names[i][j] = smp.sample_id

            plates.append({'plate_name': plate.external_id,
                           'plate_id': plate_id,
                           'concentrations': concentrations.tolist(),
                           'names': names.tolist(),
                           'blanks': blanks.tolist(),
                           'type': plate.process._process_type
                           })

        self.render('quantification.html', plates=plates)


class QuantificationProcessHandler(BaseHandler):
    @authenticated
    def post(self):
        plates_info = json_decode(self.get_argument('plates-info'))
        processes = []
        for pinfo in plates_info:
            plate = Plate(pinfo['plate_id'])
            concentrations = np.asarray(pinfo['concentrations'])

            processes.append(QuantificationProcess.create(
                self.current_user, plate, concentrations).id)

        self.write({'processes': processes})


class QuantificationViewHandler(BaseHandler):
    @authenticated
    def get(self, plate_id):

        plate = Plate(plate_id)
        quant_processes = plate.quantification_processes

        quant_values = []

        for quant in quant_processes:
            concentrations = np.zeros_like(plate.layout, dtype=float)
            names = np.empty_like(plate.layout, dtype='object')
            blanks = np.zeros_like(plate.layout, dtype=bool)

            # Get sample_composition (`smp`) from each well.
            # Currently this requires ugly logic because you have to go
            # through a named subclass that depends on plate type.
            # TODO: replace this with a direct SQL query in a dedicated
            # method of the composition class.
            for comp, raw_conc, _ in quant.concentrations:
                container = comp.container
                row, col = container.row - 1, container.column - 1

                if isinstance(comp, GDNAComposition):
                    smp = comp.sample_composition
                elif isinstance(comp, (CompressedGDNAComposition,
                                       LibraryPrep16SComposition)):
                    smp = comp.gdna_composition.sample_composition
                elif isinstance(comp, LibraryPrepShotgunComposition):
                    smp = comp.normalized_gdna_composition\
                        .compressed_gdna_composition.gdna_composition\
                        .sample_composition
                else:
                    raise ValueError('This composition type is not '
                                     'supported')

                blanks[row, col] = smp.sample_composition_type == 'blank'
                names[row, col] = smp.sample_id
                concentrations[row, col] = raw_conc

            quant_values.append({'quant_id': quant.id,
                                 'person': quant.personnel.name,
                                 'date': quant.date.isoformat(),
                                 'notes': quant.notes,
                                 'concs': concentrations.tolist(),
                                 'blanks': blanks.tolist(),
                                 'names': names.tolist()})

        self.render('view_quantifications.html',
                    quantifications=quant_values,
                    plate_type=plate.process._process_type,
                    plate_name=plate.external_id)
