# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import date_utils


class EtdDocument(models.Model):
    _inherit = "etd.document"

    model = fields.Selection(
        selection_add=[("fsm.route.dayroute", "Day Route")])

    def _xerox_get_records(self, company_id, run_date):

        res = super()._xerox_get_records(company_id, run_date)
        next_date = date_utils.add(run_date, days=1)
        res['fsm.route.dayroute'] = self.env["fsm.route.dayroute"].search([
            ("stage_id.is_closed", "=", "True"),
            ("date_close", ">=", run_date),
            ("date_close", "<", next_date),
        ])
        return res
