# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class PickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    def get_xerox_lines(self):
        """
        Returns  a dictionary with the lines for the Xerox Picking Batch report
        """
        lines = {}
        for move in self.mapped('picking_ids.move_ids_without_package'):
            key = (move.product_id, move.product_uom)
            lines.setdefault(key, {'quantity': 0, 'price': 0, 'amount': 0})
            line = lines[key]
            line['quantity'] += (move.quantity_done or move.product_uom_qty)
        so_lines = self.mapped('picking_ids.sale_id.order_line')
        for key, line in lines.items():
            prices = [
                x.price_unit for x in so_lines
                if x.product_id == key[0] and x.product_uom == key[1]]
            line['price'] = max(prices) if prices else 0
            line['amount'] = line['quantity'] * line['price']
        return lines
