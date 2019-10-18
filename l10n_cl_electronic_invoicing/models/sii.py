# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _


class SIISucursal(models.Model):
    _name = "sii.sucursal"
    _description = "SII Sucursal"

    name = fields.Char(string="Name of the SII branch", required=True)
    sii_code = fields.Char(string="Code of the SII branch")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.user.company_id.id)


class SiiDocumentClass(models.Model):
    _name = "sii.document.class"
    _description = "SII Document Class"

    name = fields.Char("Name", size=120)
    doc_code_prefix = fields.Char(
        "Document Code Prefix",
        help="""Prefix for Documents Codes on Invoices and Account Moves.
                For eg. 'FAC' will build 'FAC 00001' Document Number""")
    code_template = fields.Char("Code Template for Journal")
    sii_code = fields.Integer("SII Code", required=True)
    document_letter_id = fields.Many2one("sii.document.letter",
                                         "Document Letter")
    report_name = fields.Char(
        "Name on Reports",
        help="""Name that will be printed in reports,
         for example CREDIT NOTE""")
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
        string="Usar Prefix en las referencias DTE", default=False)


class SiiDocumentLetter(models.Model):
    _name = "sii.document.letter"
    _description = "Sii Document letter"

    name = fields.Char("Name", size=64, required=True)
    sii_document_class_ids = fields.One2many(
        "sii.document.class", "document_letter_id", "SII Document Classes")
    issuer_ids = fields.Many2many(
        "sii.responsability",
        "sii_doc_letter_issuer_rel",
        "letter_id",
        "responsability_id",
        "Issuers")
    receptor_ids = fields.Many2many(
        "sii.responsability",
        "sii_doc_letter_receptor_rel",
        "letter_id",
        "responsability_id",
        "Receptors")
    active = fields.Boolean("Active", default=True)
    vat_discriminated = fields.Boolean(
        "Vat Discriminated on Invoices?",
        help="If True, the vat will be discriminated on invoice report.")

    _sql_constraints = \
        [("name", "unique(name)",
          "Name must be unique!")]


class SiiResponsability(models.Model):
    _name = "sii.responsability"
    _description = "SII VAT Responsability"

    name = fields.Char("Name", size=64, required=True)
    code = fields.Char("Code", size=8, required=True)
    tp_sii_code = fields.Integer("Tax Payer SII Code", required=True)
    active = fields.Boolean("Active", default=True)
    issued_letter_ids = fields.Many2many(
        "sii.document.letter",
        "sii_doc_letter_issuer_rel",
        "responsability_id",
        "letter_id",
        "Issued Document Letters")
    received_letter_ids = fields.Many2many(
        "sii.document.letter",
        "sii_doc_letter_receptor_rel",
        "responsability_id",
        "letter_id",
        "Received Document Letters")

    _sql_constraints = [
        ("name", "unique(name)", "Name must be unique!"),
        ("code", "unique(code)", "Code must be unique!")]


class SiiDocumentType(models.Model):
    _name = "sii.document.type"
    _description = "SII document types"

    name = fields.Char("Name", size=120, required=True)
    code = fields.Char("Code", size=16, required=True)
    sii_code = fields.Integer("SII Code", required=True)
    active = fields.Boolean("Active", default=True)


class SiiConceptType(models.Model):
    _name = "sii.concept.type"
    _description = "SII concept types"

    name = fields.Char("Name", size=120, required=True)
    sii_code = fields.Integer("SII Code", required=True)
    active = fields.Boolean("Active", default=True)
    product_types = fields.Char(
        "Product types",
        help="Translate this product types to this SII concept.\
        Types must be a subset of adjust,\
        consu and service separated by commas.",
        required=True,
    )

    @api.constrains("product_types")
    def _check_product_types(self):
        for r in self:
            if r.product_types:
                types = set(r.product_types.split(","))
                if not types.issubset(["adjust", "consu", "service"]):
                    return {'warning': {
                        'title': _("Warning!"),
                        'message': _("You provided an invalid list of product "
                                     "types. Must be separated by commas.")}}


class SiiOptionalType(models.Model):
    _name = "sii.optional.type"
    _description = "SII optional types"

    name = fields.Char("Name", size=120, required=True)
    sii_code = fields.Integer("SII Code", required=True)
    apply_rule = fields.Char("Apply rule")
    value_computation = fields.Char("Value computation")
    active = fields.Boolean("Active", default=True)
