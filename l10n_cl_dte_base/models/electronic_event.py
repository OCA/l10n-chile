# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

_EVENT_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ElectronicEvent(models.Model):
    _name = "l10n_cl.electronic.event"
    _description = "DTE Audit Event"
    _order = "create_date desc, id desc"
    _check_company_auto = True

    document_id = fields.Many2one(
        "l10n_cl.electronic.document", required=True, index=True, ondelete="restrict"
    )
    company_id = fields.Many2one(
        related="document_id.company_id", store=True, index=True
    )
    event_code = fields.Char(required=True, index=True)
    state_domain = fields.Selection(
        [("preparation", "Preparation"), ("fiscal", "Fiscal")],
        required=True,
        index=True,
    )
    from_state = fields.Char()
    to_state = fields.Char()
    message = fields.Text()
    correlation_key = fields.Char(index=True)
    artifact_id = fields.Many2one(
        "l10n_cl.electronic.artifact",
        index=True,
        ondelete="restrict",
        check_company=True,
    )

    @api.constrains("event_code")
    def _check_event_code(self):
        for event in self:
            if not _EVENT_CODE_RE.fullmatch(event.event_code or ""):
                raise ValidationError(
                    self.env._(
                        "Use lowercase letters, digits and underscores in event codes."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Only trusted server-side actions may create audit events."""
        if not self.env.su:
            raise AccessError(
                self.env._("Audit events can only be created by DTE actions.")
            )
        return super().create(vals_list)

    def write(self, vals):  # pylint: disable=method-required-super
        raise AccessError(self.env._("DTE audit events are immutable."))

    def unlink(self):  # pylint: disable=method-required-super
        raise AccessError(self.env._("DTE audit events cannot be deleted."))
