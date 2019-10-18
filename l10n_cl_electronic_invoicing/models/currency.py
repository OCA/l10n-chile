# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from odoo.tools import float_round


def float_round_custom(
    value, precision_digits=None, precision_rounding=None,
        rounding_method="HALF-UP"):
    result = float_round(value, precision_digits, precision_rounding,
                         rounding_method)
    if precision_rounding == 1:
        return int(result)
    return result


class ResCurrency(models.Model):
    _inherit = "res.currency"

    code = fields.Char(string="Código")
    abreviatura = fields.Char(string="Abreviatura")

    @api.multi
    def round(self, amount):
        """Return ``amount`` rounded  according to ``self``'s rounding rules.

           :param float amount: the amount to round
           :return: rounded float
        """
        # TODO: Need to check why it calls round() from sale.py, _amount_all()
        #  with *No* ID after below commits,
        #  https://github.com/odoo/odoo/commit/36ee1ad813204dcb91e9f5f20d746dff6f080ac2 # noqa
        #  https://github.com/odoo/odoo/commit/0b6058c585d7d9a57bd7581b8211f20fca3ec3f7 # noqa
        #  Removing self.ensure_one() will make few test cases to break of
        #  modules event_sale, sale_mrp and stock_dropshipping.
        # self.ensure_one()
        return float_round_custom(amount, precision_rounding=self.rounding)
