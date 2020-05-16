# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import date
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import date_utils


_logger = logging.getLogger(__name__)


class EtdDocument(models.Model):
    _inherit = "etd.document"

    @api.model
    def _xerox_get_domain_invoice(self, run_date=None, force=False):
        domain = [
            ("state", "in", ["open", "paid"]),
            ("class_id.dte", "=", True),
        ]
        if run_date:
            domain.append(("date_invoice", "=", run_date))
        if not force:
            domain.append(("xerox_send_timestamp", "=", False))
        return domain

    @api.model
    def _xerox_get_domain_picking(self, run_date=None, force=False,
                                  picking_type="outgoing"):
        domain = [
            ("picking_type_code", "=", picking_type),
            # Deliveries are signed once they are waiting or confirmed
            # They will ony be "done" when delivered at customer site
            ("state", "not in", ("draft", "cancel")),
            ("class_id.dte", "=", True),
        ]
        if run_date:
            run_date1 = date_utils.add(run_date, days=1)
            domain.extend([
                ("scheduled_date", ">=", run_date),
                ("scheduled_date", "<", run_date1),
                ])
        if not force:
            domain.append(("xerox_send_timestamp", "=", False))
        return domain

    @api.model
    def _xerox_get_domain_picking_batch(self, run_date=None, force=False):
        domain = [
            ("class_id.dte", "=", True),
            ('picking_ids', "!=", False),
        ]
        if run_date:
            domain.append(("date", "=", run_date))
        if not force:
            domain.append(("xerox_send_timestamp", "=", False))
        return domain

    @api.model
    def _xerox_get_records_day(self, company, run_date=None, force=False):
        """Find and returns all documents."""
        return {
            'account.invoice': self.env["account.invoice"].search(
                self._xerox_get_domain_invoice(run_date, force)),
            'stock.picking': self.env["stock.picking"].search(
                self._xerox_get_domain_picking(run_date, force)),
            'stock.picking.batch': self.env["stock.picking.batch"].search(
                self._xerox_get_domain_picking_batch(run_date)),
            }

    @api.model
    def xerox_build_and_send_files(self, company, rsets):
        """
        Given a dict with the document recorsets,
        builds a dict with the file name an content
        """
        # TODO: split lots if exceeding size limit
        if company.backend_acp_id.status != 'confirmed':
            raise UserError(
                _('Company %s is not configured for Xerox integration')
                % company.display_name)
        now = fields.Datetime.context_timestamp(
            self.env.user,
            fields.Datetime.now())
        # Set documents as sent. In case of error, this will be rolled back.
        for rset in rsets.values():
            rset.update(
                {'xerox_send_timestamp': fields.Datetime.to_string(now)})
        doc_count = sum(len(x) for x in rsets.values())
        _logger.info(
            'Building files for %s with timestamp %s, with %d documents',
            company.display_name,
            fields.Datetime.to_string(now),
            doc_count)
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
                file_dict = record.build_files(file_dict, now=now)
        company.backend_acp_id.send(file_dict)

    def cron_xerox_send_files(self, run_date=None, force=False):
        """
        Run Cron Scheduler action.
        Accepts an optional run date,
        that can be either a Date object or a string.
        This can be used to manually run tests for a particular day.
        """
        # if not run_date:
        #     # Use yesterday
        #     today = fields.Date.context_today(self)
        #     run_date = date_utils.add(today, days=-1)
        if run_date and not isinstance(run_date, date):
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
            rsets = self._xerox_get_records_day(
                company, run_date, force)
            self.xerox_build_and_send_files(company, rsets)
