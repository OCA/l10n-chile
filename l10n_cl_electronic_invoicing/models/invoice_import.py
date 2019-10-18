# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import io
import logging
from datetime import datetime
from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)
try:
    import csv
except ImportError:
    _logger.debug("Cannot `import csv`.")
try:
    import base64
except ImportError:
    _logger.debug("Cannot `import base64`.")


class AccountAccountInvoiceWizard(models.TransientModel):
    _name = "account.invoice.import.wizard"
    _description = "Account Invoice Import Wizard"

    file = fields.Binary("File")
    file_opt = fields.Selection([("excel", "Excel"),
                                 ("csv", "CSV")], default="csv")
    invoice_opt = fields.Selection([("compra", "Compra"),
                                    ("venta", "Venta")])

    @api.multi
    def import_file(self):
        if self.file_opt == "csv":
            # Tipo Docto. RUT Contraparte Folio   Fecha Docto. Monto Exento
            # Monto Neto  Tasa Impuesto   Monto IVA Recuperable   Monto Total
            # keys = ['Cant', 'tipo_doc', 'vat', 'partner', 'memo', 'amount',
            # 'currency']
            keys = [
                "cant",
                "tipo_doc",
                "vat",
                "folio",
                "fecha",
                "monto_exento",
                "monto_neto",
                "tasa_impuesto",
                "iva_recuperable",
                "monto_total",
                "anulado",
                "iva_retenido_total",
                "iva_retenido_parcial",
                "iva_no_retenido",
                "iva_propio",
                "16",
                "17",
                "18",
                "19",
                "20",
                "21",
                "22",
                "23",
                "24",
                "25",
                "26",
                "27",
                "28",
                "29",
                "30",
                "31",
                "32",
                "33",
                "34",
                "35",
                "36",
                "37",
                "38",
                "39",
                "40",
                "41",
                "42",
                "43",
                "44",
                "45",
                "tipo_impuesto",
                "nombre",
                "48",
                "49",
                "50",
                "51",
                "52",
            ]
            data = base64.b64decode(self.file)
            file_input = io.StringIO(data.decode("latin-1"))
            file_input.seek(0)
            reader_info = []
            reader = csv.reader(file_input, delimiter=";")
            try:
                reader_info.extend(reader)
            except Exception:
                raise exceptions.Warning(_("Not a valid file!"))
            values = {}
            for i in range(len(reader_info)):
                field = list(map(str, reader_info[i]))
                values = dict(zip(keys, field))
                if values:
                    if i <= 8:
                        continue
                    else:
                        res = self._create_invoice(values)
        return res

    #
    @api.multi
    def _create_invoice(self, val):
        # Reviso Que exista
        partner_id = self._find_partner(val.get("vat"))

        # Si no lo creo
        if not partner_id:
            data = {
                "name": val.get("nombre"),
                "vat": self.format_rut(val.get("vat")),
                "document_type_id":
                    self.env.ref("l10n_cl_electronic_invoicing.dt_RUT").id,
                "responsability_id":
                    self.env.ref("l10n_cl_electronic_invoicing.res_IVARI").id,
                "document_number": val.get("vat"),
                "company_type": "company",
            }
            partner_id = self._create_partner(data)

        # Tipo de Factura
        tipo_factura = "in_invoice"
        if self.invoice_opt == "venta":
            tipo_factura = "out_invoice"
        if val.get("tipo_doc") in ["54", "61"]:
            tipo_factura = "in_refund"
        if self.invoice_opt == "venta":
            tipo_factura = "out_refund"

        # Revisar si Factura Existe
        self.env["account.invoice"].search([
            ("reference", "=", val.get("folio")),
            ("sii_document_class_id.sii_code", "=", val.get("tipo_doc")),
            ("partner_id.vat", "=", self.format_rut(val.get("vat")))])

        # Creo Instancia de Factura y líneas
        invoice_obj = self.env["account.invoice"]
        invoice_line_obj = self.env["account.invoice.line"]

        # TipoDTE 33
        # Busca el Diario que contiene este Doc
        journal_document_class_id = self._get_journal(val.get("tipo_doc"))

        # Datos de la factura
        curr_invoice = {
            "origin": "Carga Inicial: "
            + self.invoice_opt
            + " "
            + datetime.strptime(val.get("fecha"), "%d-%m-%Y").strftime("%m-%Y")
            + " "
            + val.get("cant"),
            "reference": val.get("folio"),
            "partner_id": partner_id,
            "state": "draft",
            "date_invoice":
                datetime.strptime(val.get("fecha"),
                                  "%d-%m-%Y").strftime("%Y-%m-%d"),
            "journal_id": journal_document_class_id.journal_id.id,
            "sii_document_class_id":
                journal_document_class_id.sii_document_class_id.id,
            "journal_document_class_id": journal_document_class_id.id,
            "type": tipo_factura,
        }

        # Crea Factura
        inv_ids = invoice_obj.create(curr_invoice)

        # Busco Producto Afecto Genérico
        query = [("default_code", "=", "PRODUCTO_AFECTO")]
        product_id = self.env["product.product"].search(query)

        # Primera Cuenta Contable que aparezca
        invoice_line_account = (
            self.env["account.account"].search([
                ("user_type_id", "=",
                 self.env.ref("account.data_account_type_expenses").id)],
                limit=1).id)

        # Monto Exento
        IndExe = val.get("monto_exento")
        IndAfec = val.get("monto_neto")

        # Si tiene exento
        if IndExe > "0":
            amount = 0
            sii_code = 0
            sii_type = False
            imp = self._buscar_impuesto(
                amount=amount, sii_code=sii_code, sii_type=sii_type,
                IndExe=True)

            # Datos de líneas de factura
            linea = {
                "product_id": product_id.id,
                "account_id": invoice_line_account,
                "name": "Producto Exento",
                "price_unit": IndExe,
                "quantity": 1.0,
                "invoice_id": inv_ids.id,
                "price_subtotal": IndExe,
                "invoice_line_tax_ids": [(6, 0, imp.ids)]}
            invoice_line_obj.create(linea)

        # Si tiene afecto entonces buscamos el impuesto
        if IndAfec > "0":
            amount = 19
            sii_code = 14
            sii_type = False
            imp = self._buscar_impuesto(
                amount=amount, sii_code=sii_code, sii_type=sii_type,
                IndExe=False)
            # Datos de líneas de factura
            linea = {
                "product_id": product_id.id,
                "account_id": invoice_line_account,
                "name": "Producto Afecto",
                "price_unit": IndAfec,
                "quantity": 1.0,
                "invoice_id": inv_ids.id,
                "price_subtotal": IndAfec,
                "invoice_line_tax_ids": [(6, 0, imp.ids)],
            }
            invoice_line_obj.create(linea)
        inv_ids.compute_taxes()
        return True

    def _find_partner(self, rut):
        partner_id = self.env["res.partner"].search(
            [
                ("active", "=", True),
                ("parent_id", "=", False),
                ("vat", "=", self.format_rut(rut)),
            ]
        )
        if partner_id:
            return partner_id.id
        else:
            return

    def format_rut(self, RUTEmisor=None):
        rut = RUTEmisor.replace("-", "")
        if int(rut[:-1]) < 10000000:
            rut = "0" + str(int(rut))
        rut = "CL" + rut
        return rut

    def _get_journal(self, sii_code):
        operation_type = "purchase"
        if self.invoice_opt == "ventas":
            operation_type = "sale"
        return self.env["account.journal.sii.document.class"].search([
            ("sii_document_class_id.sii_code", "=", sii_code),
            ("journal_id.type", "=", operation_type)], limit=1)

    def _create_partner(self, data):
        partner_id = self.env["res.partner"].create(data)
        if partner_id:
            return partner_id.id
        else:
            return

    def _buscar_impuesto(
        self, name="Impuesto", amount=0, sii_code=0, sii_type=False,
            IndExe=False):
        query = [
            ("amount", "=", amount),
            ("sii_code", "=", sii_code),
            (
                "type_tax_use",
                "=",
                ("purchase" if self.invoice_opt == "compra" else "sale"),
            ),
            ("activo_fijo", "=", False),
        ]
        if IndExe:
            query.append(("sii_type", "=", False))
        if amount == 0 and sii_code == 0 and not IndExe:
            query.append(("name", "=", name))
        if sii_type:
            query.extend([("sii_type", "=", sii_type)])
        imp = self.env["account.tax"].search(query, limit=1)
        if not imp:
            imp = (
                self.env["account.tax"]
                .sudo()
                .create(
                    {
                        "amount": amount,
                        "name": name,
                        "sii_code": sii_code,
                        "sii_type": sii_type,
                        "type_tax_use": "purchase",
                    }
                )
            )
        return imp
