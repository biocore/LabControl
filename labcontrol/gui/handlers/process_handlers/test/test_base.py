# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labcontrol.gui.testing import TestHandlerBase
from labcontrol.gui.handlers.base import BaseDownloadHandler
from labcontrol.db.process import _Process


class TestBaseDownloadHandler(TestHandlerBase):
    def test_generate_file_name(self):
        a_process = _Process(1)

        # default extension
        obs1 = BaseDownloadHandler.generate_file_name(["a    name", "a piece"],
                                                      a_process)
        self.assertEqual(obs1, "2017-10-24_a_name_a_piece.txt")

        # alternate extension
        obs1 = BaseDownloadHandler.generate_file_name(["a    name", "a piece"],
                                                      a_process, "csv")
        self.assertEqual(obs1, "2017-10-24_a_name_a_piece.csv")


if __name__ == '__main__':
    main()
