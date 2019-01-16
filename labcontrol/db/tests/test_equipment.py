# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labcontrol.db import sql_connection
from labcontrol.db.testing import LabcontrolTestCase
from labcontrol.db.equipment import Equipment
from labcontrol.db.exceptions import LabcontrolUnknownIdError
from labcontrol.db.exceptions import LabcontrolDuplicateError


class TestEquipment(LabcontrolTestCase):
    def test_list_equipment(self):
        obs = Equipment.list_equipment()
        exp = [{'equipment_id': 15, 'external_id': '108379Z'},
               {'equipment_id': 16, 'external_id': '109375A'},
               {'equipment_id': 17, 'external_id': '311411B'},
               {'equipment_id': 2, 'external_id': 'BUZZ'},
               {'equipment_id': 10, 'external_id': 'Carmen'},
               {'equipment_id': 1, 'external_id': 'Echo550'},
               {'equipment_id': 9, 'external_id': 'HOWE'},
               {'equipment_id': 19, 'external_id': 'IGM-HiSeq4000'},
               {'equipment_id': 8, 'external_id': 'JER-E'},
               {'equipment_id': 11, 'external_id': 'KF1'},
               {'equipment_id': 12, 'external_id': 'KF2'},
               {'equipment_id': 13, 'external_id': 'KF3'},
               {'equipment_id': 14, 'external_id': 'KF4'},
               {'equipment_id': 18, 'external_id': 'KL-MiSeq'},
               {'equipment_id': 5, 'external_id': 'LUCY'},
               {'equipment_id': 20, 'external_id': 'Not applicable'},
               {'equipment_id': 4, 'external_id': 'PRICKLY'},
               {'equipment_id': 7, 'external_id': 'RIK-E'},
               {'equipment_id': 6, 'external_id': 'ROB-E'}
               ]
        self.assertEqual(obs[:-1], exp)

        obs = Equipment.list_equipment('echo')
        exp = [{'equipment_id': 1, 'external_id': 'Echo550'}]
        self.assertEqual(obs, exp)

        obs = Equipment.list_equipment('mosquito')
        exp = [{'equipment_id': 2, 'external_id': 'BUZZ'},
               {'equipment_id': 4, 'external_id': 'PRICKLY'},
               {'equipment_id': 3, 'external_id': 'STINGER'}]
        self.assertEqual(obs, exp)

    def test_list_equipment_types(self):
        obs = Equipment.list_equipment_types()
        exp = ['echo', 'EpMotion', 'HiSeq1500', 'HiSeq2500', 'HiSeq3000',
               'HiSeq4000', 'King Fisher', 'MiniSeq', 'MiSeq', 'mosquito',
               'NextSeq', 'Not applicable', 'NovaSeq',
               'tm 1000 8 channel pipette head',
               'tm 300 8 channel pipette head',
               'tm 50 8 channel pipette head']
        self.assertEqual(obs, exp)

    def test_create(self):
        # This tests the create type, create function and accessing the
        # attributes
        try:
            Equipment.create_type('Test Equipment Type')

            # Test type creation failure due to duplicated description
            self.assertRaises(LabcontrolDuplicateError, Equipment.create_type,
                              'Test Equipment Type')

            obs = Equipment.create('Test Equipment Type', 'New Equipment')
            self.assertEqual(obs.external_id, 'New Equipment')
            self.assertEqual(obs.equipment_type, 'Test Equipment Type')
            self.assertIsNone(obs.notes)
            obs.notes = 'New notes'
            self.assertEqual(obs.notes, 'New notes')

            # Test creation failure due to non-existent type
            self.assertRaises(LabcontrolUnknownIdError, Equipment.create,
                              'Non-existent Equipment Type', 'New Equipment 2')

            # Test creation failure due to duplicated external id
            self.assertRaises(LabcontrolDuplicateError, Equipment.create,
                              'Test Equipment Type', 'New Equipment')
        finally:
            # not in TearDown as this clean-up is specific to this test only;
            # running sql directly on the db from a test isn't pretty, but it
            # is still preferable to interdependence between tests.
            # Deletes both values that should have been added to db as well
            # as values whose add should have failed (just in case this test
            # failed by not preventing those additions).
            with sql_connection.TRN as TRN:
                sql = """DELETE
                         FROM labcontrol.equipment
                         WHERE external_id in
                          ('New Equipment', 'New Equipment 2');
                         DELETE
                         FROM labcontrol.equipment_type
                         WHERE description in ('Test Equipment Type',
                          'Non-existent Equipment Type');"""
                TRN.add(sql)
                TRN.execute()


if __name__ == '__main__':
    main()
