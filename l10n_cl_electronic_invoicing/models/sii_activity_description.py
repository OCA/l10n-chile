# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PartnerActivities(models.Model):
    _name = "sii.activity.description"
    _description = "SII Economical Activities Printable Description"

    name = fields.Char(string="Glosa", required=True, translate=True)
    vat_affected = fields.Selection(
        (("SI", "Si"),
         ("NO", "No"),
         ("ND", "ND")),
        string="VAT Affected",
        required=True,
        translate=True,
        default="SI")
    active = fields.Boolean(
        string="Active",
        help="Allows you to hide the activity without removing it.",
        default=True)
