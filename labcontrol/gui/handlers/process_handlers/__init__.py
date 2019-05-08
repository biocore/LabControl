# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from .sample_plating_process import (SamplePlatingProcessNotes,
                                     SamplePlatingProcessListHandler,
                                     SamplePlatingProcessHandler)
from .gdna_extraction_process import GDNAExtractionProcessHandler
from .gdna_compression_process import GDNAPlateCompressionProcessHandler
from .library_prep_16s_process import LibraryPrep16SProcessHandler
from .library_prep_shotgun_process import (
    LibraryPrepShotgunProcessHandler, DownloadLibraryPrepShotgunProcessHandler)
from .quantification_process import (
    QuantificationProcessParseHandler, QuantificationProcessHandler,
    QuantificationViewHandler)
from .pooling_process import (
    PoolPoolProcessHandler, LibraryPoolProcessHandler,
    ComputeLibraryPoolValuesHandler, DownloadPoolFileHandler)
from .sequencing_process import (
    SequencingProcessHandler, DownloadSampleSheetHandler,
    DownloadPreparationSheetsHandler)
from .normalization_process import (
    NormalizationProcessHandler, DownloadNormalizationProcessHandler)
from .primer_working_plate_creation_process import (
    PrimerWorkingPlateCreationProcessHandler)
from .equipment_creation_process import EquipmentCreationProcessHandler

__all__ = ['SamplePlatingProcessListHandler', 'SamplePlatingProcessHandler',
           'SamplePlatingProcessNotes',
           'GDNAExtractionProcessHandler', 'LibraryPrep16SProcessHandler',
           'QuantificationProcessParseHandler', 'QuantificationProcessHandler',
           'QuantificationViewHandler',
           'PoolPoolProcessHandler', 'LibraryPoolProcessHandler',
           'SequencingProcessHandler', 'DownloadSampleSheetHandler',
           'DownloadPreparationSheetsHandler',
           'GDNAPlateCompressionProcessHandler',
           'PrimerWorkingPlateCreationProcessHandler',
           'EquipmentCreationProcessHandler',
           'ComputeLibraryPoolValuesHandler', 'DownloadPoolFileHandler']


PROCESS_ENDPOINTS = [
    (r"/process/sample_plating/([0-9]+)$", SamplePlatingProcessHandler),
    (r"/process/sample_plating$", SamplePlatingProcessListHandler),
    (r"/process/sample_plating/notes$", SamplePlatingProcessNotes),
    (r"/process/gdna_extraction$", GDNAExtractionProcessHandler),
    (r"/process/gdna_compression$", GDNAPlateCompressionProcessHandler),
    (r"/process/library_prep_16S$", LibraryPrep16SProcessHandler),
    (r"/process/parse_quantify$", QuantificationProcessParseHandler),
    (r"/process/quantify$", QuantificationProcessHandler),
    (r"/process/view_quants/([0-9]+)$", QuantificationViewHandler),
    (r"/process/compute_pool$", ComputeLibraryPoolValuesHandler),
    (r"/process/poolpools$", PoolPoolProcessHandler),
    (r"/process/poollibraries$", LibraryPoolProcessHandler),
    (r"/process/poollibraries/([0-9]+)/pool_file$", DownloadPoolFileHandler),
    (r"/process/sequencing/(.*)/", SequencingProcessHandler),
    (r"/process/library_prep_shotgun$", LibraryPrepShotgunProcessHandler),
    (r"/process/library_prep_shotgun/([0-9]+)/echo_pick_list$",
     DownloadLibraryPrepShotgunProcessHandler),
    (r"/process/sequencing/([0-9]+)/sample_sheet$",
     DownloadSampleSheetHandler),
    (r"/process/sequencing/([0-9]+)/preparation_sheets$",
     DownloadPreparationSheetsHandler),
    (r"/process/normalize$", NormalizationProcessHandler),
    (r"/process/normalize/([0-9]+)/echo_pick_list$",
     DownloadNormalizationProcessHandler),
    (r"/process/working_primers$", PrimerWorkingPlateCreationProcessHandler),
    (r"/process/equipments$", EquipmentCreationProcessHandler),
]
