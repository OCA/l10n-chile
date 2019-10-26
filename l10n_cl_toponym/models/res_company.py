# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    state_id = fields.Many2one(
        related='partner_id.state_id', readonly=False, string='State')

    city_id = fields.Many2one(
        related='partner_id.city_id', readonly=False,
        string='City of Address')

    @api.onchange('city_id')
    def _onchange_city(self):
        if self.city_id:
            self.country_id = self.city_id.state_id.country_id.id
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name
