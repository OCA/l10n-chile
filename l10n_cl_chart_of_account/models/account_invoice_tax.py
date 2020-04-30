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
                    price_tax_included += line.price_total
            if price_tax_included > 0 and \
                    tax.tax_id.sii_type in ["R"] and tax.tax_id.amount > 0:
                base = currency.round(price_tax_included)
            elif price_tax_included > 0 and tax.tax_id.amount > 0:
                base = currency.round(price_tax_included /
                                      (1 + tax.tax_id.amount / 100.0))
            net += base
        return net
