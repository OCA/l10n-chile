# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiDocumentType(models.Model):
    _name = "sii.document.type"
    _description = "SII document types"

    name = fields.Char("Name", size=120, required=True)
    code = fields.Char("Code", size=16, required=True)
    sii_code = fields.Integer("SII Code", required=True)
    active = fields.Boolean("Active", default=True)
