# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import binascii
import hashlib

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ElectronicArtifact(models.Model):
    _name = "l10n_cl.electronic.artifact"
    _description = "Immutable DTE Evidence Artifact"
    _order = "id desc"
    _check_company_auto = True

    document_id = fields.Many2one(
        "l10n_cl.electronic.document", required=True, index=True, ondelete="restrict"
    )
    company_id = fields.Many2one(
        related="document_id.company_id", store=True, index=True
    )
    is_simulated = fields.Boolean(compute="_compute_is_simulated", store=True)
    role = fields.Selection(
        [
            ("caf_source", "CAF Source"),
            ("source_snapshot", "Source Snapshot"),
            ("unsigned_xml", "Unsigned XML"),
            ("signed_xml", "Signed XML"),
            ("sii_request", "SII Request"),
            ("sii_response", "SII Response"),
            ("status_response", "Status Response"),
        ],
        required=True,
        index=True,
    )
    content = fields.Binary(
        required=True,
        attachment=True,
        copy=False,
        groups="l10n_cl_dte_base.group_dte_manager",
    )
    sha256 = fields.Char(required=True, index=True, copy=False, readonly=True)
    mimetype = fields.Char(required=True)
    encoding = fields.Char()
    byte_count = fields.Integer(readonly=True, copy=False)
    producer_version = fields.Char()

    supersedes_id = fields.Many2one(
        "l10n_cl.electronic.artifact",
        string="Previous Signature",
        readonly=True,
        copy=False,
        ondelete="restrict",
        check_company=True,
    )

    _sql_constraints = [
        (
            "signature_successor_uniq",
            "unique(supersedes_id)",
            "A signature can only have one replacement.",
        ),
    ]

    @api.depends("document_id.sii_environment")
    def _compute_is_simulated(self):
        for artifact in self:
            artifact.is_simulated = artifact.document_id.sii_environment == "demo"

    @api.model_create_multi
    def create(self, vals_list):
        """Calculate evidence metadata from the exact persisted bytes."""
        if not self.env.su and (
            self.env.context.get("default_supersedes_id")
            or any(vals.get("supersedes_id") for vals in vals_list)
        ):
            raise AccessError(
                self.env._("Regenerate signatures through the document workflow.")
            )
        return super().create(self._prepare_evidence_values(vals_list))

    def _prepare_evidence_values(self, vals_list):
        self.env["l10n_cl.electronic.document"]._check_dte_manager(
            self.env._("Only a DTE manager can add evidence.")
        )
        normalized_vals_list = []
        for vals in vals_list:
            vals = vals.copy()
            encoded_content = vals.get("content")
            if not encoded_content:
                raise ValidationError(self.env._("Evidence content is required."))
            try:
                raw_content = base64.b64decode(encoded_content, validate=True)
            except (binascii.Error, TypeError, ValueError) as error:
                raise ValidationError(
                    self.env._("Evidence must be valid base64 content.")
                ) from error
            vals["sha256"] = hashlib.sha256(raw_content).hexdigest()
            vals["byte_count"] = len(raw_content)
            normalized_vals_list.append(vals)
        return normalized_vals_list

    def _create_signature_revision(self, previous, content, producer_version):
        """Append a signed XML revision without changing any previous bytes."""
        previous.ensure_one()
        document = previous.document_id
        document.check_access("write")
        document._lock_lifecycle()
        document._check_signature_revision()
        if previous != document._get_signed_artifact():
            raise ValidationError(
                self.env._("Only the current signature can be replaced.")
            )
        previous.action_verify_integrity()
        with self.env.cr.savepoint():
            document._advance_signature_revision()
            return (
                self.sudo()
                .create(
                    {
                        "document_id": document.id,
                        "role": "signed_xml",
                        "supersedes_id": previous.id,
                        "content": base64.b64encode(content),
                        "mimetype": "application/xml",
                        "encoding": previous.encoding,
                        "producer_version": producer_version,
                    }
                )
                .with_env(self.env)
            )

    def write(self, vals):  # pylint: disable=method-required-super
        raise AccessError(self.env._("DTE evidence is immutable."))

    def unlink(self):  # pylint: disable=method-required-super
        raise AccessError(self.env._("DTE evidence cannot be deleted."))

    def copy(self, default=None):  # pylint: disable=method-required-super
        raise AccessError(self.env._("DTE evidence cannot be duplicated."))

    def action_verify_integrity(self):
        """Recompute the digest and byte count from the stored content."""
        self.ensure_one()
        self.env["l10n_cl.electronic.document"]._check_dte_manager(
            self.env._("Only a DTE manager can verify evidence content.")
        )
        encoded_content = self.content
        try:
            raw_content = base64.b64decode(encoded_content, validate=True)
        except (binascii.Error, TypeError, ValueError) as error:
            raise ValidationError(
                self.env._("Stored evidence is not valid base64 content.")
            ) from error
        actual_digest = hashlib.sha256(raw_content).hexdigest()
        actual_byte_count = len(raw_content)
        if actual_digest != self.sha256 or actual_byte_count != self.byte_count:
            raise ValidationError(
                self.env._(
                    "Stored evidence does not match its recorded digest and size."
                )
            )
        return True
