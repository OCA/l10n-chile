# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models
from ...queue_job.job import job


class EtdMixin(models.AbstractModel):
    _inherit = "etd.mixin"

    @job
    def document_sign(self):
        """
        Only sign and send the document if backend is set to send immediately.
        Otherwise, skip since the documents will be send by a scheduled job.
        """
        backend = self.company_id.backend_acp_id
        if backend.send_immediately:
            return super().document_sign()

    def _xerox_group_key(self):
        """
        Given a Model record.
        Returns a tuple, to use as grouping key.
        """
        self.ensure_one()
        if self._name == "account.invoice":
            return (self.date_invoice,)
        if self._name == "stock.picking":
            return (self.date_done,)

    def xerox_group(self, group_dict=None):
        """
        Given a recordset, groups list contains all the records
        matching the same key.

        Returns a dict, where key is a tuple for each grouping key,
        and the value is a list with the matching records.
        """
        group_dict = group_dict or {}
        for rec in self:
            group_key = rec._xerox_group_key()
            group_dict.setdefault(group_key, [])
            group_dict[group_key].append(rec)
        return group_dict
