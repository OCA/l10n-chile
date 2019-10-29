# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompanyDocument(models.Model):
    _name = "res.company.document"
    _description = "Documents To Sign"

    name = fields.Selection([], string="Document", required=True)
    xsd = fields.Text(string="XSD", required=True)
    xml_template = fields.Text(string="XML Template", required=True)
