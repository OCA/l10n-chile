# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    document_class_id = fields.Many2one(
        "sii.document.class",
        string="Document Type",
        related="move_id.document_class_id",
        store=True,
        readonly=True)
    document_number = fields.Char(
        string="Document Number",
        related="move_id.document_number",
        store=True,
        readonly=True)
