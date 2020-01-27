# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class FmsRoute(models.Model):
    _name = "fsm.route"
    _inherit = ["fsm.route", "etd.mixin"]
