# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class StockPickingBatch(models.Model):
    _name = 'stock.picking.batch'
    _inherit = ['stock.picking.batch', 'etd.mixin']

    def _compute_class_id_domain(self):
        return [('document_type', '=', 'stock_picking')]

    @api.multi
    def done(self):
        res = super().done()
        for rec in self:
            if self.class_id:
                rec.with_delay().document_sign()
        return res

    @api.model
    def create(self, vals):
        sii_obj = self.env['sii.document.class']
        sii_document = sii_obj.search(
            [('name', 'ilike', 'Guía de Despacho Electrónica'),
             ('prefix', '=', 'GDE'),
             ('code', '=', 52),
             ('document_type', '=', 'stock_picking')], limit=1)
        vals.update({'class_id': sii_document and sii_document.id})
        return super().create(vals)
