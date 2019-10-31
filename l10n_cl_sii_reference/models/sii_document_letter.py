# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiDocumentLetter(models.Model):
    _name = "sii.document.letter"
    _description = "SII Document letter"

    name = fields.Char("Name", size=64, required=True)
    class_ids = fields.One2many(
        "sii.document.class", "document_letter_id", "SII Document Classes")
    issuer_ids = fields.Many2many(
        "sii.responsibility",
        "sii_doc_letter_issuer_rel",
        "letter_id",
        "responsibility_id",
        "Issuers")
    receptor_ids = fields.Many2many(
        "sii.responsibility",
        "sii_doc_letter_receptor_rel",
        "letter_id",
        "responsibility_id",
        "Receptors")
    active = fields.Boolean("Active", default=True)
    vat_discriminated = fields.Boolean(
        "VAT Discriminated on Invoices?",
        help="If True, the VAT will be discriminated on invoice report.")

    _sql_constraints = \
        [("name", "unique(name)", "Name must be unique!")]
