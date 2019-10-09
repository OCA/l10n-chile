# Copyright (c) 2018 Konos
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    amount_retention = fields.Monetary(string="Retention", default=0.00)
    retention_account_id = fields.Many2one(
        'account.account', string='Retention Account',
        domain=[('deprecated', '=', False)])

    def _getNet(self, currency):
        net = 0
        for tax in self:
            base = tax.base
            price_tax_included = 0
            for line in tax.invoice_id.invoice_line_ids:
                if tax.tax_id in line.invoice_line_tax_ids and \
                        tax.tax_id.price_include:
                    price_tax_included += line.price_tax_included
            if price_tax_included > 0 and \
                    tax.tax_id.sii_type in ["R"] and tax.tax_id.amount > 0:
                base = currency.round(price_tax_included)
            elif price_tax_included > 0 and tax.tax_id.amount > 0:
                base = currency.round(price_tax_included /
                                      (1 + tax.tax_id.amount / 100.0))
            net += base
        return net


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _compute_amount(self):
        # TODO: Search for a better way to apply the retention
        for inv in self:
            amount_retention = 0
            neto = 0
            amount_tax = 0
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
                    line.price_subtotal for line in inv.invoice_line_ids)
            inv.amount_untaxed = neto
            inv.amount_tax = amount_tax
            inv.amount_total = \
                inv.amount_untaxed + inv.amount_tax - amount_retention
            amount_total_company_signed = inv.amount_total
            amount_untaxed_signed = inv.amount_untaxed
            if inv.currency_id and \
                    inv.currency_id != inv.company_id.currency_id:
                currency_id = inv.currency_id.with_context(
                    date=inv.date_invoice)
                amount_total_company_signed = \
                    currency_id.compute(inv.amount_total,
                                        inv.company_id.currency_id)
                amount_untaxed_signed = \
                    inv.currency_id.compute(inv.amount_untaxed,
                                            inv.company_id.currency_id)
            sign = inv.type in ['in_refund', 'out_refund'] and -1 or 1
            inv.amount_total_company_signed = \
                amount_total_company_signed * sign
            inv.amount_total_signed = inv.amount_total * sign
            inv.amount_untaxed_signed = amount_untaxed_signed * sign

    amount_retention = fields.Monetary(string="Retention", default=0.00,
                                       compute='_compute_amount')
