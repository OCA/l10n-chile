# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class EtdDocument(models.Model):
    _inherit = 'etd.document'

    is_xerox = fields.Boolean(string="Is Xerox!")

    def _xerox_get_records(self, date=None):
        """Find and returns all documents."""
        if not date:
            date = datetime.now() - timedelta(1)
        invoice_date = datetime.strftime(date, '%Y-%m-%d')
        s_date = date + relativedelta(hour=0, minute=0)
        end_date = datetime.strftime(s_date + timedelta(1), '%Y-%m-%d %H:%M')
        start_date = datetime.strftime(s_date, '%Y-%m-%d %H:%M')
        invoices = self.env['account.invoice'].search([
            ('date_invoice', '=', invoice_date),
            ('state', '=', 'open')])
        deliveries = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
            ('date_done', '>=', start_date),
            ('date_done', '<=', end_date)])
        return (invoices, deliveries)

    @api.model
    def xerox_send_files(self, date=None):
        """Scheduler action."""
        grouped_data = self._xerox_get_records(date)
        etd_mixin_obj = self.env['etd.mixin']
        backend_acp_obj = self.env['backend.acp']

        etd_mixin_obj._xerox_group(grouped_data)

        documents = self.search([('is_xerox', '=', True)])
        file_data = {}
        for document in documents:
            file_data.append(etd_mixin_obj.build_files(document))

        backend_acp_obj.send(file_data)
