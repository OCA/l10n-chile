# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    backend_acp_id = fields.Many2one(
        "backend.acp", string="Backend to the Tax Authority"
    )
