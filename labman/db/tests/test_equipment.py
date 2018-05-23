# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.equipment import Equipment
from labman.db.exceptions import LabmanUnknownIdError, LabmanDuplicateError


class TestEquipment(LabmanTestCase):
    def test_list_equipment(self):
        obs = Equipment.list_equipment()
        # Since we are creating equipment in another test, limit the list to
        # those that are already in the test DB
        obs = obs[:18]
        exp = [{'equipment_id': 1, 'external_id': 'Echo550'},
               {'equipment_id': 2, 'external_id': 'BUZZ'},
               {'equipment_id': 3, 'external_id': 'STINGER'},
               {'equipment_id': 4, 'external_id': 'PRICKLY'},
               {'equipment_id': 5, 'external_id': 'LUCY'},
               {'equipment_id': 6, 'external_id': 'ROB-E'},
               {'equipment_id': 7, 'external_id': 'RIK-E'},
               {'equipment_id': 8, 'external_id': 'JER-E'},
               {'equipment_id': 9, 'external_id': 'HOWE'},
               {'equipment_id': 10, 'external_id': 'Carmen'},
               {'equipment_id': 11, 'external_id': 'KF1'},
               {'equipment_id': 12, 'external_id': 'KF2'},
               {'equipment_id': 13, 'external_id': 'KF3'},
               {'equipment_id': 14, 'external_id': 'KF4'},
               {'equipment_id': 15, 'external_id': '108379Z'},
               {'equipment_id': 16, 'external_id': '109375A'},
               {'equipment_id': 17, 'external_id': '311411B'}]
        self.assertEqual(obs[:-1], exp)

        obs = Equipment.list_equipment('echo')
        exp = [{'equipment_id': 1, 'external_id': 'Echo550'}]
        self.assertEqual(obs, exp)

        obs = Equipment.list_equipment('mosquito')
        exp = [{'equipment_id': 2, 'external_id': 'BUZZ'},
               {'equipment_id': 3, 'external_id': 'STINGER'},
               {'equipment_id': 4, 'external_id': 'PRICKLY'}]
        self.assertEqual(obs, exp)

    def test_list_equipment_types(self):
        obs = Equipment.list_equipment_types()
        exp = ['echo', 'mosquito', 'EpMotion', 'King Fisher',
               'tm 1000 8 channel pipette head',
               'tm 300 8 channel pipette head',
               'tm 50 8 channel pipette head',
               'HiSeq4000', 'MiniSeq', 'NextSeq', 'HiSeq3000',
               'HiSeq2500', 'HiSeq1500', 'MiSeq', 'NovaSeq',
               'none', 'Test Equipment Type', 'Test create type']
        self.assertEqual(obs, exp)

    def test_create(self):
        # This tests the create type, create function and accessing the
        # attributes
        Equipment.create_type('Test Equipment Type')
        obs = Equipment.create('Test Equipment Type', 'New Equipment')
        self.assertEqual(obs.external_id, 'New Equipment')
        self.assertEqual(obs.equipment_type, 'Test Equipment Type')
        self.assertIsNone(obs.notes)
        obs.notes = 'New notes'
        self.assertEqual(obs.notes, 'New notes')

        # Test creation failure due to non-existent type
        self.assertRaises(LabmanUnknownIdError, Equipment.create,
                          'Non-existent Equipment Type', 'New Equipment 2')

        # Test creation failure due to duplicated external id
        self.assertRaises(LabmanDuplicateError, Equipment.create,
                          'Test Equipment Type', 'New Equipment')

    def test_create_type_error(self):
        # Type creatio failure: duplicate
        Equipment.create_type('Test create type')
        self.assertRaises(LabmanDuplicateError, Equipment.create_type,
                          'Test create type')


if __name__ == '__main__':
    main()
