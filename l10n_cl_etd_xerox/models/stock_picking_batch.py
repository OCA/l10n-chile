# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class PickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    # TODO: move this this fieldservice_route
    company_id = fields.Many2one(
        'res.company',
        default=lambda s: s.env.user.company_id)

    def get_xerox_lines(self):
        """
        Returns  a dictionary with the lines for the Xerox Picking Batch report
        """
        lines = {}
        for line in self.mapped('picking_ids.move_ids_without_package'):
            key = (line.product_id, line.product_uom)
            lines.setdefault(key, {'quantity': 0, 'amount': 0})
            lines[key]['quantity'] += (
                line.quantity_done or line.product_uom_qty)
            lines[key]['amount'] += line.sale_line_id.price_subtotal
        return lines
