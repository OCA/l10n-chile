# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import date_utils


class EtdDocument(models.Model):
    _inherit = "etd.document"

    model = fields.Selection(
        selection_add=[("fsm.route.dayroute", "Day Route")])

    def _xerox_get_records(self, company_id, run_date):

        def _is_in_dayroute(rec):
            """Check if doc is included in a Day Route"""
            if rec._name == 'account.invoice':
                return bool(rec.fsm_order_ids.dayroute_id)
            if rec._name == 'stock.picking':
                return bool(rec.fsm_order_id.dayroute_id)
            return False

        def _filter_out_dayroute(rset):
            """Filter out docs already included in a Day Route"""
            return rset.filtered(lambda x: not _is_in_dayroute(x))

        res = super()._xerox_get_records(company_id, run_date)
        res = {key: _filter_out_dayroute(rset) for key, rset in res.items()}

        next_date = date_utils.add(run_date, days=1)
        res['fsm.route.dayroute'] = self.env["fsm.route.dayroute"].search([
            ("stage_id.is_closed", "=", "True"),
            ("date_close", ">=", run_date),
            ("date_close", "<", next_date),
        ])
        return res
