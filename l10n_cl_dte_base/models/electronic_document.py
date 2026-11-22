# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ElectronicDocument(models.Model):
    _name = "l10n_cl.electronic.document"
    _description = "Chilean Electronic Tax Document"
    _order = "id desc"
    _check_company_auto = True
    _sql_constraints = [
        (
            "source_key_company_uniq",
            "unique(company_id, source_key)",
            "A source invoice can only have one electronic document per company.",
        )
    ]

    name = fields.Char(required=True, index=True, copy=False)
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
        readonly=True,
        index=True,
        copy=False,
    )
    document_code = fields.Char(required=True, index=True)
    source_key = fields.Char(required=True, index=True, copy=False)
    artifact_ids = fields.One2many(
        "l10n_cl.electronic.artifact", "document_id", string="Evidence"
    )

    @api.constrains("document_code", "source_key")
    def _check_document_identity(self):
        for document in self:
            if not (document.document_code or "").isdigit():
                raise ValidationError(
                    self.env._("The DTE type code must contain digits only.")
                )
            if not (document.source_key or "").strip():
                raise ValidationError(self.env._("The source key cannot be empty."))

    @api.model_create_multi
    def create(self, vals_list):
        """Create a new document with the company’s current SII environment."""
        normalized_vals_list = []
        for vals in vals_list:
            vals = vals.copy()
            company_id = vals.get("company_id") or self.env.company.id
            vals["company_id"] = company_id
            company = self.env["res.company"].browse(company_id).exists()
            if len(company) != 1:
                raise ValidationError(
                    self.env._("A valid company is required for a DTE.")
                )
            environment = vals.get("sii_environment") or company.dte_sii_environment
            if environment != company.dte_sii_environment:
                raise ValidationError(
                    self.env._(
                        "A new DTE must capture the company's current SII environment."
                    )
                )
            vals["sii_environment"] = environment
            if vals.get("source_key"):
                vals["source_key"] = vals["source_key"].strip()
            if vals.get("document_code"):
                vals["document_code"] = vals["document_code"].strip()
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    def write(self, vals):
        """Keep document identity immutable."""
        protected_fields = {
            "name",
            "company_id",
            "sii_environment",
            "document_code",
            "source_key",
        }
        if protected_fields.intersection(vals):
            raise UserError(self.env._("DTE identity fields cannot be changed."))
        return super().write(vals)

    def unlink(self):  # pylint: disable=method-required-super
        raise UserError(self.env._("Electronic tax documents cannot be deleted."))

    def copy(self, default=None):  # pylint: disable=method-required-super
        raise UserError(self.env._("Electronic tax documents cannot be duplicated."))

    @api.model
    def _check_dte_manager(self, message):
        if not self.env.su and not self.env.user.has_group(
            "l10n_cl_dte_base.group_dte_manager"
        ):
            raise AccessError(message)
