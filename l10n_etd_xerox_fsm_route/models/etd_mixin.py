# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class EtdMixin(models.AbstractModel):

    _inherit = 'etd.mixin'

    def _xerox_group_key(self, group=None):
        """
        Given a Model record.

        returns a tuple, to use as grouping key.
        """
        # WIP
        group.ensure_one()
        if group._name == 'account.invoice':
            return (group.date_invoice, 'route')
        if group._name == 'stock.picking':
            return (group.date_done, 'route')

    def get_get_etd_directory(self, file):
        """Get directory path."""
        # WIP
        return self.set_jinja_env()

    def get_etd_filename(self, file):
        """Get Directory."""
        # WIP
        return self._get_etd_directory(file)
