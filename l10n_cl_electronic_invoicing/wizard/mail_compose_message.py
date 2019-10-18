# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model,
                             res_id):
        result = super(MailComposer, self).onchange_template_id(
            template_id, composition_mode, model, res_id
        )
        atts = self._context.get("default_attachment_ids", [])
        for att in atts:
            if not result["value"].get("attachment_ids"):
                result["value"]["attachment_ids"] = [(6, 0, [])]
            if att not in result["value"]["attachment_ids"][0][2]:
                result["value"]["attachment_ids"][0][2].append(att)
        return result
