# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiOptionalType(models.Model):
    _name = "sii.optional.type"
    _description = "SII Optional Types"

    name = fields.Char("Name", size=120, required=True)
    sii_code = fields.Integer("SII Code", required=True)
    apply_rule = fields.Char("Apply rule")
    value_computation = fields.Char("Value computation")
    active = fields.Boolean("Active", default=True)
