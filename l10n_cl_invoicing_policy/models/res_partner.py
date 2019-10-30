# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _default_invoicing_policy(self):
        res = 'ticket'
        if self.company_type == 'company':
            res = 'invoice'
        return res

    invoicing_policy = fields.Selection(
        (("ticket", "Ticket"),
         ("invoice", "Invoice"),
         ("eguide", "Electronic Guide")),
        string="Invoicing Policy", required=True,
        default=_default_invoicing_policy,
        help="""
        * Ticket: Only for individuals. 1 invoice for each delivery order.
        * Invoice: Only for companies. The VAT is required. 1 invoice for each
          delivery order. Requires the customer PO # on the SO/Invoice.
        * Electronic Guide: Only for companies. 1 invoice at the end of the
          month for all the delivery orders of that month.""")

    def check_invoicing_policy(self, policy, rec_type):
        if policy == 'ticket':
            if rec_type != 'person':
                raise UserError(_('The invoicing policy Ticket only applies '
                                  'to individuals.'))
        else:
            if rec_type != 'company':
                raise UserError(_('The selected invoicing policy only applies'
                                  ' to companies.'))

    @api.model
    def create(self, vals):
        self.check_invoicing_policy(vals['invoicing_policy'], vals['company_type'])
        return super().create(vals)

    @api.multi
    def write(self, vals):
        self.check_invoicing_policy(
            'invoicing_policy' in vals and vals['invoicing_policy'] or
            self.invoicing_policy,
            'company_type' in vals and vals['company_type'] or
            self.company_type)
        return super().write(vals)
