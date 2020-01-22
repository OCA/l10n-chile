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
        group.ensure_one()
        if group._name == 'account.invoice':
            return group.date_invoice
        if group._name == 'stock.picking':
            return group.date_done

    def _xerox_group(self, groups=None):
        """
        Given a recordset.

        groups list contains all the records matching that key.
        """
        group_dict = {}
        date = False
        for group in groups:
            for group_data in group:
                group_list = group_dict and group_dict[date] or [group_data]
                date = (self._xerox_group_key(group_data)).strftime("%Y-%m-%d")
                if date in group_dict:
                    group_list.append(group_data)
                group_dict[date] = group_list
        return group_dict
