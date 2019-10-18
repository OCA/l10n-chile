# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GlobalDescuentoRecargo(models.Model):
    _name = "account.invoice.gdr"
    _description = "Account Invoice GDR"

    type = fields.Selection(
        [("D", "Descuento"), ("R", "Recargo")],
        string="Seleccione Descuento/Recargo Global",
        default="D",
        required=True)
    valor = fields.Float(string="Value", default=0.00,
                         required=True)
    gdr_type = fields.Selection(
        [("amount", "Amount"), ("percent", "Percentage")],
        string="Discount Type",
        default="percent",
        required=True)
    gdr_dtail = fields.Char(string="Discount Reason")
    amount_untaxed_global_dr = fields.Float(
        string="Descuento/Recargo Global", default=0.00,
        compute="_compute_untaxed_gdr")
    aplicacion = fields.Selection(
        [("flete", "Flete"), ("seguro", "Seguro")],
        string="Discount Application")
    invoice_id = fields.Many2one("account.invoice", string="Invoice")

    def _get_afecto(self):
        afecto = 0.00
        for line in self[0].invoice_id.invoice_line_ids:
            for tl in line.invoice_line_tax_ids:
                if tl.amount > 0:
                    afecto += line.price_subtotal
        return afecto

    @api.depends("gdr_type", "valor", "type")
    def _compute_untaxed_gdr(self):
        afecto = self._get_afecto()
        des = 0
        rec = 0
        for gdr in self:
            dr = gdr.valor
            if gdr.gdr_type in ["percent"]:
                if afecto == 0.00:
                    continue
                # exento = 0 #@TODO Descuento Global para exentos
                if afecto > 0:
                    dr = gdr.invoice_id.currency_id.round(
                        (afecto * (dr / 100.0)))
            if gdr.type == "D":
                des += dr
            else:
                rec += dr
            gdr.amount_untaxed_global_dr = dr

    def get_agrupados(self):
        result = {"D": 0.00, "R": 0.00}
        for gdr in self:
            result[gdr.type] += gdr.amount_untaxed_global_dr
        return result

    def get_monto_aplicar(self):
        grouped = self.get_agrupados()
        monto = 0
        for key, value in grouped.items():
            valor = value
            if key == "D":
                valor = float(value) * (-1)
            monto += valor
        return monto

    @api.model
    def default_get(self, fields_list):
        ctx = self.env.context.copy()
        # FIX: la accion de Notas de credito pasa por contexto default_type:
        # 'out_refund' pero al existir en esta clase de descuentos un campo
        # llamado type el ORM lo interpreta como un valor para ese campo,
        # pero el valor no esta dentro de las opciones del selection, por ello
        # sale error asi que si no esta en los valores soportados, eliminarlo
        # del contexto
        if "default_type" in ctx and ctx.get("default_type") not in ("D", "R"):
            ctx.pop("default_type")
        return super(GlobalDescuentoRecargo, self.with_context(ctx)).\
            default_get(fields_list)
