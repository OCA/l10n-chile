# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SIISucursal(models.Model):
    _name = "sii.sucursal"
    _description = "SII Sucursal"

    name = fields.Char(string="Name of the SII branch", required=True)
    sii_code = fields.Char(string="Code of the SII branch")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.user.company_id.id)
