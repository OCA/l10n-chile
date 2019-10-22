from odoo import fields, models
from odoo.addons import decimal_precision as dp


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    
    rate = fields.Float(
        digits=dp.get_precision('Currency'),
        help='The rate of the currency to the currency of rate 1')
