# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiResponsibility(models.Model):
    _name = "sii.responsibility"
    _description = "SII VAT Responsibility"

    name = fields.Char("Name", size=64, required=True)
    code = fields.Char("Code", size=8, required=True)
    sii_code = fields.Integer("Tax Payer SII Code", required=True)
    active = fields.Boolean("Active", default=True)
    issued_letter_ids = fields.Many2many(
        "sii.document.letter",
        "sii_doc_letter_issuer_rel",
        "responsibility_id",
        "letter_id",
        "Issued Letters")
    received_letter_ids = fields.Many2many(
        "sii.document.letter",
        "sii_doc_letter_receptor_rel",
        "responsibility_id",
        "letter_id",
        "Received Letters")

    _sql_constraints = [
        ("name", "unique(name)", "Name must be unique!"),
        ("code", "unique(code)", "Code must be unique!")]
