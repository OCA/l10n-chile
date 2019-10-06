# -*- encoding: utf-8 -*-
from odoo import models, fields, api



class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_default_country(self):
        return self.env.user.company_id.country_id.id or self.env.user.partner_id.country_id.id

    state_id = fields.Many2one(
            "res.country.state",
            'Ubication',
        )



    @api.onchange('city_id')
    def _asign_city(self):
        if self.city_id:
            self.country_id = self.city_id.state_id.country_id.id
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name