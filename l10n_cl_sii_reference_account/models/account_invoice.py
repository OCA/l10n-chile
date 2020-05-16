# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    reference_ids = fields.One2many(
        "sii.reference", "invoice_id", readonly=True,
        states={"draft": [("readonly", False)]})

    def prepare_ref_values(self, record=False):
        res = {}
        if record:
            if record._name == 'account.invoice':
                res.update({
                    'name': record.number,
                    'motive': record.name,
                    'code': "1",
                    'date': record.date_invoice,
                    'class_id': record.class_id.id,
                    'invoice_id': self.id,
                })
            elif record._name == 'stock.picking':
                res.update({
                    'name': record.name,
                    'motive': record.name,
                    'date':
                        record.date_done and record.date_done.date() or
                        record.scheduled_date.date(),
                    'class_id': record.class_id.id,
                    'invoice_id': self.id,
                })
            elif record._name == "sale.order":
                if record.client_order_ref:
                    # Customer Purchase Order
                    res.update({
                        'name': record.client_order_ref,
                        'motive': record.name,
                        'date': record.confirmation_date.date(),
                        'class_id':
                            self.env.ref('l10n_cl_sii_reference.dc_oc').id,
                        'invoice_id': self.id,
                    })
            elif record._name == "sale.blanket.order":
                if record.client_order_ref:
                    # Customer Purchase Order
                    res.update({
                        'name': record.client_order_ref,
                        'motive': record.name,
                        'date': record.validity_date,
                        'class_id': self.env.ref(
                            'l10n_cl_sii_reference.dc_oc').id,
                        'invoice_id': self.id,
                    })
        return res

    def create_refs_from_sol(self, sol=False):
        ref = self.env['sii.reference']
        if sol and sol.order_id.client_order_ref:
            ref.create(self.prepare_ref_values(sol.order_id))
        if sol and sol.blanket_order_line:
            ref.create(self.prepare_ref_values(
                sol.blanket_order_line.order_id))
        for picking in sol.order_id.picking_ids.filtered(
                lambda x:
                x.class_id.id is not False and
                x.picking_type_id.code == 'outgoing'):
            ref.create(self.prepare_ref_values(picking))
        return True

    @api.depends('refund_invoice_id', 'invoice_lines')
    def compute_refs(self):
        for rec in self:
            if not rec.reference_ids:
                ref = self.env['sii.reference']
                if rec.refund_invoice_id:
                    ref.create(rec.prepare_ref_values(rec.refund_invoice_id))
                elif rec.invoice_line_ids:
                    for line in rec.invoice_line_ids:
                        for sol in line.sale_line_ids:
                            rec.create_refs_from_sol(sol)

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        for rec in self.filtered(lambda x: x.state == 'draft'):
            rec.compute_refs()
        return res
