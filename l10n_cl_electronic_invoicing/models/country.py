# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiCountry(models.Model):
    _inherit = "res.country"

    rut_natural = fields.Char("RUT persona natural", size=11)
    rut_juridica = fields.Char("RUT persona juridica", size=11)
    rut_otro = fields.Char("RUT otro", size=11)
