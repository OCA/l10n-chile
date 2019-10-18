# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCountryStateRegion(models.Model):
    _name = 'res.country.state.region'
    _description = 'Region of a state'

    name = fields.Char(string='Region Name', required=True,
                       help='The state code.')
    code = fields.Char(string='Region Code', required=True,
                       help='The region code.')
    child_ids = fields.One2many('res.country.state', 'region_id',
                                string='Child Regions')
