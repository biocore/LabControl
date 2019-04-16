# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from .reagent_composition import (ReagentCompositionListHandler)

__all__ = ['ReagentCompositionListHandler']

COMPOSITION_ENDPOINTS = [
    (r"/composition/reagent$", ReagentCompositionListHandler)
]
