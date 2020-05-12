# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class EtdDocument(models.Model):
    _inherit = "etd.document"

    model = fields.Selection(
        selection_add=[("fsm.route.dayroute", "Day Route")])

    @api.model
    def _xerox_get_domain_invoice(self, run_date=None, force=False):
        # Only invoices at run date without a DayRoute assigned
        res = super()._xerox_get_domain_invoice(run_date, force)
        res.append(('fsm_order_ids', '=', False))
        return res

    @api.model
    def _xerox_get_domain_picking(self, run_date=None, force=False):
        # Only pickings at run date without a DayRoute assigned
        res = super()._xerox_get_domain_picking(run_date, force)
        res.append(('fsm_order_id', '=', False))
        return res

    @api.model
    def _xerox_get_domain_dayroute(self, run_date=None, force=False):
        domain = []
        if run_date:
            domain.append(("date", "=", run_date))
        if not force:
            domain.append(("xerox_send_timestamp", "=", False))
        return domain

    @api.model
    def _xerox_add_records_dayroute(self, dayroutes, rsets=None):
        """
        Given Day Routes and dictionary with recordsets,
        adds the Day Routes and corresponding documents to the recorsets dict.
        """
        rsets = rsets or {}
        rsets['fsm.route.dayroute'] = dayroutes
        # Include Invoices and Pickings linked to the DayRoute
        # regardless of their document date
        rsets.setdefault('account.invoice', self.env['account.invoice'])
        rsets['account.invoice'] |= (
            dayroutes
            .mapped('order_ids.invoice_ids')
            .filtered('class_id')
            .filtered(lambda inv: inv.state in ["open", "paid"])
        )
        rsets.setdefault('stock.picking', self.env['stock.picking'])
        rsets['stock.picking'] |= (
            dayroutes
            .mapped('order_ids.picking_ids')
            .filtered('class_id')
            .filtered(lambda pick: pick.picking_type_id.code == 'outgoing')
            .filtered(lambda pick: pick.state not in ("draft", "cancel"))
        )
        return rsets

    @api.model
    def _xerox_get_records_day(self, company, run_date=None, force=None):
        res = super()._xerox_get_records_day(company, run_date, force)
        Dayroute = self.env["fsm.route.dayroute"]
        dayroutes = Dayroute.search(
            self._xerox_get_domain_dayroute(run_date, force))
        res = self._xerox_add_records_dayroute(dayroutes, res)
        return res
