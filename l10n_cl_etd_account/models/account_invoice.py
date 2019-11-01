# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'etd.mixin']

    def get_etd_document(self):
        res = super().get_etd_document()
        res = res.filtered(
            lambda x:
            x.name.lower() == self.partner_id.invoicing_policy.lower())
        return res

    @api.multi
    def invoice_validate(self):
        res = super().invoice_validate()
        sign = self._name in [x.model for x in self.company_id.etd_ids]
        for invoice in self:
            if sign and invoice.type in ('out_invoice', 'out_refund'):
                self.with_delay().document_sign()
        return res
