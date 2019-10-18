# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PaymentTerm(models.Model):
    _inherit = "account.payment.term"

    dte_sii_code = fields.Selection(
        (("1", "1: Contado"),
         ("2", "2: Credito"),
         ("3", "3: Otro")),
        "DTE Sii Code")
