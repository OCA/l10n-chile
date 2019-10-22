# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 Konos
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.addons import decimal_precision as dp


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    rate = fields.Float(
        digits=dp.get_precision('Currency'),
        help='The rate of the currency to the currency of rate 1')
