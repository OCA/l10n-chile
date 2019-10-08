# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.depends(
        "price_unit",
        "discount",
        "invoice_line_tax_ids",
        "quantity",
        "product_id",
        "invoice_id.partner_id",
        "invoice_id.currency_id",
        "invoice_id.company_id",
    )
    def _compute_price(self):
        for line in self:
            currency = line.invoice_id and line.invoice_id.currency_id or None
            taxes = False
            total = 0
            if line.invoice_line_tax_ids:
                taxes = line.invoice_line_tax_ids.compute_all(
                    line.price_unit,
                    currency,
                    line.quantity,
                    product=line.product_id,
                    partner=line.invoice_id.partner_id,
                    discount=line.discount,
                )
            if taxes:
                line.price_subtotal = price_subtotal_signed = \
                    taxes["total_excluded"]
            else:
                total = \
                    line.currency_id.round((line.quantity * line.price_unit))
                total_discount = line.currency_id.round(
                    (total * ((line.discount or 0.0) / 100.0))
                )
                total -= total_discount
                line.price_subtotal = price_subtotal_signed = total
            if (line.invoice_id.currency_id and
                    line.invoice_id.currency_id !=
                    line.invoice_id.company_id.currency_id):
                price_subtotal_signed = line.invoice_id.currency_id.\
                    with_context(date=line.invoice_id.
                                 _get_currency_rate_date()).\
                    compute(price_subtotal_signed,
                            line.invoice_id.company_id.currency_id)
            sign = line.invoice_id.type in ["in_refund", "out_refund"] \
                and -1 or 1
            line.price_subtotal_signed = price_subtotal_signed * sign
            line.price_tax_included = (
                taxes["total_included"]
                if (taxes and taxes["total_included"] > total)
                else total
            )
            line.price_total = (
                taxes["total_included"]
                if (taxes and taxes["total_included"] > total)
                else total
            )

    # TODO: eliminar este campo en versiones futuras
    # odoo en V11 ya agrega un campo para guardar el precio incluido impuestos
    # este campo es innecesario a partir de V11
    price_tax_included = fields.Monetary(
        string="Amount", readonly=True, compute="_compute_price")
