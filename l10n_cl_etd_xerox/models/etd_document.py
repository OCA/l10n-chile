# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import date
import logging
from odoo import api, fields, models
from odoo.tools import date_utils


_logger = logging.getLogger(__name__)


class EtdDocument(models.Model):
    _inherit = "etd.document"

    def _xerox_get_records(self, company_id, run_date):
        """Find and returns all documents."""
        next_date = date_utils.add(run_date, days=1)
        class_ids = self.env["sii.document.class"].search([
            ("dte", "=", True)
        ]).ids
        recs = {}
        recs['account.invoice'] = self.env["account.invoice"].search([
            ("date_invoice", "=", run_date),
            ("state", "in", ["open", "paid"]),
            ("class_id", "in", class_ids)
        ])
        recs['stock.picking'] = self.env["stock.picking"].search([
            ("picking_type_code", "=", "outgoing"),
            ("state", "=", "done"),
            ("date_done", ">=", run_date),
            ("date_done", "<=", next_date),
            ("class_id", "in", class_ids)
        ])
        return recs

    @api.model
    def cron_xerox_send_files(self, run_date=None):
        """
        Run Cron Scheduler action.
        Accepts an optional run date,
        that can be either a Date object or a string.
        This can be used to manually run tests for a particualr day.
        """
        if not run_date:
            # Use yesterday
            today = fields.Date.context_today(self)
            run_date = date_utils.add(today, days=-1)
        elif not isinstance(run_date, date):
            # Convert t Date object
            run_date = fields.Date.to_date(run_date)

        companies = self.env["res.company"].search(
            [
                ("backend_acp_id", "!=", False),
                ("backend_acp_id.status", "=", 'confirmed'),
                ("backend_acp_id.send_immediately", "=", False),
            ]
        )
        if not companies:
            _logger.info('No Company is configured for Xerox integration')

        for company in companies:
            ungrouped_rsets = self._xerox_get_records(company, run_date)
            doc_count = sum(len(x) for x in ungrouped_rsets.values())
            _logger.info(
                'Found %d documents for company %s', doc_count, company.name)
            # Group records by file set, using rule in `xerox_group()`
            grouped_data = {}
            for rset in ungrouped_rsets.values():
                # In place update of the grouped data dict
                grouped_data = rset.xerox_group(grouped_data)

            file_dict = {}
            for key, records in grouped_data.items():
                for record in records:
                    # FIXME: run .with_delay. Implies some code reorg
                    file_dict = record.build_files(file_dict)
            company.backend_acp_id.send(file_dict)
