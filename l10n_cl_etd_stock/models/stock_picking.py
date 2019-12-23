# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'etd.mixin']

    def _compute_class_id_domain(self):
        return [('document_type', '=', 'stock_picking')]

    @api.multi
    def action_done(self):
        res = super().action_done()
        sign = self._name in [x.model for x in self.company_id.etd_ids]
        for picking in self:
            if sign and picking.location_dest_id.usage == 'customer':
                self.with_delay().document_sign()
        return res

    @api.model
    def create(self, vals):
        if vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            if partner and partner.invoicing_policy == 'eguide':
                sii_obj = self.env['sii.document.class']
                sii_document = sii_obj.search(
                    [('name', 'ilike', 'Guía de Despacho Electrónica'),
                     ('prefix', '=', 'GDE'),
                     ('code', '=', 52),
                     ('document_type', '=', 'stock_picking')], limit=1)
                vals.update({'class_id': sii_document and sii_document.id})
        return super(StockPicking, self).create(vals)
