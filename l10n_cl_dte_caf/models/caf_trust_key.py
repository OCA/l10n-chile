# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class CafTrustKey(models.Model):
    _name = "l10n_cl.caf.trust.key"
    _description = "SII CAF Signature Trust Key"
    _order = "key_id, valid_from desc"
    _sql_constraints = [
        (
            "caf_trust_key_id_scope_start_uniq",
            "unique(key_id, scope, valid_from)",
            "A trust key with this ID and start date already exists.",
        )
    ]

    name = fields.Char(required=True)
    key_id = fields.Char(required=True, index=True)
    scope = fields.Selection(
        [("demo", "Demo"), ("official", "Official SII")],
        required=True,
        default="official",
        index=True,
    )
    is_synthetic = fields.Boolean(
        string="Synthetic Demo Data",
        readonly=True,
        copy=False,
        help="Identifies a public key generated locally for the simulated Demo mode.",
    )
    algorithm = fields.Selection(
        [("SHA1withRSA", "SHA1 with RSA")], required=True, default="SHA1withRSA"
    )
    public_key_pem = fields.Text(required=True)
    fingerprint = fields.Char(required=True, readonly=True, index=True, copy=False)
    valid_from = fields.Date(required=True, index=True)
    valid_to = fields.Date(index=True)
    source_url = fields.Char(required=True)

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager()
        values_list = []
        for vals in vals_list:
            vals = vals.copy()
            if vals.get("algorithm", "SHA1withRSA") != "SHA1withRSA":
                raise ValidationError(
                    _("Only SHA1withRSA CAF trust keys are supported.")
                )
            public_key = self._load_rsa_public_key(vals.get("public_key_pem"))
            canonical_pem = public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            vals["public_key_pem"] = canonical_pem.decode()
            vals["fingerprint"] = hashlib.sha256(canonical_pem).hexdigest()
            values_list.append(vals)
        return super().create(values_list)

    def write(self, vals):
        self._check_manager()
        if "fingerprint" in vals:
            raise ValidationError(
                _("The trust key fingerprint is calculated automatically.")
            )
        if "public_key_pem" in vals or "algorithm" in vals:
            raise UserError(
                _("Trust key material is immutable; create a new validity record.")
            )
        if set(vals) - {"name", "valid_to", "source_url"}:
            raise UserError(_("SII trust key identity and start date are immutable."))
        return super().write(vals)

    def unlink(self):  # pylint: disable=method-required-super
        raise AccessError(_("SII CAF trust keys cannot be deleted."))

    def action_verify_caf_signature(
        self, key_id, signed_data, signature, signed_at, scope="official"
    ):
        """Verify CAF DA with the SII public key identified by IDK."""
        self._check_manager()
        trust_key = self.search(
            [
                ("key_id", "=", str(key_id)),
                ("scope", "=", scope),
                ("valid_from", "<=", signed_at),
                "|",
                ("valid_to", "=", False),
                ("valid_to", ">=", signed_at),
            ],
            order="valid_from desc, id desc",
            limit=1,
        )
        if not trust_key:
            raise ValidationError(
                _("No SII trust key for IDK %(key_id)s covers CAF date %(date)s.")
                % {"key_id": key_id, "date": signed_at}
            )
        public_key = self._load_rsa_public_key(trust_key.public_key_pem)
        try:
            public_key.verify(
                signature,
                signed_data,
                padding.PKCS1v15(),
                hashes.SHA1(),
            )
        except InvalidSignature as error:
            raise ValidationError(
                _("The SII signature on the CAF is invalid.")
            ) from error
        return trust_key

    @api.model
    def _load_rsa_public_key(self, pem):
        if not pem:
            raise ValidationError(_("An SII public key is required."))
        try:
            public_key = serialization.load_pem_public_key(pem.encode())
        except (TypeError, ValueError) as error:
            raise ValidationError(_("The SII public key is not valid PEM.")) from error
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValidationError(_("The CAF trust key must be RSA."))
        return public_key

    @api.constrains("scope", "is_synthetic")
    def _check_synthetic_scope(self):
        for trust_key in self:
            if trust_key.is_synthetic and trust_key.scope != "demo":
                raise ValidationError(
                    _("Synthetic trust keys can only use the Demo scope.")
                )

    def _check_manager(self):
        if not self.env.user.has_group("l10n_cl_dte_core.group_dte_manager"):
            raise AccessError(_("Only a DTE manager can manage CAF trust keys."))
