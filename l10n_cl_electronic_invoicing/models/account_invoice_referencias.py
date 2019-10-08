# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class Referencias(models.Model):
    _name = "account.invoice.referencias"
    _description = "References on a invoice"

    origen = fields.Char(string="Origin")
    sii_referencia_TpoDocRef = fields.Many2one(
        "sii.document.class", string="SII Reference Document Type")
    sii_referencia_CodRef = fields.Selection([
        ("1", "Anula Documento de Referencia"),
        ("2", "Corrige texto Documento Referencia"),
        ("3", "Corrige montos")],
        string="SII Reference Code")
    motivo = fields.Char(string="Motivo")
    invoice_id = fields.Many2one(
        "account.invoice",
        ondelete="cascade",
        index=True,
        copy=False,
        string="Document")
    fecha_documento = fields.Date(string="Document Date", required=True)
