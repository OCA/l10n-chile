# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import sys
import os
from datetime import datetime, timedelta
import logging
from lxml import etree
from lxml.etree import Element, SubElement
import pytz
from six import string_types
import struct
import collections

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from io import BytesIO
except ImportError:
    _logger.warning("no se ha cargado io")

try:
    from suds.client import Client
except ImportError:
    pass
try:
    import textwrap
except ImportError:
    pass

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import \
        load_pem_private_key
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except ImportError:
    _logger.warning("Cannot import OpenSSL library")

try:
    import dicttoxml
except ImportError:
    _logger.warning("Cannot import dicttoxml library")

try:
    import pdf417gen
except ImportError:
    _logger.warning("Cannot import pdf417gen library")

try:
    import base64
except ImportError:
    _logger.warning("Cannot import base64 library")

try:
    import hashlib
except ImportError:
    _logger.warning("Cannot import hashlib library")

# timbre patrón. Permite parsear y formar el
# ordered-dict patrón corespondiente al documento
timbre = """<TED version="1.0"><DD><RE>99999999-9</RE><TD>11</TD><F>1</F>\
<FE>2000-01-01</FE><RR>99999999-9</RR><RSR>\
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</RSR><MNT>10000</MNT><IT1>IIIIIII\
</IT1><CAF version="1.0"><DA><RE>99999999-9</RE><RS>YYYYYYYYYYYYYYY</RS>\
<TD>10</TD><RNG><D>1</D><H>1000</H></RNG><FA>2000-01-01</FA><RSAPK><M>\
DJKFFDJKJKDJFKDJFKDJFKDJKDnbUNTAi2IaDdtAndm2p5udoqFiw==</M><E>Aw==</E></RSAPK>\
<IDK>300</IDK></DA><FRMA algoritmo="SHA1withRSA">\
J1u5/1VbPF6ASXkKoMOF0Bb9EYGVzQ1AMawDNOy0xSuAMpkyQe3yoGFthdKVK4JaypQ/F8\
afeqWjiRVMvV4+s4Q==</FRMA></CAF><TSTED>2014-04-24T12:02:20</TSTED></DD>\
<FRMT algoritmo="SHA1withRSA">jiuOQHXXcuwdpj8c510EZrCCw+pfTVGTT7obWm/\
fHlAa7j08Xff95Yb2zg31sJt6lMjSKdOK+PQp25clZuECig==</FRMT></TED>"""

try:
    import xmltodict

    result = xmltodict.parse(timbre)
except ImportError:
    _logger.warning("Cannot import xmltodict library")

server_url = {
    "SIICERT": "https://maullin.sii.cl/DTEWS/",
    "SII": "https://palena.sii.cl/DTEWS/",
}

claim_url = {
    "SIICERT": "https://ws2.sii.cl/WSREGISTRORECLAMODTECERT/registroreclamodteservice", # noqa
    "SII": "https://ws1.sii.cl/WSREGISTRORECLAMODTE/registroreclamodteservice", # noqa
}

BC = """-----BEGIN CERTIFICATE-----\n"""
EC = """\n-----END CERTIFICATE-----\n"""

# hardcodeamos este valor por ahora

USING_PYTHON2 = True if sys.version_info < (3, 0) else False
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace("/models",
                                                              "/static/xsd/")

TYPE2JOURNAL = {
    "out_invoice": "sale",
    "in_invoice": "purchase",
    "out_refund": "sale",
    "in_refund": "purchase",
}


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _default_journal_document_class_id(self, default=None):
        ids = self._get_available_journal_document_class()
        document_classes = \
            self.env["account.journal.sii.document.class"].browse(ids)
        if default:
            for dc in document_classes:
                if dc.sii_document_class_id.id == default:
                    self.journal_document_class_id = dc.id
        elif document_classes:
            default = self.get_document_class_default(document_classes)
        return default

    def _domain_journal_document_class_id(self):
        domain = self._get_available_journal_document_class()
        return [("id", "in", domain)]

    def _compute_barcode_img(self):
        for r in self:
            if r.sii_barcode:
                barcodefile = BytesIO()
                image = self.pdf417bc(r.sii_barcode)
                image.save(barcodefile, "PNG")
                data = barcodefile.getvalue()
                r.sii_barcode_img = base64.b64encode(data)

    vat_discriminated = fields.Boolean(
        "Discriminate VAT?",
        compute="_compute_vat_discriminated",
        store=True,
        readonly=False,
        help="Discriminate VAT on Quotations and Sale Orders?",
    )
    available_journal_document_class_ids = fields.Many2many(
        "account.journal.sii.document.class",
        #    compute='_get_available_journal_document_class',
        string="Available Journal Document Classes",
    )
    journal_document_class_id = fields.Many2one(
        "account.journal.sii.document.class",
        string="Documents Type",
        default=lambda self: self._default_journal_document_class_id(),
        domain=_domain_journal_document_class_id,
        readonly=True,
        store=True,
        states={"draft": [("readonly", False)]},
    )
    sii_document_class_id = fields.Many2one(
        "sii.document.class",
        related="journal_document_class_id.sii_document_class_id",
        string="Document Type",
        copy=False,
        readonly=True,
        store=True,
    )
    sii_document_number = fields.Char(
        string="Document Number", copy=False, readonly=True
    )
    responsability_id = fields.Many2one(
        "sii.responsability",
        string="Responsability",
        related="commercial_partner_id.responsability_id",
        store=True,
    )
    iva_uso_comun = fields.Boolean(
        string="Uso Común", readonly=True,
        states={"draft": [("readonly", False)]}
    )  # solamente para compras tratamiento del iva
    no_rec_code = fields.Selection([
        ("1", "Compras destinadas a IVA a generar operaciones no gravados o "
              "exentas."),
        ("2", "Facturas de proveedores registrados fuera de plazo."),
        ("3", "Gastos rechazados."),
        ("4", "Entregas gratuitas (premios, bonificaciones, etc.) recibidos."),
        ("9", "Otros.")],
        string="Código No recuperable",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )  # @TODO select 1 automático si es emisor 2Categoría

    document_number = fields.Char(
        compute="_compute_document_number", string="Ref. Number",
        readonly=True)
    next_invoice_number = fields.Integer(
        related="journal_document_class_id.sequence_id.number_next_actual",
        string="Next Document Number",
        readonly=True,
    )
    use_documents = fields.Boolean(
        related="journal_id.use_documents", string="Use Documents?",
        readonly=True
    )
    forma_pago = fields.Selection(
        [("1", "Contado"), ("2", "Crédito"), ("3", "Gratuito")],
        string="Forma de pago",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default="1",
    )
    contact_id = fields.Many2one("res.partner", string="Contacto")
    sii_batch_number = fields.Integer(
        copy=False,
        string="Batch Number",
        readonly=True,
        help="Batch number for processing multiple invoices together",
    )
    sii_barcode = fields.Char(
        copy=False,
        string="SII Barcode",
        help="SII Barcode Name",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    sii_barcode_img = fields.Binary(
        string="SII Barcode Image",
        help="SII Barcode Image in PDF417 format",
        compute="_compute_barcode_img",
    )
    sii_message = fields.Text(string="SII Message", copy=False)
    sii_xml_dte = fields.Text(
        string="SII XML DTE",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    sii_xml_request = fields.Many2one(
        "sii.xml.envio", string="SII XML Request", copy=False
    )
    sii_result = fields.Selection(
        [
            ("draft", "Borrador"),
            ("NoEnviado", "No Enviado"),
            ("EnCola", "En cola de envío"),
            ("Enviado", "Enviado"),
            ("Aceptado", "Aceptado"),
            ("Rechazado", "Rechazado"),
            ("Reparo", "Reparo"),
            ("Proceso", "Procesado"),
            ("Anulado", "Anulado"),
        ],
        string="Resultado",
        help="SII request result",
        copy=False,
    )
    canceled = fields.Boolean(string="Canceled?", copy=False)
    estado_recep_dte = fields.Selection(
        [
            ("recibido", "Recibido en DTE"),
            ("mercaderias", "Recibido mercaderias"),
            ("validate", "Validada Comercial"),
        ],
        string="Estado de Recepcion del Envio",
        default="recibido",
        copy=False,
    )
    estado_recep_glosa = fields.Char(
        string="Información Adicional del Estado de Recepción", copy=False
    )
    ticket = fields.Boolean(
        string="Formato Ticket",
        default=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    claim = fields.Selection(
        [
            ("ACD", "Acepta Contenido del Documento"),
            ("RCD", "Reclamo al  Contenido del Documento "),
            ("ERM", " Otorga  Recibo  de  Mercaderías  o Servicios"),
            ("RFP", "Reclamo por Falta Parcial de Mercaderías"),
            ("RFT", "Reclamo por Falta Total de Mercaderías"),
        ],
        string="Reclamo",
        copy=False,
    )
    claim_description = fields.Char(string="Detalle Reclamo", readonly=True)
    purchase_to_done = fields.Many2many(
        "purchase.order",
        string="Ordenes de Compra a validar",
        domain=[("state", "not in", ["done", "cancel"])],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    activity_description = fields.Many2one(
        "sii.activity.description",
        string="Giro",
        related="partner_id.activity_description",
        readonly=True,
    )
    amount_untaxed_global_discount = fields.Float(
        string="Global Discount Amount",
        store=True,
        default=0.00,
        compute="_compute_amount",
    )
    amount_untaxed_global_recargo = fields.Float(
        string="Global Recargo Amount",
        store=True,
        default=0.00,
        compute="_compute_amount",
    )
    global_descuentos_recargos = fields.One2many(
        "account.invoice.gdr",
        "invoice_id",
        string="Descuentos / Recargos globales",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        """
        TODO: Agregar Descuento Global como Concepto a parte en el caso de que
         sea asociado a una aplicación
        """
        total = 0
        total_currency = 0
        amount_diff = self.amount_total
        amount_diff_currency = 0
        gdr = self.porcentaje_dr()
        if self.currency_id != company_currency:
            currency = self.currency_id
            date = self._get_currency_rate_date() or \
                fields.Date.context_today(self)
            amount_diff = currency._convert(
                self.amount_total, company_currency, self.company_id, date
            )
            amount_diff_currency = self.amount_total
        for line in invoice_move_lines:
            # @TODO Posibilidad de GDR a exentos
            exento = False
            if line.get("tax_ids"):
                tax_ids = []
                # el ORM puede pasar (4, id, _) O (6, _, ids), asi que evaluar
                # cada caso ver el metodo write de models.py de odoo, para
                # mayor informacion de cada caso
                if line.get("tax_ids")[0][0] == 4:
                    tax_ids = [line.get("tax_ids")[0][1]]
                elif line.get("tax_ids")[0][0] == 6:
                    tax_ids = line.get("tax_ids")[0][2]
                if tax_ids:
                    exento = self.env["account.tax"].search(
                        [("id", "in", tax_ids), ("amount", "=", 0)])
            if not line.get("tax_line_id") and not exento:
                line["price"] *= gdr
            if line.get("amount_currency", False) and not \
                    line.get("tax_line_id"):
                if not exento:
                    line["amount_currency"] *= gdr
            if self.currency_id != company_currency:
                currency = self.currency_id
                date = self._get_currency_rate_date() or \
                    fields.Date.context_today(self)
                if not (line.get("currency_id") and
                        line.get("amount_currency")):
                    line["currency_id"] = currency.id
                    line["amount_currency"] = currency.round(line["price"])
                    line["price"] = currency._convert(
                        line["price"], company_currency, self.company_id, date
                    )
            else:
                line["currency_id"] = False
                line["amount_currency"] = False
                line["price"] = self.currency_id.round(line["price"])
            # para chequeo diferencia
            amount_diff -= line["price"]
            if line.get("amount_currency", False):
                amount_diff_currency -= line["amount_currency"]
            if self.type in ("out_invoice", "in_refund"):
                total += line["price"]
                total_currency += line["amount_currency"] or line["price"]
                line["price"] = -line["price"]
            else:
                total -= line["price"]
                total_currency -= line["amount_currency"] or line["price"]
        if amount_diff != 0:
            if self.type in ("out_invoice", "in_refund"):
                invoice_move_lines[0]["price"] -= amount_diff
                total += amount_diff
            else:
                invoice_move_lines[0]["price"] += amount_diff
                total -= amount_diff
        if amount_diff_currency != 0:
            invoice_move_lines[0]["amount_currency"] += amount_diff_currency
            total_currency += amount_diff_currency
        return total, total_currency, invoice_move_lines

    @api.depends(
        "invoice_line_ids.price_subtotal",
        "tax_line_ids.amount",
        "tax_line_ids.amount_rounding",
        "currency_id",
        "company_id",
        "date_invoice",
        "type",
        "global_descuentos_recargos",
    )
    def _compute_amount(self):
        for inv in self:
            neto = 0
            if inv.global_descuentos_recargos:
                neto = inv.global_descuentos_recargos.get_monto_aplicar()
                agrupados = inv.global_descuentos_recargos.get_agrupados()
                inv.amount_untaxed_global_discount = agrupados["D"]
                inv.amount_untaxed_global_recargo = agrupados["R"]
            amount_tax = 0
            amount_retention = 0
            included = False
            for tax in inv.tax_line_ids:
                if tax.tax_id.price_include:
                    included = True
                amount_tax += tax.amount
                amount_retention += tax.amount_retention
            inv.amount_retention = amount_retention
            if included:
                neto += inv.tax_line_ids._getNeto(inv.currency_id)
                amount_retention += amount_retention
            else:
                neto += sum(
                    line.price_subtotal
                    for line in inv.invoice_line_ids
                    if line.account_id
                )
            inv.amount_untaxed = neto
            inv.amount_tax = amount_tax
            inv.amount_total = \
                inv.amount_untaxed + inv.amount_tax - amount_retention
            amount_total_company_signed = inv.amount_total
            amount_untaxed_signed = inv.amount_untaxed
            if (
                inv.currency_id
                and inv.company_id
                and inv.currency_id != inv.company_id.currency_id
            ):
                currency_id = inv.currency_id
                amount_total_company_signed = currency_id._convert(
                    inv.amount_total,
                    inv.company_id.currency_id,
                    inv.company_id,
                    inv.date_invoice or fields.Date.today(),
                )
                amount_untaxed_signed = currency_id._convert(
                    inv.amount_untaxed,
                    inv.company_id.currency_id,
                    inv.company_id,
                    inv.date_invoice or fields.Date.today(),
                )
            sign = inv.type in ["in_refund", "out_refund"] and -1 or 1
            inv.amount_total_company_signed = \
                amount_total_company_signed * sign
            inv.amount_total_signed = inv.amount_total * sign
            inv.amount_untaxed_signed = amount_untaxed_signed * sign

    def _prepare_tax_line_vals(self, line, tax):
        vals = super(AccountInvoice, self)._prepare_tax_line_vals(line, tax)
        vals["amount_retention"] = tax["retention"]
        vals["retention_account_id"] = (
            self.type in ("out_invoice", "in_invoice")
            and (tax["refund_account_id"] or line.account_id.id)
            or (tax["account_id"] or line.account_id.id)
        )
        return vals

    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            amount = tax_line.amount_total + tax_line.amount_retention
            if amount:
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                analytic_tag_ids = [
                    (4, analytic_tag.id, None)
                    for analytic_tag in tax_line.analytic_tag_ids
                ]
                done_taxes.append(tax.id)
                if tax_line.amount_total > 0:
                    res.append(
                        {
                            "invoice_tax_line_id": tax_line.id,
                            "tax_line_id": tax_line.tax_id.id,
                            "type": "tax",
                            "name": tax_line.name,
                            "price_unit": tax_line.amount_total,
                            "quantity": 1,
                            "price": tax_line.amount_total,
                            "account_id": tax_line.account_id.id,
                            "account_analytic_id":
                                tax_line.account_analytic_id.id,
                            "analytic_tag_ids": analytic_tag_ids,
                            "invoice_id": self.id,
                            "tax_ids": [(6, 0, done_taxes)]
                            if tax_line.tax_id.include_base_amount
                            else [],
                        }
                    )
                if tax_line.amount_retention > 0:
                    res.append(
                        {
                            "invoice_tax_line_id": tax_line.id,
                            "tax_line_id": tax_line.tax_id.id,
                            "type": "tax",
                            "name": "RET - " + tax_line.name,
                            "price_unit": -tax_line.amount_retention,
                            "quantity": 1,
                            "price": -tax_line.amount_retention,
                            "account_id": tax_line.retention_account_id.id,
                            "account_analytic_id":
                                tax_line.account_analytic_id.id,
                            "analytic_tag_ids": analytic_tag_ids,
                            "invoice_id": self.id,
                            "tax_ids": [(6, 0, done_taxes)]
                            if tax_line.tax_id.include_base_amount
                            else [],
                        }
                    )
        return res

    def porcentaje_dr(self):
        if not self.global_descuentos_recargos:
            return 1
        taxes = super(AccountInvoice, self).get_taxes_values()
        afecto = 0.00
        exento = 0.00
        percentage = 0.00
        total = 0.00
        for tax_id, t in taxes.items():
            tax = self.env["account.tax"].browse(t["tax_id"])
            total += t["base"]
            if tax.amount > 0:
                afecto += t["base"]
            else:
                exento += t["base"]
        agrupados = self.global_descuentos_recargos.get_agrupados()
        amount = agrupados["R"] - agrupados["D"]
        if amount == 0:
            return 1
        percentage = (100.0 * amount) / afecto
        return 1 + (percentage / 100.0)

    def _get_grouped_taxes(self, line, taxes, tax_grouped=None):
        for tax in taxes:
            val = self._prepare_tax_line_vals(line, tax)
            # If the taxes generate moves on the same financial account as the
            # invoice line, propagate the analytic account from the invoice
            # line to the tax line.
            # This is necessary in situations were (part of) the taxes cannot
            # be reclaimed, to ensure the tax move is allocated to the proper
            # analytic account.
            if (
                not val.get("account_analytic_id")
                and line.account_analytic_id
                and val["account_id"] == line.account_id.id
            ):
                val["account_analytic_id"] = line.account_analytic_id.id
            key = \
                self.env["account.tax"].browse(tax["id"]).get_grouping_key(val)
            if key not in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]["amount"] += val["amount"]
                tax_grouped[key]["amount_retention"] += val["amount_retention"]
                tax_grouped[key]["base"] += val["base"]
        return tax_grouped

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        totales = {}
        included = False
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if (
                line.invoice_line_tax_ids and
                    line.invoice_line_tax_ids[0].price_include
            ):  # se asume todos losproductos vienen con precio incluido o no
                # (no hay mixes)
                if (
                    included or not tax_grouped
                ):  # genero error en caso de contenido mixto, en caso primer
                    # impusto no incluido segundo impuesto incluido
                    for t in line.invoice_line_tax_ids:
                        if t not in totales:
                            totales[t] = 0
                        totales[t] += (self.currency_id.round(
                            line.price_unit * line.quantity) * line.discount)
                included = True
            else:
                included = False
            if (totales and not included) or (included and not totales):
                raise UserError(_(
                    "Mixed signature cannot be done, all the taxes in this "
                    "order must be one of those two:\n"
                    "1. Included in price,\n"
                    "2. Not included in price"))
            taxes = line.invoice_line_tax_ids.compute_all(
                line.price_unit,
                self.currency_id,
                line.quantity,
                line.product_id,
                self.partner_id,
                discount=line.discount,
            )["taxes"]
            tax_grouped = self._get_grouped_taxes(line, taxes, tax_grouped)
        if totales:
            for line in self.invoice_line_ids:
                if not line.account_id:
                    continue
                for t in line.invoice_line_tax_ids:
                    taxes = t.compute_all(totales[t],
                                          self.currency_id, 1)["taxes"]
                    tax_grouped = \
                        self._get_grouped_taxes(line, taxes, tax_grouped)
        if not self.global_descuentos_recargos:
            return tax_grouped
        gdr = self.porcentaje_dr()
        taxes = {}
        for t, group in tax_grouped.items():
            if t not in taxes:
                taxes[t] = group
            tax = self.env["account.tax"].browse(group["tax_id"])
            if tax.amount > 0:
                taxes[t]["amount"] *= gdr
                taxes[t]["base"] *= gdr
        return taxes

    @api.onchange("global_descuentos_recargos")
    def _onchange_descuentos(self):
        self._onchange_invoice_line_ids()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None, tipo_nota=61,
                        mode="1"):
        values = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice, date, description, journal_id)
        document_type = self.env["account.journal.sii.document.class"].search([
            ("sii_document_class_id.sii_code", "=", tipo_nota),
            ("journal_id", "=", invoice.journal_id.id)], limit=1)
        if invoice.type == "out_invoice":
            invoice_type = "out_refund"
        elif invoice.type == "out_refund":
            invoice_type = "out_invoice"
        elif invoice.type == "in_invoice":
            invoice_type = "in_refund"
        elif invoice.type == "in_refund":
            invoice_type = "in_invoice"
        values.update({
            "type": invoice_type,
            "journal_document_class_id": document_type.id,
            "reference_ids": [[0, 0, {
                "origen":
                    int(invoice.sii_document_number or invoice.reference),
                "class_id": invoice.class_id.id,
                "code": mode,
                "motivo": description,
                "fecha_documento": invoice.date_invoice}]]})
        return values

    @api.multi
    @api.returns("self")
    def refund(self, date_invoice=None, date=None, description=None,
               journal_id=None, tipo_nota=61, mode="1"):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(
                invoice,
                date_invoice=date_invoice,
                date=date,
                description=description,
                journal_id=journal_id,
                tipo_nota=tipo_nota,
                mode=mode)
            refund_invoice = self.create(values)
            invoice_type = {
                "out_invoice": ("customer invoices credit note"),
                "out_refund": ("customer invoices debit note"),
                "in_invoice": ("vendor bill credit note"),
                "in_refund": ("vendor bill debit note")}
            message = _(
                "This %s has been created from: "
                "<a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>"
                "<br>Reason: %s") % (
                invoice_type[invoice.type], invoice.id, invoice.number,
                description)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices

    def get_document_class_default(self, document_classes):
        document_class_id = None
        # @TODO compute from company or journal
        # if self.turn_issuer.vat_affected not in ['SI', 'ND']:
        #    exempt_ids = [
        #        self.env.ref('l10n_cl_electronic_invoicing.dc_y_f_dtn').id,
        #        self.env.ref('l10n_cl_electronic_invoicing.dc_y_f_dte').id]
        #    for document_class in document_classes:
        #        if document_class.sii_document_class_id.id in exempt_ids:
        #            document_class_id = document_class.id
        #            break
        #        else:
        #            document_class_id = document_classes.ids[0]
        # else:
        document_class_id = document_classes.ids[0]
        return document_class_id

    @api.multi
    def name_get(self):
        TYPES = {
            "out_invoice": _("Invoice"),
            "in_invoice": _("Supplier Invoice"),
            "out_refund": _("Refund"),
            "in_refund": _("Supplier Refund"),
        }
        result = []
        for inv in self:
            result.append(
                (
                    inv.id,
                    "%s %s" % (inv.document_number or TYPES[inv.type],
                               inv.name or ""),
                )
            )
        return result

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([("document_number", "=", name)] + args,
                               limit=limit)
        if not recs:
            recs = self.search([("name", operator, name)] + args, limit=limit)
        return recs.name_get()

    def action_invoice_cancel(self):
        if self.sii_result not in [False, "draft", "NoEnviado", "Rechazado",
                                   "Anulado"]:
            raise UserError(_("You cannot cancel a document already accepted "
                              "by SII."))
        return super(AccountInvoice, self).action_invoice_cancel()

    def _buscarTaxEquivalente(self, tax):
        tax_n = self.env["account.tax"].search(
            [
                ("sii_code", "=", tax.sii_code),
                ("sii_type", "=", tax.sii_type),
                ("retention", "=", tax.retention),
                ("type_tax_use", "=", tax.type_tax_use),
                ("no_rec", "=", tax.no_rec),
                ("company_id", "=", self.company_id.id),
                ("price_include", "=", tax.price_include),
                ("amount", "=", tax.amount),
                ("amount_type", "=", tax.amount_type),
            ]
        )
        return tax_n

    def _crearTaxEquivalente(self, tax):
        tax_n = self.env["account.tax"].create(
            {
                "sii_code": tax.sii_code,
                "sii_type": tax.sii_type,
                "retention": tax.retention,
                "type_tax_use": tax.type_tax_use,
                "no_rec": tax.no_rec,
                "name": tax.name,
                "description": tax.description,
                "tax_group_id": tax.tax_group_id.id,
                "company_id": self.company_id.id,
                "price_include": tax.price_include,
                "amount": tax.amount,
                "amount_type": tax.amount_type,
                "account_id": tax.account_id.id,
                "refund_account_id": tax.refund_account_id.id,
            }
        )
        return tax_n

    @api.onchange("partner_id")
    def update_journal(self):
        self.journal_id = self._default_journal()
        self.set_default_journal()
        return self.update_domain_journal()

    @api.onchange("company_id")
    def _refreshRecords(self):
        self.journal_id = self._default_journal()
        invoice_type = self._context.get("type") or "out_invoice"
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            tax_ids = []
            account = line.get_invoice_line_account(
                invoice_type, line.product_id, self.fiscal_position_id,
                self.company_id
            )
            if account:
                line.account_id = account.id
            if invoice_type in ("out_invoice", "out_refund"):
                for tax in line.product_id.taxes_id:
                    if tax.company_id.id == self.company_id.id:
                        tax_ids.append(tax.id)
                    else:
                        tax_n = self._buscarTaxEquivalente(tax)
                        if not tax_n:
                            tax_n = self._crearTaxEquivalente(tax)
                        tax_ids.append(tax_n.id)
                line.product_id.taxes_id = False
                line.product_id.taxes_id = tax_ids
            else:
                for tax in line.product_id.supplier_taxes_id:
                    if tax.company_id.id == self.company_id.id:
                        tax_ids.append(tax.id)
                    else:
                        tax_n = self._buscarTaxEquivalente(tax)
                        if not tax_n:
                            tax_n = self._crearTaxEquivalente(tax)
                        tax_ids.append(tax_n.id)
                line.invoice_line_tax_ids = False
                line.product_id.supplier_taxes_id.append = tax_ids
            line.invoice_line_tax_ids = False
            line.invoice_line_tax_ids = tax_ids

    def _get_available_journal_document_class(self):
        context = dict(self._context or {})
        journal_id = self.journal_id
        if not journal_id and "default_journal_id" in context:
            journal_id = self.env["account.journal"].browse(
                context["default_journal_id"]
            )
        if not journal_id:
            journal_id = self.env["account.journal"].search(
                [("type", "=", "sale")], limit=1
            )
        invoice_type = self.type or context.get("default_type", False)
        if not invoice_type:
            invoice_type = (
                "in_invoice" if journal_id.type == "purchase" else
                "out_invoice")
        document_class_ids = []
        nd = False
        for ref in self.reference_ids:
            if not nd:
                nd = ref.code
        if invoice_type in ["out_invoice", "in_invoice", "out_refund",
                            "in_refund"]:
            if journal_id:
                domain = [("journal_id", "=", journal_id.id)]
            else:
                operation_type = self.get_operation_type(invoice_type)
                domain = [("journal_id.type", "=", operation_type)]
            if invoice_type in ["in_refund", "out_refund"]:
                domain += [
                    ("sii_document_class_id.document_type", "in",
                     ["credit_note"])
                ]
            else:
                options = ["invoice", "invoice_in"]
                if nd:
                    options.append("debit_note")
                domain += \
                    [("sii_document_class_id.document_type", "in", options)]
            document_classes = \
                self.env["account.journal.sii.document.class"].search(
                    domain)
            document_class_ids = document_classes.ids
        return document_class_ids

    @api.onchange("journal_id", "partner_id")
    def update_domain_journal(self):
        document_classes = self._get_available_journal_document_class()
        return {"domain": {
            "journal_document_class_id": [("id", "in", document_classes)]}}

    @api.depends("journal_id")
    @api.onchange("journal_id", "partner_id")
    def set_default_journal(self, default=None):
        if (
            not self.journal_document_class_id
            or self.journal_document_class_id.journal_id != self.journal_id
        ):
            query = []
            if not default and not self.journal_document_class_id:
                query.append(
                    ("sii_document_class_id",
                     "=",
                     self.journal_document_class_id.sii_document_class_id.id)
                )
            if (
                self.journal_document_class_id.journal_id != self.journal_id
                or not default
            ):
                query.append(("journal_id", "=", self.journal_id.id))
            if query:
                default = (
                    self.env["account.journal.sii.document.class"]
                    .search(query, order="sequence asc", limit=1)
                    .id
                )
            self.journal_document_class_id = \
                self._default_journal_document_class_id(default)

    @api.onchange("sii_document_class_id", "partner_id")
    def _check_vat(self):
        if (
            self.partner_id
            and not self._es_boleta()
            and not self.partner_id.commercial_partner_id.document_number
            and self.vat_discriminated
        ):
            raise UserError(
                _(
                    """The customer/supplier does not have a VAT \
defined. The type of invoicing document you selected requires you tu settle \
a VAT."""
                )
            )

    @api.depends(
        "sii_document_class_id",
        "sii_document_class_id.document_letter_id",
        "sii_document_class_id.document_letter_id.vat_discriminated",
        "company_id",
        "company_id.invoice_vat_discrimination_default",
    )
    def _compute_vat_discriminated(self):
        for inv in self:
            vat_discriminated = False
            # agregarle una condicion: si el giro es afecto a iva, debe
            # seleccionar factura, de lo contrario boleta (to-do)
            if (
                inv.sii_document_class_id.document_letter_id.vat_discriminated
                or inv.company_id.invoice_vat_discrimination_default
                == "discriminate_default"
            ):
                vat_discriminated = True
            inv.vat_discriminated = vat_discriminated

    @api.depends("sii_document_number", "number")
    def _compute_document_number(self):
        for inv in self:
            if inv.sii_document_number and inv.sii_document_class_id:
                document_number = (
                    inv.sii_document_class_id.doc_code_prefix or ""
                ) + inv.sii_document_number
            else:
                document_number = inv.number
            inv.document_number = document_number

    @api.constrains("reference", "partner_id", "company_id", "type",
                    "journal_document_class_id")
    def _check_reference_in_invoice(self):
        if self.type in ["in_invoice", "in_refund"] and self.reference:
            domain = [
                ("type", "=", self.type),
                ("reference", "=", self.reference),
                ("partner_id", "=", self.partner_id.id),
                ("journal_document_class_id.sii_document_class_id", "=",
                 self.journal_document_class_id.sii_document_class_id.id),
                ("company_id", "=", self.company_id.id),
                ("id", "!=", self.id)]
            invoice_ids = self.search(domain)
            if invoice_ids:
                raise UserError(_(
                    "The vendor bill number must be unique per vendor.\n"
                    "Another document with the number %s already exists for "
                    "vendor: %s") %
                    (self.reference, self.partner_id.display_name))

    @api.multi
    def action_move_create(self):
        for obj_inv in self:
            invtype = obj_inv.type
            if obj_inv.journal_document_class_id and not \
                    obj_inv.sii_document_number:
                if invtype in ("out_invoice", "out_refund"):
                    if not obj_inv.journal_document_class_id.sequence_id:
                        raise UserError(
                            _("Please define sequence on the journal related"
                              " documents to this invoice."))
                    sii_document_number = (
                        obj_inv.journal_document_class_id.sequence_id.
                        next_by_id()
                    )
                    prefix = (
                        obj_inv.journal_document_class_id.
                        sii_document_class_id.doc_code_prefix
                        or ""
                    )
                    move_name = (prefix + str(sii_document_number)).\
                        replace(" ", "")
                    obj_inv.write({"move_name": move_name})
                elif invtype in ("in_invoice", "in_refund"):
                    sii_document_number = obj_inv.reference
        super(AccountInvoice, self).action_move_create()
        for obj_inv in self:
            invtype = obj_inv.type
            if obj_inv.journal_document_class_id and not \
                    obj_inv.sii_document_number:
                obj_inv.write({"sii_document_number": sii_document_number})
            document_class_id = obj_inv.sii_document_class_id.id
            guardar = {
                "document_class_id": document_class_id,
                "sii_document_number": obj_inv.sii_document_number,
                "no_rec_code": obj_inv.no_rec_code,
                "iva_uso_comun": obj_inv.iva_uso_comun,
            }
            obj_inv.move_id.write(guardar)
        return True

    def get_operation_type(self, invoice_type):
        if invoice_type in ["in_invoice", "in_refund"]:
            operation_type = "purchase"
        elif invoice_type in ["out_invoice", "out_refund"]:
            operation_type = "sale"
        else:
            operation_type = False
        return operation_type

    def get_valid_document_letters(
            self, partner_id, operation_type="sale", company=False,
            vat_affected="SI", invoice_type="out_invoice", nd=False):
        document_letter_obj = self.env["sii.document.letter"]
        partner = self.partner_id

        if not partner_id or not company or not operation_type:
            return []

        partner = partner.commercial_partner_id
        if operation_type == "sale":
            issuer_responsability_id = company.partner_id.responsability_id.id
            receptor_responsability_id = partner.responsability_id.id
            domain = [
                ("issuer_ids", "=", issuer_responsability_id),
                ("receptor_ids", "=", receptor_responsability_id),
            ]
            if invoice_type == "out_invoice" and not nd:
                if vat_affected == "SI":
                    domain.append(("name", "!=", "C"))
                else:
                    domain.append(("name", "=", "C"))
        elif operation_type == "purchase":
            issuer_responsability_id = partner.responsability_id.id
            domain = [("issuer_ids", "=", issuer_responsability_id)]
        else:
            raise UserError(
                _("Operation Type Error"),
                _('Operation Type Must be "Sale" or "Purchase"'),
            )

        # TODO: fijar esto en el wizard, o llamar un wizard desde aca
        # if not company.partner_id.responsability_id.id:
        #     raise except_orm(_('You have not settled a tax payer type for
        #     your company.'),
        #      _('Please, set your company tax payer type (in company or \
        #      partner before to continue.'))
        document_letter_ids = document_letter_obj.search(domain)
        return document_letter_ids

    @api.multi
    def _check_duplicate_supplier_reference(self):
        for invoice in self:
            if invoice.type in ("in_invoice", "in_refund") and\
                    invoice.reference:
                if self.search([("reference", "=", invoice.reference),
                                ("journal_document_class_id", "=",
                                 invoice.journal_document_class_id.id),
                                ("partner_id", "=", invoice.partner_id.id),
                                ("type", "=", invoice.type),
                                ("id", "!=", invoice.id)]):
                    raise UserError(_(
                        "The document %s with the folio %s of the company %s "
                        "is now stored")
                        % (invoice.journal_document_class_id.
                           sii_document_class_id.name,
                           invoice.reference,
                           invoice.partner_id.name))

    @api.multi
    def invoice_validate(self):
        for inv in self:
            if (inv.sii_document_class_id.sii_code in
                    [55, 56, 60, 61, 111, 112, 802] and not inv.reference_ids):
                raise UserError(_(
                    "Per legal requirement every note must include a reference"
                    " to the document they are related."))
            if not inv.journal_id.use_documents or not \
                    inv.sii_document_class_id.dte:
                continue
            inv.sii_result = "NoEnviado"
            inv.responsable_envio = self.env.user.id
            if inv.type in ["out_invoice", "out_refund"]:
                if inv.journal_id.restore_mode:
                    inv.sii_result = "Proceso"
                else:
                    inv._timbrar()
                    tiempo_pasivo = datetime.now() + timedelta(
                        hours=int(
                            self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("account.auto_send_dte", default=12)
                        )
                    )
                    self.env["sii.cola.envio"].create(
                        {
                            "doc_ids": [inv.id],
                            "model": "account.invoice",
                            "user_id": self.env.uid,
                            "tipo_trabajo": "pasivo",
                            "date_time": tiempo_pasivo,
                            "send_email": False
                            if inv.company_id.dte_service_provider == "SIICERT"
                            or not self.env["ir.config_parameter"]
                            .sudo()
                            .get_param("account.auto_send_email", default=True)
                            else True,
                        }
                    )
            if inv.purchase_to_done:
                for ptd in inv.purchase_to_done:
                    ptd.write({"state": "done"})
        return super().invoice_validate()

    @api.model
    def create(self, vals):
        inv = super().create(vals)
        inv.update_domain_journal()
        inv.set_default_journal()
        return inv

    @api.model
    def _default_journal(self):
        if self._context.get("default_journal_id", False):
            return self.env["account.journal"].browse(
                self._context.get("default_journal_id")
            )
        company_id = self._context.get(
            "company_id", self.company_id.id or self.env.user.company_id.id
        )
        if self._context.get("honorarios", False):
            inv_type = self._context.get("type", "out_invoice")
            inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
            domain = [
                ("journal_document_class_ids.sii_document_class_id."
                 "document_letter_id.name",
                 "=",
                 "M"),
                ("type", "in",
                 [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL])
                ("company_id", "=", company_id),
            ]
            journal_id = self.env["account.journal"].search(domain, limit=1)
            return journal_id
        inv_type = self._context.get("type", "out_invoice")
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        domain = [
            (
                "type",
                "in",
                [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL],
            ),
            ("company_id", "=", company_id),
        ]
        return self.env["account.journal"].search(domain, limit=1,
                                                  order="sequence asc")

    def get_resolution_data(self, comp_id):
        resolution_data = {
            "dte_resolution_date": comp_id.dte_resolution_date,
            "dte_resolution_number": comp_id.dte_resolution_number,
        }
        return resolution_data

    def create_template_envio(
            self, RutEmisor, RutReceptor, FchResol, NroResol, TmstFirmaEnv,
            EnvioDTE, signature_d, SubTotDTE):
        xml = """<SetDTE ID="SetDoc">
<Caratula version="1.0">
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<RutReceptor>{2}</RutReceptor>
<FchResol>{3}</FchResol>
<NroResol>{4}</NroResol>
<TmstFirmaEnv>{5}</TmstFirmaEnv>
{6}</Caratula>{7}
</SetDTE>
""".format(
            RutEmisor,
            signature_d["subject_serial_number"],
            RutReceptor,
            FchResol,
            NroResol,
            TmstFirmaEnv,
            SubTotDTE,
            EnvioDTE,
        )
        return xml

    def time_stamp(self, formato="%Y-%m-%dT%H:%M:%S"):
        tz = pytz.timezone("America/Santiago")
        return datetime.now(tz).strftime(formato)

    def _get_xsd_types(self):
        return {
            "doc": "DTE_v10.xsd",
            "env": "EnvioDTE_v10.xsd",
            "env_boleta": "EnvioBOLETA_v11.xsd",
            "recep": "Recibos_v10.xsd",
            "env_recep": "EnvioRecibos_v10.xsd",
            "env_resp": "RespuestaEnvioDTE_v10.xsd",
            "sig": "xmldsignature_v10.xsd",
        }

    def _get_xsd_file(self, validacion, path=False):
        validacion_type = self._get_xsd_types()
        return (path or xsdpath) + validacion_type[validacion]

    def xml_validator(self, some_xml_string, validacion="doc"):
        if validacion == "bol":
            return True
        xsd_file = self._get_xsd_file(validacion)
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            xml_doc = etree.fromstring(some_xml_string)
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            _logger.warning(etree.tostring(xml_doc))
            raise UserError(_("XML Malformed Error:  %s") % e.args)

    def create_template_doc(self, doc):
        xml = """<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
{}
</DTE>""".format(
            doc
        )
        return xml

    def create_template_env(self, doc):
        xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" \
version="1.0">
{}
</EnvioDTE>""".format(
            doc
        )
        return xml

    def create_template_env_boleta(self, doc):
        xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioBOLETA xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioBOLETA_v11.xsd" \
version="1.0">
{}
</EnvioBOLETA>""".format(
            doc
        )
        return xml

    def create_template_doc1(self, doc, sign):
        xml = doc.replace("</DTE>", sign.decode() + "</DTE>")
        return xml

    def create_template_env1(self, doc, sign):
        xml = doc.replace("</EnvioDTE>", sign.decode() + "</EnvioDTE>")
        return xml

    def append_sign_recep(self, doc, sign):
        xml = doc.replace("</Recibo>", sign.decode() + "</Recibo>")
        return xml

    def append_sign_env_recep(self, doc, sign):
        xml = doc.replace("</EnvioRecibos>", sign.decode() + "</EnvioRecibos>")
        return xml

    def append_sign_env_resp(self, doc, sign):
        xml = doc.replace("</RespuestaDTE>", sign.decode() + "</RespuestaDTE>")
        return xml

    def append_sign_env_bol(self, doc, sign):
        xml = doc.replace("</EnvioBOLETA>", sign.decode() + "</EnvioBOLETA>")
        return xml

    def ensure_str(self, x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x

    def long_to_bytes(self, n, blocksize=0):
        s = b""
        if USING_PYTHON2:
            n = long(n)  # noqa
        pack = struct.pack
        while n > 0:
            s = pack(b">I", n & 0xFFFFFFFF) + s
            n = n >> 32
        # strip off leading zeros
        for i in range(len(s)):
            if s[i] != b"\000"[0]:
                break
        else:
            # only happens when n == 0
            s = b"\000"
            i = 0
        s = s[i:]
        # add back some pad bytes.  this could be done more efficiently w.r.t.
        # the de-padding being done above, but sigh...
        if blocksize > 0 and len(s) % blocksize:
            s = (blocksize - len(s) % blocksize) * b"\000" + s
        return s

    def _append_sig(self, doc_type, msg, message):
        if doc_type in ["doc", "bol"]:
            fulldoc = self.create_template_doc1(message, msg)
        if doc_type == "env":
            fulldoc = self.create_template_env1(message, msg)
        if doc_type == "recep":
            fulldoc = self.append_sign_recep(message, msg)
        if doc_type == "env_recep":
            fulldoc = self.append_sign_env_recep(message, msg)
        if doc_type == "env_resp":
            fulldoc = self.append_sign_env_resp(message, msg)
        if doc_type == "env_boleta":
            fulldoc = self.append_sign_env_bol(message, msg)
        return fulldoc

    def sign_full_xml(self, message, uri, doc_type="doc"):
        # Esto debemos mejorar. Buscamos a la primera que consiga con
        # certificado
        obj = self.env["res.company"].search([("status", "=", "valid")],
                                             limit=1)
        signature_id = {
            "subject_name": obj.name,
            "subject_serial_number": obj.subject_serial_number,
            "priv_key": obj.priv_key,
            "cert": obj.cert}
        if not obj:
            raise UserError(_(
                "There is no Signer Person with an authorized signature for "
                "you in the system. Please make sure that 'user_signature_key' "
                "module has been installed and enable a digital signature, for "
                "you or make the signer to authorize you to use his "
                "signature."))
        cert = (signature_id["cert"].replace(BC, "").replace(EC, "")
                .replace("\n", "").replace(" ", ""))
        privkey = signature_id["priv_key"]
        doc = etree.fromstring(message)
        string = etree.tostring(doc[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        digest = base64.b64encode(self.digest(mess))
        reference_uri = "#" + uri
        signed_info = Element("SignedInfo")
        SubElement(signed_info, "CanonicalizationMethod",
                   Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        SubElement(signed_info, "SignatureMethod",
                   Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1")
        reference = SubElement(signed_info, "Reference", URI=reference_uri)
        transforms = SubElement(reference, "Transforms")
        SubElement(transforms, "Transform",
                   Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        SubElement(reference, "DigestMethod",
                   Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_value = SubElement(reference, "DigestValue")
        digest_value.text = digest
        signed_info_c14n = etree.tostring(
            signed_info, method="c14n", exclusive=False, with_comments=False,
            inclusive_ns_prefixes=None)
        if doc_type in ["doc", "recep"]:
            att = 'xmlns="http://www.w3.org/2000/09/xmldsig#"'
        else:
            att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" ' \
                  'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        # TODO: Find better way to add xmlns:xsi attrib
        signed_info_c14n = signed_info_c14n.decode().replace(
            "<SignedInfo>", "<SignedInfo %s>" % att)
        sig_root = Element(
            "Signature", attrib={"xmlns": "http://www.w3.org/2000/09/xmldsig#"}
        )
        sig_root.append(etree.fromstring(signed_info_c14n))
        signature_value = SubElement(sig_root, "SignatureValue")
        key = crypto.load_privatekey(type_, privkey.encode("ascii"))
        signature = crypto.sign(key, signed_info_c14n, "sha1")
        signature_value.text = \
            textwrap.fill(base64.b64encode(signature).decode(), 64)
        key_info = SubElement(sig_root, "KeyInfo")
        key_value = SubElement(key_info, "KeyValue")
        rsa_key_value = SubElement(key_value, "RSAKeyValue")
        modulus = SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(
            privkey.encode("ascii"), password=None, backend=default_backend())
        modulus.text = textwrap.fill(
            base64.b64encode(self.long_to_bytes(
                key.public_key().public_numbers().n)).decode(), 64)
        exponent = SubElement(rsa_key_value, "Exponent")
        exponent.text = self.ensure_str(
            base64.b64encode(self.long_to_bytes(key.public_key().
                                                public_numbers().e)))
        x509_data = SubElement(key_info, "X509Data")
        x509_certificate = SubElement(x509_data, "X509Certificate")
        x509_certificate.text = "\n" + textwrap.fill(cert, 64)
        msg = etree.tostring(sig_root)
        msg = msg if self.xml_validator(msg, "sig") else ""
        fulldoc = self._append_sig(doc_type, msg, message)
        return fulldoc if self.xml_validator(fulldoc, doc_type) else ""

    def crear_intercambio(self):
        rut = self.format_vat(self.partner_id.commercial_partner_id.vat)
        envio = self._crear_envio(RUTRecep=rut)
        return envio["xml_envio"].encode("ISO-8859-1")

    def _create_attachment(self,):
        xml_intercambio = self.crear_intercambio()
        url_path = "/download/xml/invoice/%s" % (self.id)
        filename = ("%s.xml" % self.document_number).replace(" ", "_")
        att = self.env["ir.attachment"].search([
            ("name", "=", filename),
            ("res_id", "=", self.id),
            ("res_model", "=", "account.invoice")], limit=1)
        if att:
            return att
        data = base64.b64encode(xml_intercambio)
        values = dict(
            name=filename,
            datas_fname=filename,
            url=url_path,
            res_model="account.invoice",
            res_id=self.id,
            type="binary",
            datas=data)
        att = self.env["ir.attachment"].sudo().create(values)
        return att

    @api.multi
    def action_invoice_sent(self):
        result = super(AccountInvoice, self).action_invoice_sent()
        if self.sii_xml_dte:
            att = self._create_attachment()
            result["context"].update({"default_attachment_ids": att.ids})
        return result

    @api.multi
    def get_xml_file(self):
        url_path = "/download/xml/invoice/%s" % (self.id)
        return {"type": "ir.actions.act_url", "url": url_path,
                "target": "self"}

    @api.multi
    def get_xml_exchange_file(self):
        url_path = "/download/xml/invoice_exchange/%s" % (self.id)
        return {"type": "ir.actions.act_url", "url": url_path,
                "target": "self"}

    def get_folio(self):
        # saca el folio directamente de la secuencia
        return int(self.sii_document_number)

    def format_vat(self, value, con_cero=False):
        """ Se Elimina el 0 para prevenir problemas con el sii, ya que las
        muestras no las toma si va con el 0, y tambien internamente se generan
        problemas, se mantiene el 0 delante, para cosultas, o sino retorna
        "error de datos """
        if not value or value == "" or value == 0:
            value = "CL666666666"
            # @TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + "-" + value[10:]
        if not con_cero:
            rut = rut.replace("CL0", "")
        rut = rut.replace("CL", "")
        return rut

    def pdf417bc(self, ted):
        bc = pdf417gen.encode(ted, security_level=5, columns=13)
        image = pdf417gen.render_image(bc, padding=15, scale=1)
        return image

    def digest(self, data):
        sha1 = hashlib.new("sha1", data)
        return sha1.digest()

    def signmessage(self, texto, key):
        key = crypto.load_privatekey(type_, key)
        signature = crypto.sign(key, texto, "sha1")
        text = base64.b64encode(signature).decode()
        return textwrap.fill(text, 64)

    @api.multi
    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        rel_invoices = self.search(
            [
                ("number", "=", self.origin),
                ("state", "not in", ["draft", "proforma", "proforma2",
                                     "cancel"]),
            ]
        )
        return rel_invoices

    def _acortar_str(self, texto, size=1):
        c = 0
        cadena = ""
        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1
        return cadena

    @api.multi
    def do_dte_send_invoice(self, n_atencion=None):
        ids = []
        envio_boleta = False
        for inv in self.with_context(lang="es_CL"):
            if (
                inv.sii_result in ["", "NoEnviado", "Rechazado"]
                or inv.company_id.dte_service_provider == "SIICERT"
            ):
                if inv.sii_result in ["Rechazado"]:
                    inv._timbrar()
                    if inv.sii_xml_request:
                        inv.sii_xml_request.unlink()
                inv.sii_result = "EnCola"
                ids.append(inv.id)
                if not envio_boleta and (inv._es_boleta() or inv._nc_boleta()):
                    envio_boleta = True
        if not isinstance(n_atencion, string_types):
            n_atencion = ""
        if ids:
            if envio_boleta:
                self.browse(ids).do_dte_send(n_atencion)
                return
            self.env["sii.cola.envio"].create(
                {
                    "doc_ids": ids,
                    "model": "account.invoice",
                    "user_id": self.env.user.id,
                    "tipo_trabajo": "envio",
                    "n_atencion": n_atencion,
                    "send_email": False
                    if self[0].company_id.dte_service_provider == "SIICERT"
                    or not self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("account.auto_send_email", default=True)
                    else True,
                }
            )

    @api.multi
    def _es_boleta(self):
        if self.sii_document_class_id.sii_code in [35, 38, 39, 41, 70, 71]:
            return True
        return False

    @api.multi
    def _nc_boleta(self):
        if not self.reference_ids or self.type != "out_refund":
            return False
        for r in self.reference_ids:
            if r.class_id.sii_code in [35, 38, 39, 41, 70, 71]:
                return True
        return False

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.journal_id.journal_activities_ids:
            giros_emisor.extend([{"Acteco": turn.code}])
        return giros_emisor

    def _id_doc(self, taxInclude=False, MntExe=0):
        IdDoc = collections.OrderedDict()
        IdDoc["TipoDTE"] = self.sii_document_class_id.sii_code
        IdDoc["Folio"] = self.get_folio()
        IdDoc["FchEmis"] = self.date_invoice
        if self._es_boleta():
            # TODO: Agregar las otras opciones a la ficha de producto servicio
            IdDoc[
                "IndServicio"
            ] = 3
        if self.ticket:
            IdDoc["TpoImpresion"] = "T"
        # if self.tipo_servicio:
        #    Encabezado['IdDoc']['IndServicio'] = 1,2,3,4
        # todo: forma de pago y fecha de vencimiento - opcional
        if taxInclude and MntExe == 0 and not self._es_boleta():
            IdDoc["MntBruto"] = 1
        if not self._es_boleta():
            IdDoc["FmaPago"] = self.forma_pago or 1
        if not taxInclude and self._es_boleta():
            IdDoc["IndMntNeto"] = 2
        # if self._es_boleta():
        # Servicios periódicos
        #    IdDoc['PeriodoDesde'] =
        #    IdDoc['PeriodoHasta'] =
        if not self._es_boleta():
            IdDoc["FchVenc"] = self.date_due or datetime.strftime(
                datetime.now(), "%Y-%m-%d"
            )
        return IdDoc

    def _emisor(self):
        Emisor = collections.OrderedDict()
        Emisor["RUTEmisor"] = self.format_vat(self.company_id.vat)
        if self._es_boleta():
            Emisor["RznSocEmisor"] = self._acortar_str(
                self.company_id.partner_id.name, 100
            )
            Emisor["GiroEmisor"] = self._acortar_str(
                self.company_id.activity_description.name, 80
            )
        else:
            Emisor["RznSoc"] = self._acortar_str(
                self.company_id.partner_id.name, 100)
            Emisor["GiroEmis"] = self._acortar_str(
                self.company_id.activity_description.name, 80
            )
            if self.company_id.phone:
                Emisor["Telefono"] = \
                    self._acortar_str(self.company_id.phone, 20)
            Emisor["CorreoEmisor"] = self.company_id.dte_email
            Emisor["item"] = self._giros_emisor()
        if self.journal_id.sucursal_id:
            Emisor["Sucursal"] = \
                self._acortar_str(self.journal_id.sucursal_id.name, 20)
            Emisor["CdgSIISucur"] = self._acortar_str(
                self.journal_id.sucursal_id.sii_code, 9
            )
        Emisor["DirOrigen"] = self._acortar_str(
            self.company_id.street + " " + (self.company_id.street2 or ""), 70
        )
        Emisor["CmnaOrigen"] = self.company_id.city_id.name or ""
        Emisor["CiudadOrigen"] = self.company_id.city or ""
        return Emisor

    def _receptor(self):
        Receptor = collections.OrderedDict()
        if (
            not self.commercial_partner_id.vat
            and not self._es_boleta()
            and not self._nc_boleta()
        ):
            raise UserError(_("You must enter the Tax ID of the receptor"))
        # if self._es_boleta():
        #    Receptor['CdgIntRecep']
        Receptor["RUTRecep"] = self.format_vat(self.commercial_partner_id.vat)
        Receptor["RznSocRecep"] = self._acortar_str(
            self.commercial_partner_id.name, 100
        )
        if not self.partner_id or Receptor["RUTRecep"] == "66666666-6":
            return Receptor
        if not self._es_boleta() and not self._nc_boleta():
            if not self.commercial_partner_id.activity_description:
                raise UserError(_("Select giro of the partner"))
            Receptor["GiroRecep"] = self._acortar_str(
                self.commercial_partner_id.activity_description.name, 40)
        if self.partner_id.phone or self.commercial_partner_id.phone:
            Receptor["Contacto"] = self._acortar_str(
                self.partner_id.phone
                or self.commercial_partner_id.phone
                or self.partner_id.email,
                80)
        if (self.commercial_partner_id.email or
            self.commercial_partner_id.dte_email or
            self.partner_id.email or self.partner_id.dte_email) and\
                not self._es_boleta():
            Receptor["CorreoRecep"] = (
                self.commercial_partner_id.dte_email
                or self.partner_id.dte_email
                or self.commercial_partner_id.email
                or self.partner_id.email)
        street_recep = (
            self.partner_id.street or self.commercial_partner_id.street or
            False)
        if not street_recep and not self._es_boleta() and \
                not self._nc_boleta():
            raise UserError(_("You must enter the address of the customer."))
        street2_recep = (
            self.partner_id.street2 or self.commercial_partner_id.street2
            or False)
        Receptor["DirRecep"] = self._acortar_str(
            street_recep + (" " + street2_recep if street2_recep else ""), 70)
        Receptor["CmnaRecep"] = (
            self.partner_id.city_id.name or
            self.commercial_partner_id.city_id.name)
        if (not Receptor["CmnaRecep"] and not self._es_boleta() and
                not self._nc_boleta()):
            raise UserError(_("You must enter the municipality of the "
                              "customer."))
        Receptor["CiudadRecep"] = (
            self.partner_id.city or self.commercial_partner_id.city)
        return Receptor

    def _totales_otra_moneda(
        self,
        currency_id,
        MntExe,
        MntNeto,
        IVA,
        TasaIVA,
        ImptoReten,
        MntTotal=0,
        MntBase=0,
    ):
        Totales = collections.OrderedDict()
        Totales["TpoMoneda"] = self._acortar_str(currency_id.abreviatura, 15)
        Totales["TpoCambio"] = currency_id.rate
        if MntNeto > 0:
            if currency_id:
                MntNeto = currency_id.compute(MntNeto,
                                              self.company_id.currency_id)
            Totales["MntNetoOtrMnda"] = MntNeto
        if MntExe:
            if currency_id:
                MntExe = currency_id.compute(MntExe,
                                             self.company_id.currency_id)
            Totales["MntExeOtrMnda"] = MntExe
        if MntBase and MntBase > 0:
            Totales["MntFaeCarneOtrMnda"] = MntBase
        if TasaIVA:
            if currency_id:
                IVA = currency_id.compute(IVA, self.company_id.currency_id)
            Totales["IVAOtrMnda"] = IVA
        if ImptoReten:
            for item in ImptoReten:
                ret = {"ImptRetOtrMnda": collections.OrderedDict()}
                ret["ImptRetOtrMnda"]["TipoImpOtrMnda"] = \
                    item["ImptRet"]["TipoImp"]
                ret["ImptRetOtrMnda"]["TasaImpOtrMnda"] = \
                    item["ImptRet"]["TasaImp"]
                if currency_id:
                    ret["ImptRetOtrMnda"]["MontoImp"] = currency_id.compute(
                        item["ImptRet"]["MontoImp"],
                        self.company_id.currency_id
                    )
                ret["ImptRetOtrMnda"]["ValorImpOtrMnda"] = \
                    item["ImptRet"]["MontoImp"]
            Totales["item_ret_otr"] = ret
        if currency_id:
            MntTotal = currency_id.compute(MntTotal,
                                           self.company_id.currency_id)
        Totales["MntTotOtrMnda"] = MntTotal
        # Totales['MontoNF']
        # Totales['TotalPeriodo']
        # Totales['SaldoAnterior']
        # Totales['VlrPagar']
        return Totales

    def _totales_normal(
        self,
        currency_id,
        MntExe,
        MntNeto,
        IVA,
        TasaIVA,
        ImptoReten,
        MntTotal=0,
        MntBase=0,
    ):
        Totales = collections.OrderedDict()
        if MntNeto > 0:
            Totales["MntNeto"] = MntNeto
        if MntExe:
            Totales["MntExe"] = MntExe
        if MntBase > 0:
            Totales["MntBase"] = MntBase
        if TasaIVA:
            Totales["TasaIVA"] = TasaIVA
            Totales["IVA"] = IVA
        if ImptoReten:
            Totales["item_ret"] = ImptoReten
        Totales["MntTotal"] = MntTotal
        # Totales['MontoNF']
        # Totales['TotalPeriodo']
        # Totales['SaldoAnterior']
        # Totales['VlrPagar']
        return Totales

    def _es_exento(self):
        return self.sii_document_class_id.code in [34, 41] or (
            self.reference_ids and
            self.reference_ids[0].class_id.code in [34, 41]
        )

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        MntNeto = 0
        IVA = False
        ImptoReten = False
        TasaIVA = False
        MntIVA = 0
        MntBase = 0
        OtrosImp = []
        if self._es_exento():
            MntExe = self.currency_id.round(self.amount_total)
            if no_product:
                MntExe = 0
            if self.amount_tax > 0:
                raise UserError(_("You can't assign products in exempt "
                                  "documents."))
        elif self.amount_untaxed and self.amount_untaxed != 0:
            if not self._es_boleta() or not taxInclude:
                IVA = False
                for t in self.tax_line_ids:
                    if t.tax_id.sii_code in [14, 15]:
                        IVA = t
                    elif t.tax_id.sii_code in [15, 17, 18, 19, 27, 271, 26]:
                        OtrosImp.append(t)
                    if t.tax_id.sii_code in [14, 15]:
                        MntNeto += self.currency_id.round(t.base)
                    if t.tax_id.sii_code in [17]:
                        # TODO: Buscar forma de calcular la base para
                        #  faenamiento
                        MntBase += (
                            IVA.base
                        )
        if self.amount_tax == 0 and MntExe > 0 and not self._es_exento():
            raise UserError(_("You must assign at least one product."))
        if MntExe > 0:
            MntExe = self.currency_id.round(MntExe)
        if not self._es_boleta() or not taxInclude:
            if IVA:
                if not self._es_boleta():
                    TasaIVA = round(IVA.tax_id.amount, 2)
                MntIVA = self.currency_id.round(IVA.amount)
            if no_product:
                MntNeto = 0
                if not self._es_boleta():
                    TasaIVA = 0
                MntIVA = 0
        if OtrosImp:
            ImptoReten = []
            for item in OtrosImp:
                itemRet = {"ImptoReten": collections.OrderedDict()}
                itemRet["ImptoReten"]["TipoImp"] = item.tax_id.sii_code
                itemRet["ImptoReten"]["TasaImp"] = self.currency_id.round(
                    item.tax_id.amount
                )
                itemRet["ImptoReten"]["MontoImp"] = self.currency_id.round(
                    item.amount_retention
                    if item.tax_id.sii_type == "R"
                    else item.amount
                )
                ImptoReten.append(itemRet)
        MntTotal = self.currency_id.round(self.amount_total)
        if no_product:
            MntTotal = 0
        return MntExe, MntNeto, MntIVA, TasaIVA, ImptoReten, MntTotal, MntBase

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        Encabezado = collections.OrderedDict()
        Encabezado["IdDoc"] = self._id_doc(taxInclude, MntExe)
        Encabezado["Emisor"] = self._emisor()
        Encabezado["Receptor"] = self._receptor()
        currency_id = False
        if (
            self.currency_id
            and self.company_id
            and self.currency_id != self.company_id.currency_id
        ):
            currency_id = self.currency_id.with_context(date=self.date_invoice)
        MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal, MntBase = \
            self._totales(MntExe, no_product, taxInclude)
        Encabezado["Totales"] = self._totales_normal(
            currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal,
            MntBase)
        if currency_id:
            Encabezado["OtraMoneda"] = self._totales_otra_moneda(
                currency_id,
                MntExe,
                MntNeto,
                IVA,
                TasaIVA,
                ImptoReten,
                MntTotal,
                MntBase,
            )
        return Encabezado

    @api.multi
    def get_barcode(self, no_product=False):
        ted = False
        folio = self.get_folio()
        result["TED"]["DD"]["RE"] = self.format_vat(self.company_id.vat)
        result["TED"]["DD"]["TD"] = self.sii_document_class_id.sii_code
        result["TED"]["DD"]["F"] = folio
        result["TED"]["DD"]["FE"] = self.date_invoice
        if (
            not self.commercial_partner_id.vat
            and not self._es_boleta()
            and not self._nc_boleta()
        ):
            raise UserError(_("Fill Partner VAT"))
        result["TED"]["DD"]["RR"] = \
            self.format_vat(self.commercial_partner_id.vat)
        result["TED"]["DD"]["RSR"] = self._acortar_str(
            self.commercial_partner_id.name, 40
        )
        result["TED"]["DD"]["MNT"] = self.currency_id.round(self.amount_total)
        if no_product:
            result["TED"]["DD"]["MNT"] = 0
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            result["TED"]["DD"]["IT1"] = \
                self._acortar_str(line.product_id.name, 40)
            if line.product_id.default_code:
                result["TED"]["DD"]["IT1"] = self._acortar_str(
                    line.product_id.name.replace(
                        "[" + line.product_id.default_code + "] ", ""
                    ),
                    40,
                )
            break

        resultcaf = self.journal_document_class_id.sequence_id.get_caf_file(
            self.get_folio()
        )
        result["TED"]["DD"]["CAF"] = resultcaf["AUTORIZACION"]["CAF"]
        dte = result["TED"]["DD"]
        timestamp = self.time_stamp()
        if fields.Date.context_today(self) < self.date_invoice:
            raise UserError(_(
                "The date of the signature cannot be before the date of the "
                "emission document."))
        dte["TSTED"] = timestamp
        dicttoxml.set_debug(False)
        ddxml = (
            "<DD>"
            + dicttoxml.dicttoxml(dte, root=False, attr_type=False)
            .decode()
            .replace('<key name="@version">1.0</key>', "", 1)
            .replace('><key name="@version">1.0</key>', ' version="1.0">', 1)
            .replace('><key name="@algoritmo">SHA1withRSA</key>',
                     ' algoritmo="SHA1withRSA">')
            .replace('<key name="#text">', "")
            .replace("</key>", "")
            .replace("<CAF>", '<CAF version="1.0">')
            + "</DD>"
        )
        keypriv = resultcaf["AUTORIZACION"]["RSASK"].replace("\t", "")
        root = etree.XML(ddxml)
        ddxml = etree.tostring(root)
        frmt = self.signmessage(ddxml, keypriv)
        ted = (
            """<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}\
</FRMT></TED>"""
        ).format(ddxml.decode(), frmt)
        self.sii_barcode = ted
        ted += "<TmstFirma>{}</TmstFirma>".format(timestamp)
        return ted

    @api.multi
    def is_price_included(self):
        if (
            not self.invoice_line_ids
            or not self.invoice_line_ids[0].invoice_line_tax_ids
        ):
            return False
        tax = self.invoice_line_ids[0].invoice_line_tax_ids[0]
        if tax.price_include or (
            not tax.sii_detailed and (self._es_boleta() or self._nc_boleta())
        ):
            return True
        return False

    def _invoice_lines(self):
        line_number = 1
        invoice_lines = []
        no_product = False
        MntExe = 0
        currency_id = False
        if (
            self.currency_id
            and self.company_id
            and self.currency_id != self.company_id.currency_id
        ):
            currency_id = self.currency_id.with_context(date=self.date_invoice)
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if line.product_id.default_code == "NO_PRODUCT":
                no_product = True
            lines = collections.OrderedDict()
            lines["NroLinDet"] = line_number
            if line.product_id.default_code and not no_product:
                lines["CdgItem"] = collections.OrderedDict()
                lines["CdgItem"]["TpoCodigo"] = "INT1"
                lines["CdgItem"]["VlrCodigo"] = line.product_id.default_code
            taxInclude = False
            for t in line.invoice_line_tax_ids:
                taxInclude = t.price_include or (
                    (self._es_boleta() or self._nc_boleta()) and
                    not t.sii_detailed
                )
                if t.amount == 0 or t.sii_code in [
                    0
                ]:  # TODO mejor manera de identificar exento de afecto
                    lines["IndExe"] = 1
                    price_exe = line.price_tax_included
                    MntExe += self.currency_id.round(price_exe)
            # if line.product_id.type == 'events':
            #   lines['ItemEspectaculo'] =
            #            if self._es_boleta():
            #                lines['RUTMandante']
            lines["NmbItem"] = self._acortar_str(line.product_id.name, 80)
            lines["DscItem"] = self._acortar_str(
                line.name, 1000
            )  # descripción más extenza
            if line.product_id.default_code:
                lines["NmbItem"] = self._acortar_str(
                    line.product_id.name.replace(
                        "[" + line.product_id.default_code + "] ", ""
                    ),
                    80,
                )
            # lines['InfoTicket']
            qty = round(line.quantity, 4)
            if not no_product:
                lines["QtyItem"] = qty
            if qty == 0 and not no_product:
                lines["QtyItem"] = 1
            elif qty < 0:
                raise UserError(_("It cannot be lower than 0!"))
            if not no_product:
                lines["UnmdItem"] = line.uom_id.name[:4]
                lines["PrcItem"] = round(line.price_unit, 6)
                for t in line.invoice_line_tax_ids:
                    if t.sii_code in [26, 27, 271]:
                        # Agregar todos los adicionales
                        lines["CodImpAdic"] = t.sii_code
                if currency_id:
                    lines["OtrMnda"] = collections.OrderedDict()
                    lines["OtrMnda"]["PrcOtrMon"] = round(
                        currency_id.compute(
                            line.price_unit, self.company_id.currency_id,
                            round=False
                        ),
                        6,
                    )
                    lines["OtrMnda"]["Moneda"] = self._acortar_str(
                        self.company_id.currency_id.name, 3
                    )
                    lines["OtrMnda"]["FctConv"] = round(currency_id.rate, 4)
            if line.discount > 0:
                if currency_id:
                    lines["OtrMnda"]["DctoOtrMnda"] = line.discount
                lines["DescuentoPct"] = line.discount
                DescMonto = ((line.discount / 100) * lines["PrcItem"]) * qty
                lines["DescuentoMonto"] = self.currency_id.round(DescMonto)
                if currency_id:
                    lines["OtrMnda"]["DctoOtrMnda"] = currency_id.compute(
                        DescMonto, self.company_id.currency_id
                    )
            if not no_product and not taxInclude:
                if currency_id:
                    lines["OtrMnda"]["MontoItemOtrMnda"] = \
                        currency_id.compute(
                            line.price_subtotal,
                            self.company_id.currency_id
                    )
                lines["MontoItem"] = \
                    self.currency_id.round(line.price_subtotal)
            elif not no_product:
                if currency_id:
                    lines["OtrMnda"]["MontoItemOtrMnda"] = \
                        currency_id.compute(
                            line.price_tax_included,
                            self.company_id.currency_id
                    )
                lines["MontoItem"] = self.currency_id.round(
                    line.price_tax_included)
            if no_product:
                lines["MontoItem"] = 0
            line_number += 1
            invoice_lines.extend([{"Detalle": lines}])
            if "IndExe" in lines:
                taxInclude = False
        return {
            "invoice_lines": invoice_lines,
            "MntExe": MntExe,
            "no_product": no_product,
            "tax_include": taxInclude,
        }

    def _gdr(self):
        result = []
        lin_dr = 1
        for dr in self.global_descuentos_recargos:
            dr_line = collections.OrderedDict()
            dr_line["NroLinDR"] = lin_dr
            dr_line["TpoMov"] = dr.type
            if dr.gdr_dtail:
                dr_line["GlosaDR"] = dr.gdr_dtail
            disc_type = "%"
            if dr.gdr_type == "amount":
                disc_type = "$"
            dr_line["TpoValor"] = disc_type
            dr_line["ValorDR"] = self.currency_id.round(dr.valor)
            if (
                self.currency_id
                and self.company_id
                and self.currency_id != self.company_id.currency_id
            ):
                currency_id = \
                    self.currency_id.with_context(date=self.date_invoice)
                dr_line["ValorDROtrMnda"] = currency_id.compute(
                    dr.valor, self.company_id.currency_id
                )
            if self.class_id.code in [34] and (
                self.reference_ids and
                self.reference_ids[0].class_id.code == "34"
            ):  # solamente si es exento
                dr_line["IndExeDR"] = 1
            dr_lines = [{"DscRcgGlobal": dr_line}]
            result.append(dr_lines)
            lin_dr += 1
        return result

    def _dte(self, n_atencion=None):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        dte["Encabezado"] = self._encabezado(
            invoice_lines["MntExe"],
            invoice_lines["no_product"],
            invoice_lines["tax_include"],
        )
        lin_ref = 1
        ref_lines = []
        if (
            self.company_id.dte_service_provider == "SIICERT"
            and isinstance(n_atencion, string_types)
            and n_atencion != ""
            and not self._es_boleta()
        ):
            ref_line = collections.OrderedDict()
            ref_line["NroLinRef"] = lin_ref
            ref_line["TpoDocRef"] = "SET"
            ref_line["FolioRef"] = self.get_folio()
            ref_line["FchRef"] = datetime.strftime(datetime.now(), "%Y-%m-%d")
            ref_line["RazonRef"] = (
                "CASO " + n_atencion + "-" + str(self.sii_batch_number)
            )
            lin_ref = 2
            ref_lines.extend([{"Referencia": ref_line}])
        if self.reference_ids:
            for ref in self.reference_ids:
                ref_line = collections.OrderedDict()
                ref_line["NroLinRef"] = lin_ref
                if not self._es_boleta():
                    if ref.class_id:
                        ref_line["TpoDocRef"] = (
                            self._acortar_str(
                                ref.class_id.doc_code_prefix, 3
                            )
                            if ref.class_id.use_prefix
                            else ref.class_id.code
                        )
                        ref_line["FolioRef"] = ref.origen
                    ref_line["FchRef"] = \
                        ref.fecha_documento or \
                        datetime.strftime(datetime.now(), "%Y-%m-%d")
                if ref.sii_referencia_CodRef not in ["", "none", False]:
                    ref_line["CodRef"] = ref.sii_referencia_CodRef
                ref_line["RazonRef"] = ref.motivo
                if self._es_boleta():
                    ref_line["CodVndor"] = self.seler_id.id
                    ref_lines["CodCaja"] = \
                        self.journal_id.point_of_sale_id.name
                ref_lines.extend([{"Referencia": ref_line}])
                lin_ref += 1
        dte["item"] = invoice_lines["invoice_lines"]
        if self.global_descuentos_recargos:
            dte["drlines"] = self._gdr()
        dte["reflines"] = ref_lines
        dte["TEDd"] = self.get_barcode(invoice_lines["no_product"])
        return dte

    def _dte_to_xml(self, dte, tpo_dte="Documento"):
        ted = dte[tpo_dte + " ID"]["TEDd"]
        dte[(tpo_dte + " ID")]["TEDd"] = ""
        xml = (
            dicttoxml.dicttoxml(dte, root=False, attr_type=False)
            .decode()
            .replace("<item >", "")
            .replace("<item>", "")
            .replace("</item>", "")
            .replace("<reflines>", "")
            .replace("</reflines>", "")
            .replace("<TEDd>", "")
            .replace("</TEDd>", "")
            .replace("</" + tpo_dte + "_ID>", "\n" + ted + "\n</" + tpo_dte +
                     "_ID>")
            .replace("<drlines>", "")
            .replace("</drlines>", "")
            .replace("<item_ret>", "")
            .replace("</item_ret>", "")
            .replace("<item_ret_otr>", "")
            .replace("</item_ret_otr>", "")
        )
        return xml

    def _tpo_dte(self):
        tpo_dte = "Documento"
        if self.sii_document_class_id.sii_code == 43:
            tpo_dte = "Liquidacion"
        return tpo_dte

    def _timbrar(self, n_atencion=None):
        folio = self.get_folio()
        tpo_dte = self._tpo_dte()
        doc_id_number = \
            "F{}T{}".format(folio, self.sii_document_class_id.sii_code)
        doc_id = "<" + tpo_dte + ' ID="{}">'.format(doc_id_number)
        dte = collections.OrderedDict()
        dte[(tpo_dte + " ID")] = self._dte(n_atencion)
        xml = self._dte_to_xml(dte, tpo_dte)
        root = etree.XML(xml)
        xml_pret = (
            etree.tostring(root, pretty_print=True)
            .decode()
            .replace("<" + tpo_dte + "_ID>", doc_id)
            .replace("</" + tpo_dte + "_ID>", "</" + tpo_dte + ">"))
        envelope_efact = self.create_template_doc(xml_pret)
        doc_type = "doc"
        if self._es_boleta():
            doc_type = "bol"
        einvoice = self.sign_full_xml(envelope_efact, doc_id_number, doc_type)
        self.sii_xml_dte = einvoice

    def _crear_envio(self, n_atencion=None, RUTRecep="60803000-K"):
        dicttoxml.set_debug(False)
        clases = {}
        company_id = False
        es_boleta = False
        batch = 0
        for inv in self.with_context(lang="es_CL"):
            if not inv.sii_batch_number or inv.sii_batch_number == 0:
                batch += 1
                # si viene una guía/nota regferenciando una factura, que por
                # numeración viene a continuación de la guia/nota, será
                # recahazada laguía porque debe estar declarada la factura
                # primero
                inv.sii_batch_number = (
                    batch
                )
            if inv.sii_batch_number != 0 and inv._es_boleta():
                if not es_boleta and clases:
                    raise UserError(_(
                        "You cannot do mass mailing with mixed content. "
                        "For this mailing, only electronic ticket, electronic "
                        "exempt ticket or ticket NC (or remove the cases from "
                        "the set)"))
                es_boleta = True
            if (
                inv.company_id.dte_service_provider == "SIICERT"
            ):  # Retimbrar con número de atención y envío
                inv._timbrar(n_atencion)
            # @TODO Mejarorar esto en lo posible
            if inv.sii_document_class_id.sii_code not in clases:
                clases[inv.sii_document_class_id.sii_code] = []
            clases[inv.sii_document_class_id.sii_code].extend(
                [
                    {
                        "id": inv.id,
                        "envio": inv.sii_xml_dte,
                        "sii_batch_number": inv.sii_batch_number,
                        "sii_document_number": inv.sii_document_number,
                    }
                ]
            )
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError(_(
                    "It is combining companies. This is not allowed in a "
                    "shipping."))
        file_name = ""
        dtes = {}
        SubTotDTE = ""
        resol_data = self.get_resolution_data(company_id)
        signature_d = self.env.user.get_digital_signature(company_id)
        RUTEmisor = self.format_vat(company_id.vat)
        for id_class_doc, classes in clases.items():
            NroDte = 0
            for documento in classes:
                if documento["sii_batch_number"] in dtes.keys():
                    raise UserError(_(
                        "You cannot repeat the same order number"))
                dtes.update(
                    {str(documento["sii_batch_number"]): documento["envio"]})
                NroDte += 1
                file_name += (
                    "F"
                    + str(documento["sii_document_number"])
                    + "T"
                    + str(id_class_doc)
                )
            SubTotDTE += (
                "<SubTotDTE>\n<TpoDTE>"
                + str(id_class_doc)
                + "</TpoDTE>\n<NroDTE>"
                + str(NroDte)
                + "</NroDTE>\n</SubTotDTE>\n"
            )
        file_name += ".xml"
        documentos = ""
        for key in sorted(dtes.keys(), key=lambda r: int(r)):
            documentos += "\n" + dtes[key]
        # firma del sobre
        dtes = self.create_template_envio(
            RUTEmisor,
            RUTRecep,
            resol_data["dte_resolution_date"],
            resol_data["dte_resolution_number"],
            self.time_stamp(),
            documentos,
            signature_d,
            SubTotDTE,
        )
        env = "env"
        if es_boleta:
            envio_dte = self.create_template_env_boleta(dtes)
            env = "env_boleta"
        else:
            envio_dte = self.create_template_env(dtes)
        envio_dte = (
            self.env["account.invoice"]
            .sudo(self.env.uid)
            .with_context({"company_id": company_id.id})
            .sign_full_xml(
                envio_dte.replace('<?xml version="1.0"'
                                  ' encoding="ISO-8859-1"?>\n', ""),
                "SetDoc",
                env,
            )
        )
        return {
            "xml_envio": '<?xml version="1.0" encoding="ISO-8859-1"?>\n' +
                         envio_dte,
            "name": file_name,
            "company_id": company_id.id,
            "user_id": self.env.uid,
        }

    @api.multi
    def do_dte_send(self, n_atencion=None):
        if (
            not self[0].sii_xml_request
            or self[0].sii_result in ["Rechazado"]
            or (
                self[0].company_id.dte_service_provider == "SIICERT"
                and self[0].sii_xml_request.state in ["", "NoEnviado"]
            )
        ):
            tipo_envio = {"boleta": [], "normal": []}
            for r in self:
                if r._es_boleta():
                    tipo_envio["boleta"].append(r.id)
                else:
                    tipo_envio["normal"].append(r.id)
                if r.sii_xml_request:
                    r.sii_xml_request.unlink()
                    r.sii_message = ""
            for k, t in tipo_envio.items():
                if not t:
                    continue
                recs = self.browse(t)
                envio = recs._crear_envio(n_atencion, RUTRecep="60803000-K")
                if k in ["boleta"]:
                    envio.update({"state": "Aceptado",
                                  "sii_send_ident": envio["name"]})
                envio_id = self.env["sii.xml.envio"].create(envio)
                for r in recs:
                    r.sii_xml_request = envio_id.id
                    if r._es_boleta():
                        r.sii_result = "Proceso"
                if k in ["factura"]:
                    envio_id.send_xml()
            return envio_id
        self[0].sii_xml_request.send_xml()
        return self[0].sii_xml_request

    def process_response_xml(self, resp):
        if "java" in resp["SII:RESPUESTA"]["SII:RESP_HDR"]:
            return "Proceso"
        if resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] == "2":
            return "Enviado"
        if resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] in [
            "EPR",
            "MMC",
            "DOK",
            "TMC",
        ]:
            return "Proceso"
        elif resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] in ["DNK"]:
            return "Reparo"
        elif resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] in ["FAU", "RCT",
                                                                 "FNA"]:
            return "Rechazado"
        elif resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] in ["FAN", "ANC"]:
            return "Anulado"  # Desde El sii

    @api.onchange("sii_message")
    def get_sii_result(self):
        for r in self:
            try:
                if r.sii_message:
                    r.sii_result = r.process_response_xml(
                        xmltodict.parse(r.sii_message)
                    )
                    continue
                if r.sii_xml_request.state == "NoEnviado":
                    r.sii_result = "EnCola"
                    continue
                r.sii_result = r.sii_xml_request.state
            except Exception as e:
                _logger.warning("No answer to SII MESSAGE: %s" % str(e))

    def _get_dte_status(self):
        for r in self:
            if r.sii_xml_request and r.sii_xml_request.state not in [
                "Aceptado",
                "Rechazado",
            ]:
                continue
            token = r.sii_xml_request.get_token(self.env.user, r.company_id)
            url = server_url[r.company_id.dte_service_provider] +\
                "QueryEstDte.jws?WSDL"
            _server = Client(url)
            receptor = r.format_vat(r.commercial_partner_id.vat)
            date_invoice = \
                datetime.strptime(str(r.date_invoice), "%Y-%m-%d").\
                strftime("%d-%m-%Y")
            signature_d = self.env.user.get_digital_signature(r.company_id)
            rut = signature_d["subject_serial_number"]
            respuesta = _server.service.getEstDte(
                rut[:8].replace("-", ""),
                str(rut[-1]),
                r.company_id.vat[2:-1],
                r.company_id.vat[-1],
                receptor[:8].replace("-", ""),
                receptor[-1],
                str(r.sii_document_class_id.sii_code),
                str(r.sii_document_number),
                date_invoice,
                str(int(r.amount_total)),
                token,
            )
            r.sii_message = respuesta

    @api.multi
    def ask_for_dte_status(self):
        for r in self:
            if not r.sii_xml_request and not r.sii_xml_request.sii_send_ident:
                raise UserError(_(
                    "The document was not sent. It is in the Odoo internal "
                    "message queue envío interna en odoo"))
            if r.sii_xml_request.state not in ["Aceptado", "Rechazado"]:
                r.sii_xml_request.get_send_status(r.env.user)
        if r.sii_xml_request.state in ["Aceptado", "Rechazado"]:
            try:
                self._get_dte_status()
            except Exception as e:
                _logger.warning("Error when obtaining the DTE Status: %s" % str(e))
        self.get_sii_result()

    def set_dte_claim(
        self,
        rut_emisor=False,
        company_id=False,
        sii_document_number=False,
        sii_document_class_id=False,
        claim=False,
    ):
        rut_emisor = \
            rut_emisor or self.format_vat(self.company_id.partner_id.vat)
        company_id = company_id or self.company_id
        sii_document_number = (
            sii_document_number or self.sii_document_number or self.reference
        )
        sii_document_class_id = \
            sii_document_class_id or self.sii_document_class_id
        claim = claim or self.claim
        token = self.sii_xml_request.get_token(self.env.user, self.company_id)
        url = claim_url[company_id.dte_service_provider] + "?wsdl"
        _server = Client(url, headers={"Cookie": "TOKEN=" + token})
        respuesta = _server.service.ingresarAceptacionReclamoDoc(
            rut_emisor[:-2],
            rut_emisor[-1],
            str(sii_document_class_id.sii_code),
            str(sii_document_number),
            claim,
        )
        if self.id:
            self.claim_description = respuesta

    @api.multi
    def get_dte_claim(self,):
        token = self.sii_xml_request.get_token(self.env.user, self.company_id)
        url = claim_url[self.company_id.dte_service_provider] + "?wsdl"
        _server = Client(url, headers={"Cookie": "TOKEN=" + token})
        respuesta = _server.service.listarEventosHistDoc(
            self.company_id.vat[2:-1],
            self.company_id.vat[-1],
            str(self.sii_document_class_id.sii_code),
            str(self.sii_document_number),
        )
        self.claim_description = respuesta

    @api.multi
    def wizard_upload(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sii.dte.upload_xml.wizard",
            "src_model": "account.invoice",
            "view_mode": "form",
            "view_type": "form",
            "views": [(False, "form")],
            "target": "new",
            "tag": "action_upload_xml_wizard",
        }

    @api.multi
    def wizard_validar(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sii.dte.validar.wizard",
            "src_model": "account.invoice",
            "view_mode": "form",
            "view_type": "form",
            "views": [(False, "form")],
            "target": "new",
            "tag": "action_validar_wizard",
        }

    @api.multi
    def invoice_print(self):
        self.ensure_one()
        self.filtered(lambda inv: not inv.sent).write({"sent": True})
        if self.ticket:
            return self.env.ref(
                "l10n_cl_electronic_invoicing.action_print_ticket").\
                report_action(self)
        return super(AccountInvoice, self).invoice_print()

    @api.multi
    def print_cedible(self):
        """ Print Cedible
        """
        return self.env.ref(
            "l10n_cl_electronic_invoicing.action_print_cedible").\
            report_action(self)

    def send_exchange(self):
        att = self._create_attachment()
        body = "XML de Intercambio DTE: %s" % (self.document_number)
        subject = "XML de Intercambio DTE: %s" % (self.document_number)
        self.sudo().message_post(
            body=body,
            subject=subject,
            partner_ids=[self.commercial_partner_id.id],
            attachment_ids=att.ids,
            message_type="comment",
            subtype="mt_comment",
        )
        if not self.commercial_partner_id.dte_email:
            return False
        if self.commercial_partner_id.dte_email in [
            "facturacionmipyme2@sii.cl",
            "facturacionmipyme@sii.cl",
        ]:
            return False
        values = {
            "email_from": self.company_id.dte_email,
            "email_to": self.commercial_partner_id.dte_email,
            "auto_delete": False,
            "model": "account.invoice",
            "body": body,
            "subject": subject,
            "attachment_ids": [[6, 0, att.ids]],
        }
        send_mail = self.env["mail.mail"].sudo().create(values)
        send_mail.send()

    @api.multi
    def manual_send_exchange(self):
        self.send_exchange()

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        if self.sii_document_class_id:
            string_state = ""
            if self.state == "draft":
                string_state = "en borrador "
            report_string = "%s %s %s" % (
                self.sii_document_class_id.name,
                string_state,
                self.sii_document_number or "",
            )
        else:
            report_string = super(AccountInvoice, self).\
                _get_printed_report_name()
        return report_string

    @api.multi
    def getTotalDiscount(self):
        total_discount = 0
        for l in self.invoice_line_ids:
            if not l.account_id:
                continue
            total_discount += \
                ((l.discount or 0.00) / 100) * l.price_unit * l.quantity
        return self.currency_id.round(total_discount)
