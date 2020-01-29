# Copyright (C) 2019 Konos
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartnerDicom(models.Model):
    _name = 'res.partner.dicom'
    _description = 'Dicom Log of a Partner'
    _order = 'date desc'

    dicom_score = fields.Char("Dicom Score", default="999", required=True)
    date = fields.Date(
        string='Dicom Date', required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
