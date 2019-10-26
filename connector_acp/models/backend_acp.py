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
    port = fields.Integer(string="Port", required=True)
    user = fields.Char(string="User", required=True)
    password = fields.Char(string="Password", required=True)
    active = fields.Boolean(string="Active", default=True)
    status = fields.Selection((('unconfirmed', 'Unconfirmed'),
                               ('confirmed', 'Confirmed')), string="Status",
                              default='unconfirmed')

    def action_confirm(self):
        self.status = 'confirmed'
        return True
