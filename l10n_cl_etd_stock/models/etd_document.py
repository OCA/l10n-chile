# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class EtdDocument(models.Model):
    _inherit = "etd.document"

    model = fields.Selection(selection_add=[("stock.picking", "Picking")])
