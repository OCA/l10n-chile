# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SiiReference(models.Model):
    _name = "sii.reference"
    _description = "SII References"

    name = fields.Char(string="Origin", required=True)
    class_id = fields.Many2one(
        "sii.document.class", string="SII Document Class", index=True,
        required=True)
    code = fields.Selection([
        ("1", "Cancel the referenced document"),
        ("2", "Fix the text of the referenced document"),
        ("3", "Fix the amount of the referenced document")],
        string="Code")
    motive = fields.Char(string="Motive")
    date = fields.Date(string="Document Date", required=True)
