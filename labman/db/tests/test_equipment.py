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
