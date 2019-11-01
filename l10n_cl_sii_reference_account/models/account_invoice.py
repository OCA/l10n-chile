# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    reference_ids = fields.One2many(
        "sii.reference", "invoice_id", readonly=True,
        states={"draft": [("readonly", False)]})
