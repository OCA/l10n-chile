# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BackendAcp(models.Model):
    _inherit = "backend.acp"

    def action_confirm(self):
        self.status = 'confirmed'
        return True

    def send(self, xml):
        # Send the XML of the document to the Third Party for signature
        return True

    def check_status(self):
        # Check the status of the document with the Third Party
        return True
