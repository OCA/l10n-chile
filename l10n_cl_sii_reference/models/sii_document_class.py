# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiDocumentClass(models.Model):
    _name = "sii.document.class"
    _description = "SII Document Class"

    name = fields.Char("Name", size=120)
    prefix = fields.Char(
        "Prefix",
        help="""Prefix for Documents Codes on Invoices and Account Moves.
                For eg. 'FAC' will build 'FAC 00001' Document Number""")
    code_template = fields.Char("Code Template for Journal")
    code = fields.Integer("SII Code", required=True)
    document_letter_id = fields.Many2one("sii.document.letter",
                                         "Document Letter")
    report_name = fields.Char(
        "Name on Reports",
        help="Name that will be printed in reports, for example CREDIT NOTE")
    document_type = fields.Selection([
        ("invoice", "Invoices"),
        ("invoice_in", "Purchase Invoices"),
        ("debit_note", "Debit Notes"),
        ("credit_note", "Credit Notes"),
        ("stock_picking", "Stock Picking"),
        ("other_document", "Other Documents")],
        string="Document Type",
        help="""It defines some behaviours on automatic journal selection and
                in menus where it is shown.""")
    active = fields.Boolean("Active", default=True)
    dte = fields.Boolean("DTE", required=True)
    use_prefix = fields.Boolean(
        string="Use the prefix in the reference", default=False)
