# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import tempfile
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
            route = [fms_order.route_id
                     for fms_order in group.fsm_order_ids]
            return (group.date_invoice, route)
        if group._name == 'stock.picking':
            return (group.date_done, group.fsm_order_id.route_id)

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
                date = (self._xerox_group_key(group_data)
                        [0]).strftime("%Y-%m-%d")
                if date in group_dict:
                    group_list.append(group_data)
                group_dict[date] = group_list
        return group_dict

    def get_etd_directory(self, file, file_list, res_content, etd_document):
        """Get directory path."""
        doc_directory_name = tempfile.mkdtemp()
        file_dir = file.get('directory', '')
        doc_filename = (
            doc_directory_name + "%s/%s" % (
                file_dir and '/' + file_dir, file.get('name')))
        return doc_filename

    def get_etd_filename(self, file):
        """Get Directory."""
        res = super(EtdMixin, self).get_etd_filename(file)
        self._get_etd_directory(file=file, etd_document=res)
        return res
