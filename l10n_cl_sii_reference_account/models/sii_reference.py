# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class SiiReference(models.Model):
    _inherit = "sii.reference"

    invoice_id = fields.Many2one("account.invoice", string="Invoice",
                                 ondelete="cascade", index=True, copy=False)

    _sql_constraints = [(
        "name_class_invoice",
        "unique(name, class_id, invoice_id)",
        "The document is already referenced on this invoice!"
    )]

    @api.model
    def create(self, vals):
        res = False
        if vals.get('name', False) and vals.get('class_id', False) and \
                vals.get('invoice_id', False):
            exist = self.search([
                ('name', '=', vals.get('name')),
                ('class_id', '=', vals.get('class_id')),
                ('invoice_id', '=', vals.get('invoice_id')),
            ])
            if not exist:
                res = super().create(vals)
        else:
            res = super().create(vals)
        return res
