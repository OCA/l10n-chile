# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class EtdMixin(models.AbstractModel):
    _inherit = 'etd.mixin'

    def _compute_class_id_domain(self):
        return []

    class_id = fields.Many2one(
        "sii.document.class", string="SII Document",
        track_visibility='onchange',
        domain=lambda self: self._compute_class_id_domain())
