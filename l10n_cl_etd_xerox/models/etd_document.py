# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import date
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils


_logger = logging.getLogger(__name__)


class EtdDocument(models.Model):
    _inherit = "etd.document"

    @api.model
    def _xerox_get_domain_invoice(self, run_date):
        return [
            ("date_invoice", "=", run_date),
            ("state", "in", ["open", "paid"]),
            ("class_id.dte", "=", True),
        ]

    @api.model
    def _xerox_get_domain_picking(self, run_date):
        run_date1 = date_utils.add(run_date, days=1)
        return [
            ("picking_type_code", "=", "outgoing"),
            # Deliveries are signed once they are waiting or confirmed
            # They will ony be "done" when delivered at customer site
            ("state", "not in", ("draft", "cancel")),
            ("scheduled_date", ">=", run_date),
            ("scheduled_date", "<", run_date1),
            ("class_id.dte", "=", True),
        ]

    @api.model
    def _xerox_get_domain_picking_batch(self, run_date):
        return [
            ("date", "=", run_date),
            ("class_id.dte", "=", True),
            ('picking_ids', '!=', False),
        ]

    @api.model
    def _xerox_get_records_day(self, company_id, run_date):
        """Find and returns all documents."""
        now = fields.Datetime.context_timestamp(
            self.env.user,
            fields.Datetime.now())
        recs = {}
        Invoice = self.env["account.invoice"].with_context(context_now=now)
        recs['account.invoice'] = Invoice.search(
            self._xerox_get_domain_invoice(run_date))
        Picking = self.env["stock.picking"].with_context(context_now=now)
        recs['stock.picking'] = Picking.search(
            self._xerox_get_domain_picking(run_date))
        Batch = self.env["stock.picking.batch"].with_context(context_now=now)
        recs['stock.picking.batch'] = Batch.search(
            self._xerox_get_domain_picking_batch(run_date))
        return recs

    @api.model
    def xerox_build_files(self, rsets):
        """
        Given a dict with the document recorsets,
        builds a dict with the file name an content
        """
        doc_count = sum(len(x) for x in rsets.values())
        _logger.info(
            'Building files for %d documents', doc_count)
        for model, rset in rsets.items():
            _logger.info('- %s: %s' % (model, rset.mapped('display_name')))
        # Group records by file set, using rule in `xerox_group()`
        grouped_data = {}
        for rset in rsets.values():
            # In place update of the grouped data dict
            grouped_data = rset.xerox_group(grouped_data)

        file_dict = {}
        for key, records in grouped_data.items():
            for record in records:
                file_dict = record.build_files(file_dict)
        return file_dict

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
            # Convert to Date object
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
            rsets = self._xerox_get_records_day(company, run_date)
            file_dict = self.xerox_build_files(rsets)
            company.backend_acp_id.send(file_dict)
