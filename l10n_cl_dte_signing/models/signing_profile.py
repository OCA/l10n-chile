# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class DteSigningProfile(models.Model):
    _name = "l10n_cl.dte.signing.profile"
    _description = "DTE Signing Profile"
    _order = "company_id, sii_environment"
    _check_company_auto = True
    _sql_constraints = [
        (
            "company_environment_uniq",
            "unique(company_id, sii_environment)",
            "A signing profile already exists for this company and SII environment.",
        ),
        (
            "certificate_uniq",
            "unique(certificate_id)",
            "A certificate can only be used by one DTE signing profile.",
        ),
    ]

    name = fields.Char(required=True)
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
    )
    certificate_id = fields.Many2one(
        "certificate.certificate",
        required=True,
        check_company=True,
        ondelete="restrict",
    )
    active = fields.Boolean(default=True)
    is_synthetic = fields.Boolean(
        string="Synthetic Demo Data",
        readonly=True,
        copy=False,
        help="Identifies a certificate generated locally for the simulated Demo mode.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager()
        for values in vals_list:
            company = self.env["res.company"].browse(
                values.get("company_id") or self.env.company.id
            )
            certificate = self.env["certificate.certificate"].browse(
                values.get("certificate_id")
            )
            if certificate and certificate.company_id != company:
                raise ValidationError(
                    _("The signing certificate must belong to the selected company.")
                )
        return super().create(vals_list)

    def write(self, vals):
        self._check_manager()
        if "is_synthetic" in vals:
            raise UserError(_("The synthetic material marker cannot be changed."))
        if any(profile.active for profile in self) and {
            "company_id",
            "sii_environment",
            "certificate_id",
        }.intersection(vals):
            raise UserError(
                _("Deactivate a signing profile before changing its identity or key.")
            )
        return super().write(vals)

    def unlink(self):  # pylint: disable=method-required-super
        raise AccessError(_("Signing profiles are retained as configuration evidence."))

    @api.constrains("company_id", "certificate_id")
    def _check_certificate_company(self):
        for profile in self:
            if profile.certificate_id.company_id != profile.company_id:
                raise ValidationError(
                    _("The signing certificate must belong to the selected company.")
                )

    @api.constrains("sii_environment", "is_synthetic")
    def _check_synthetic_environment(self):
        for profile in self:
            if profile.is_synthetic and profile.sii_environment != "demo":
                raise ValidationError(
                    _("Synthetic signing profiles can only use Demo environment.")
                )

    @api.model
    def _check_manager(self):
        if not self.env.user.has_group("l10n_cl_dte_core.group_dte_manager"):
            raise AccessError(_("Only a DTE manager can manage signing profiles."))
