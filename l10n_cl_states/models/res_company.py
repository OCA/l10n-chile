from odoo import fields, models, api
from odoo.tools.translate import _
import re


class Company(models.Model):
    _inherit = 'res.company'


    state_id = fields.Many2one(
            related='partner_id.state_id', readonly=False,
            relation="res.country.state",
            string='Ubication',
        )

    city_id = fields.Many2one(
            related='partner_id.city_id', readonly=False,
            relation="res.city",
            string='City',
        )

    @api.onchange('city_id')
    def _asign_city(self):
        if self.city_id:
            self.country_id = self.city_id.state_id.country_id.id
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name
