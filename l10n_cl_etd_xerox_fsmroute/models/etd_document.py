# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EtdDocument(models.Model):
    _inherit = "etd.document"

    model = fields.Selection(
        selection_add=[("fsm.route.dayroute", "Day Route")])

    def _xerox_get_domain_invoice(self, run_date, classes):
        # Only invoices at run date without a DayRoute assigned
        res = super()._xerox_get_domain_invoice(run_date, classes)
        res.append(('fsm_order_ids', '=', False))
        return res

    def _xerox_get_domain_picking(self, run_date, classes):
        # Only pickings at run date without a DayRoute assigned
        res = super()._xerox_get_domain_picking(run_date, classes)
        res.append(('fsm_order_id', '=', False))
        return res

    def _xerox_get_records(self, company_id, run_date):
        res = super()._xerox_get_records(company_id, run_date)
        rec0 = list(res.values())[0]
        now = rec0.env.context['context_now']
        Dayroute = self.env["fsm.route.dayroute"].with_context(context_now=now)
        dayroutes = Dayroute.search([("date", "=", run_date)])
        res['fsm.route.dayroute'] = dayroutes
        # Include Invoices and Pickings linked to the DayRoute
        # regardless of their document date
        res['account.invoice'] |= (
            dayroutes
            .mapped('order_ids.invoice_ids')
            .filtered('class_id')
            .filtered(lambda inv: inv.status in ["open", "paid"])
        )
        res['stock.picking'] |= (
            dayroutes
            .mapped('order_ids.picking_ids')
            .filtered('class_id')
            .filtered(lambda pick: pick.picking_type_id.code == 'outgoing')
            .filtered(lambda pick: pick.state not in ("draft", "cancel"))
        )
        return res
