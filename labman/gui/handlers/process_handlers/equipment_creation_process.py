# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler
from labman.db.equipment import Equipment


class EquipmentCreationProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        equipment_types = Equipment.list_equipment_types()
        self.render('equipments.html', equipment_types=equipment_types)

    @authenticated
    def post(self):
        equipment_type = self.get_argument('equipment_type')
        external_id = self.get_argument('external_id')
        equipment = Equipment.create(equipment_type, external_id)
        self.write({'equipment': equipment.id})
