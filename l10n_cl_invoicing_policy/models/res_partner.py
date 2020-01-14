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
        if self.company_type == 'company':
            return 'invoice'
        return 'ticket'

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

    @api.constrains('is_company', 'invoicing_policy')
    def check_invoicing_policy(self):
        if self.invoicing_policy == 'ticket':
            if self.is_company:
                raise UserError(_('The invoicing policy Ticket only applies '
                                  'to individuals.'))
        else:
            if not self.is_company:
                raise UserError(_('The selected invoicing policy only applies'
                                  ' to companies.'))

    @api.onchange('is_company')
    def onchange_invoicing_policy(self):
        self.invoicing_policy = self._default_invoicing_policy()
