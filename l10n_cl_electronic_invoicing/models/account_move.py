# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends(
        "sii_document_number",
        "name",
        "document_class_id",
        "document_class_id.doc_code_prefix",
    )
    def _compute_document_number(self):
        for r in self:
            if r.sii_document_number and r.document_class_id:
                document_number = (
                    r.document_class_id.doc_code_prefix or ""
                ) + r.sii_document_number
            else:
                document_number = r.name
            r.document_number = document_number

    document_class_id = fields.Many2one(
        "sii.document.class",
        string="Document Type",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]})
    sii_document_number = fields.Char(
        string="SII Document Number",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]})
    canceled = fields.Boolean(
        string="Cancelled?", readonly=True,
        states={"draft": [("readonly", False)]})
    iva_uso_comun = fields.Boolean(
        string="Iva Uso Común", readonly=True,
        states={"draft": [("readonly", False)]})
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
        compute="_compute_document_number",
        string="Document Number",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]})
    sended = fields.Boolean(
        string="Enviado al SII",
        default=False,
        readonly=True,
        states={"draft": [("readonly", False)]})
    factor_proporcionalidad = fields.Float(
        string="Factor proporcionalidad",
        default=0.00,
        readonly=True,
        states={"draft": [("readonly", False)]})

    def _get_move_imps(self):
        imps = {}
        for l in self.line_ids:
            if l.tax_line_id:
                if l.tax_line_id:
                    if l.tax_line_id.id not in imps:
                        imps[l.tax_line_id.id] = {
                            "tax_id": l.tax_line_id.id,
                            "credit": 0,
                            "debit": 0,
                            "code": l.tax_line_id.sii_code,
                        }
                    imps[l.tax_line_id.id]["credit"] += l.credit
                    imps[l.tax_line_id.id]["debit"] += l.debit
            elif l.tax_ids and l.tax_ids[0].amount == 0:  # caso monto exento
                if not l.tax_ids[0].id in imps:
                    imps[l.tax_ids[0].id] = {
                        "tax_id": l.tax_ids[0].id,
                        "credit": 0,
                        "debit": 0,
                        "code": l.tax_ids[0].sii_code,
                    }
                imps[l.tax_ids[0].id]["credit"] += l.credit
                imps[l.tax_ids[0].id]["debit"] += l.debit
        return imps

    def totales_por_movimiento(self):
        move_imps = self._get_move_imps()
        imps = {"iva": 0, "exento": 0, "otros_imps": 0}
        for key, i in move_imps.items():
            if i["code"] in [14]:
                imps["iva"] += i["credit"] or i["debit"]
            elif i["code"] == 0:
                imps["exento"] += i["credit"] or i["debit"]
            else:
                imps["otros_imps"] += i["credit"] or i["debit"]
        imps["neto"] = \
            self.amount - imps["otros_imps"] - imps["exento"] - imps["iva"]
        return imps
