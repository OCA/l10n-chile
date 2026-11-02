# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import AccessError, UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    def action_open_dte_demo_setup(self):
        self.ensure_one()
        if not self.env.user.has_group("l10n_cl_dte_core.group_dte_manager"):
            raise AccessError(_("Only a DTE manager can prepare Demo configuration."))
        if self.dte_sii_environment != "demo":
            raise UserError(_("Set the company's DTE SII environment to Demo first."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Prepare Synthetic DTE Demo Configuration"),
            "res_model": "l10n_cl.dte.demo.setup.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_company_id": self.id},
        }
