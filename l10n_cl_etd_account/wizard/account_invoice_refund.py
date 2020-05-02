# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountInvoiceRefund(models.TransientModel):
    _inherit = 'account.invoice.refund'

    @api.multi
    def compute_refund(self, mode='refund'):
        res = super().compute_refund(mode)
        if mode == 'modify':
            inv_obj = self.env['account.invoice']
            context = dict(self._context or {})
            for invoice in inv_obj.browse(context.get('active_ids')):
                # Get the doc of the refund
                sii_doc = invoice.get_reverse_sii_document()
                # Get the code of the refund of the refund
                sii_code = invoice.get_reverse_sii_code(code=sii_doc.code)
                # Get the doc of the refund of the refund
                sii_doc = self.env['sii.document.class'].search([
                    ('code', '=', sii_code)], limit=1)
                # Get the new document...
                new_inv = inv_obj.browse(res['res_id'])
                # ...to update its document class
                new_inv.class_id = sii_doc.id
        return res
