# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from .sample_plating_process import SamplePlatingProcessListHandler

__all__ = ['SamplePlatingProcessListHandler']

PROCESS_ENDPOINTS = [
    (r"/process/sample_plating$", SamplePlatingProcessListHandler)
]
