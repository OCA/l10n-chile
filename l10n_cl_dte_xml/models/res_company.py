# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    dte_sii_activity_code = fields.Char(
        string="SII Economic Activity Code",
        help="Positive SII activity code included in the DTE issuer section.",
        groups="l10n_cl_dte_core.group_dte_manager",
    )

    @api.constrains("dte_sii_activity_code")
    def _check_dte_sii_activity_code(self):
        for company in self:
            code = (company.dte_sii_activity_code or "").strip()
            if code and (not re.fullmatch(r"[0-9]{1,6}", code) or int(code) <= 0):
                raise ValidationError(
                    _(
                        "The SII activity code must be a positive code of at most "
                        "6 digits."
                    )
                )
