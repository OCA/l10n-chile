# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    xerox_code = fields.Char(
        required=True, default="00000", size=5,
        help="Code to use for Xerox ETD integration")
