# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CompanyTurns(models.Model):
    _inherit = 'res.company'

    activity_description = fields.Many2one(
        string='Activity Description',
        related='partner_id.activity_description',
        relation='sii.activity.description')
