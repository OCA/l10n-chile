# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    dte_sii_environment = fields.Selection(
        [
            ("demo", "Demo / Simulated"),
            ("certification", "Certification"),
            ("production", "Production"),
        ],
        string="DTE SII Environment",
        default="demo",
        required=True,
        groups="l10n_cl_dte_base.group_dte_manager",
    )
