# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class EtdDocument(models.Model):
    _inherit = "etd.document"

    model = fields.Selection(
        selection_add=[("fsm.route.dayroute", "Day Route")])

    # For cron generated runs, dayroutes are ignored
    # Documents related to a dayroute won't be included
    # For per dayrout runs, only documents related to the dayroute
    # are included

    @api.model
    def _xerox_get_domain_invoice(self, run_date=None, force=False,
                                  dayroutes=None):
        domain = super()._xerox_get_domain_invoice(run_date, force)
        if dayroutes:
            fsm_orders = dayroutes.mapped('order_ids')
            domain.append(('fsm_order_ids', 'in', fsm_orders.ids))
        else:
            domain.append(('fsm_order_ids', '=', False))
        return domain

    @api.model
    def _xerox_get_domain_picking(self, run_date=None, force=False,
                                  picking_type="outgoing", dayroutes=None):
        domain = super()._xerox_get_domain_picking(
            run_date=run_date, force=force, picking_type=picking_type)
        if dayroutes:
            fsm_orders = dayroutes.mapped('order_ids')
            domain.append(('fsm_order_id', 'in', fsm_orders.ids))
        else:
            domain.append(('fsm_order_id', '=', False))
        return domain

    @api.model
    def _xerox_get_domain_picking_batch(self, run_date=None, force=False,
                                        dayroutes=None):
        # TODO: properly exclude DayRoute picking batches from cron runs
        domain = super()._xerox_get_domain_picking_batch(run_date, force)
        domain = [('id', '=', 0)]  # Always False
        return domain
