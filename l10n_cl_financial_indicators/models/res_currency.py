from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class Currency(models.Model):
    _inherit = "res.currency"
    
    rate = fields.Float(
        compute='_compute_current_rate', string='Current Rate',
        digits=dp.get_precision('Currency'),
        help='The rate of the currency to the currency of rate 1.')

    rounding = fields.Float(
        string='Rounding Factor', default=0.01,
        digits=dp.get_precision('Currency'))
    
    @api.multi
    def _compute_current_rate(self):
        date = self._context.get('date') or fields.Datetime.now()
        company_id = self._context.get(
            'company_id') or self.env['res.users']._get_company().id
        # the subquery selects the last rate before 'date' for
        # the given currency/company
        query = """SELECT c.id, (
        SELECT r.rate
        FROM res_currency_rate r
        WHERE r.currency_id = c.id AND r.name <= %s
        AND (r.company_id IS NULL OR r.company_id = %s)
        ORDER BY r.company_id, r.name DESC
        LIMIT 1) AS rate
            FROM res_currency c
            WHERE c.id IN %s"""
        self._cr.execute(query, (date, company_id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        for currency in self:
            currency.rate = currency_rates.get(currency.id) or 1.0


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    
    rate = fields.Float(
        digits=dp.get_precision('Currency'),
        help='The rate of the currency to the currency of rate 1')
