# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class MasiveDTEAcceptWizard(models.TransientModel):
    _name = "sii.dte.masive.accept.wizard"
    _description = "SII Masive DTE Accept Wizard"

    @api.multi
    def confirm(self):
        dtes = self.env["mail.message.dte.document"].browse(
            self._context.get("active_ids", []))
        return dtes.accept_document()
