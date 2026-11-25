# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import binascii
import hashlib

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_MAX_CAF_BYTES = 1024 * 1024


class CafAuthorization(models.Model):
    _name = "l10n_cl.caf.authorization"
    _description = "SII Folio Authorization (CAF)"
    _order = "date_from desc, id desc"
    _check_company_auto = True
    _sql_constraints = [
        (
            "caf_company_digest_uniq",
            "unique(company_id, caf_digest)",
            "This CAF file is already registered for the company.",
        ),
    ]

    name = fields.Char(required=True, copy=False)
    company_id = fields.Many2one(
        "res.company", required=True, index=True, default=lambda self: self.env.company
    )
    sii_environment = fields.Selection(
        [
            ("demo", "Demo / Simulated"),
            ("certification", "Certification"),
            ("production", "Production"),
        ],
        required=True,
        index=True,
        default=lambda self: self.env.company.dte_sii_environment,
        groups="l10n_cl_dte_base.group_dte_manager",
    )
    is_synthetic = fields.Boolean(
        string="Synthetic Demo Data",
        readonly=True,
        copy=False,
        help="Identifies a CAF generated locally for the simulated Demo mode.",
    )
    document_code = fields.Char(required=True, index=True)
    issuer_vat = fields.Char(required=True, index=True)
    folio_start = fields.Integer(required=True)
    folio_end = fields.Integer(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    caf_file = fields.Binary(
        required=True,
        attachment=True,
        copy=False,
        groups="l10n_cl_dte_base.group_dte_manager",
    )
    caf_filename = fields.Char(groups="l10n_cl_dte_base.group_dte_manager")
    caf_digest = fields.Char(required=True, index=True, copy=False, readonly=True)

    state = fields.Selection(
        [("draft", "Draft")], default="draft", required=True, index=True, copy=False
    )

    @api.constrains("folio_start", "folio_end", "date_from", "date_to")
    def _check_registration_range(self):
        for caf in self:
            if caf.folio_start <= 0 or caf.folio_end < caf.folio_start:
                raise ValidationError(self.env._("CAF folio range is invalid."))
            if caf.date_to and caf.date_to < caf.date_from:
                raise ValidationError(self.env._("CAF validity period is invalid."))

    @api.constrains("is_synthetic", "sii_environment")
    def _check_synthetic_environment(self):
        for caf in self:
            if caf.is_synthetic and caf.sii_environment != "demo":
                raise ValidationError(
                    self.env._("Synthetic CAF authorizations can only use Demo.")
                )

    @api.constrains("company_id", "caf_digest")
    def _check_unique_caf_digest(self):
        for caf in self:
            caf._check_duplicate_digest(caf.company_id.id, caf.caf_digest, caf.id)

    @api.model
    def _check_duplicate_digest(self, company_id, digest, exclude_id=False):
        if self.search_count(
            [
                ("company_id", "=", company_id),
                ("caf_digest", "=", digest),
                ("id", "!=", exclude_id),
            ],
            limit=1,
        ):
            raise ValidationError(
                self.env._("This CAF file is already registered for the company.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager()
        normalized = []
        for vals in vals_list:
            vals = vals.copy()
            company = (
                self.env["res.company"]
                .browse(vals.get("company_id") or self.env.company.id)
                .exists()
            )
            if not company:
                raise ValidationError(self.env._("A valid CAF company is required."))
            vals["company_id"] = company.id
            vals.setdefault("sii_environment", company.dte_sii_environment)
            if vals.get("state", "draft") != "draft":
                raise ValidationError(
                    self.env._("A CAF must be created in draft state.")
                )
            vals["state"] = "draft"
            vals["caf_digest"] = hashlib.sha256(
                self._decode_content(vals.get("caf_file"))
            ).hexdigest()
            self._check_duplicate_digest(company.id, vals["caf_digest"])
            normalized.append(vals)
        return super().create(normalized)

    def write(self, vals):
        self._check_manager()
        if {"state", "caf_digest", "is_synthetic"}.intersection(vals):
            raise UserError(
                self.env._("CAF state and integrity metadata are protected.")
            )
        if any(caf.state != "draft" for caf in self):
            raise UserError(self.env._("A validated CAF is immutable."))
        values = vals.copy()
        if "caf_file" in values:
            values["caf_digest"] = hashlib.sha256(
                self._decode_content(values["caf_file"])
            ).hexdigest()
        return super().write(values)

    def unlink(self):  # pylint: disable=method-required-super
        raise AccessError(self.env._("CAF authorizations cannot be deleted."))

    def copy(self, default=None):  # pylint: disable=method-required-super
        raise AccessError(self.env._("CAF authorizations cannot be duplicated."))

    def _check_caf_integrity(self, content=None):
        self.ensure_one()
        if content is None:
            self.invalidate_recordset(["caf_file"])
            content = self._decode_content(self.caf_file)
        if hashlib.sha256(content).hexdigest() != self.caf_digest:
            raise ValidationError(
                self.env._(
                    "The stored CAF content does not match its registered SHA-256."
                )
            )

    @api.model
    def _decode_content(self, encoded_content):
        if not encoded_content:
            raise ValidationError(self.env._("CAF file content is required."))
        if not isinstance(encoded_content, str | bytes):
            raise ValidationError(self.env._("CAF file content must be valid base64."))
        if len(encoded_content) > 4 * ((_MAX_CAF_BYTES + 2) // 3):
            raise ValidationError(self.env._("CAF content exceeds the size limit."))
        try:
            content = base64.b64decode(encoded_content, validate=True)
        except (binascii.Error, TypeError, ValueError) as error:
            raise ValidationError(
                self.env._("CAF file content must be valid base64.")
            ) from error
        if len(content) > _MAX_CAF_BYTES:
            raise ValidationError(self.env._("CAF content exceeds the size limit."))
        return content

    def _check_manager(self):
        self.env["l10n_cl.electronic.document"]._check_dte_manager(
            self.env._("Only a DTE manager can manage CAF authorizations.")
        )
