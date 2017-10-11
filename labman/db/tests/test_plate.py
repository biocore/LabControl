# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.plate import PlateConfiguration, Plate


class TestPlateConfiguration(LabmanTestCase):
    def test_create(self):
        obs = PlateConfiguration.create('96-well Test description', 8, 12)
        self.assertEqual(obs.description, '96-well Test description')
        self.assertEqual(obs.num_rows, 8)
        self.assertEqual(obs.num_columns, 12)


class TestPlate(LabmanTestCase):
    def test_create(self):
        plate_conf = PlateConfiguration.create('96-well Test desc', 8, 12)
        obs = Plate.create('New plate', plate_conf)
        self.assertEqual(obs.external_identifier, 'New plate')
        self.assertEqual(obs.plate_configuration, plate_conf)
        self.assertFalse(obs.discarded)
        self.assertIsNone(obs.notes)


if __name__ == '__main__':
    main()
