# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class MasiveDTEProcessWizard(models.TransientModel):
    _name = "sii.dte.masive.process.wizard"
    _description = "SII Masive DTE Process Wizard"

    action = fields.Selection([
        ("create", "Create"),
        ("accept", "Create Accept All"),
        ("reject", "Create Refuse All")],
        string="Action",
        default="create",
        required=True)

    @api.multi
    def confirm(self):
        dtes = self.env["mail.message.dte"].browse(
            self._context.get("active_ids", []))
        if self.action == "create":
            dtes.pre_process()
        else:
            dtes.process(option=self.action)
