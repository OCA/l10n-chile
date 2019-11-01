# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BackendAcp(models.Model):
    _name = "backend.acp"
    _description = "Backend of Authorized Certification Providers"

    name = fields.Char(string="Name", required=True)
    host = fields.Char(string="Host", required=True)
    port = fields.Integer(string="Port",)
    user = fields.Char(string="User",)
    password = fields.Char(string="Password",)
    active = fields.Boolean(string="Active", default=True)
    status = fields.Selection((('unconfirmed', 'Unconfirmed'),
                               ('confirmed', 'Confirmed')), string="Status",
                              default='unconfirmed')

    def action_confirm(self):
        """
        Called by the Check button on the form view
        Set the status to 'confirmed' if the backend:
         - accepts connections
         - authorizes the given credentials
        :return: True or False whether the backend is usable
        """
        self.status = 'confirmed'
        return True

    def send(self, xml):
        # Send the XML of the document to the Third Party for signature
        return True

    def check_status(self):
        # Check the status of the document with the Third Party
        return True
