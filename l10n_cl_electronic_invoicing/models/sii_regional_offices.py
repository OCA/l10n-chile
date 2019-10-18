# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiRegionalOffices(models.Model):
    _name = "sii.regional.offices"
    _description = "SII Regional Offices"

    name = fields.Char("Regional Office Name")
    city_ids = fields.Many2many(
        "res.city", id1="sii_regional_office_id", id2="city_id",
        string="Cities")
