# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import binascii
import hashlib
import re
import xml.etree.ElementTree as ElementTree
from datetime import date

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_MAX_CAF_BYTES = 1024 * 1024
_CAF_SIGNED_DATA_WHITESPACE = re.compile(rb">[\r\n\t ]+<")


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
        groups="l10n_cl_dte_core.group_dte_manager",
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
        groups="l10n_cl_dte_core.group_dte_manager",
    )
    caf_filename = fields.Char(groups="l10n_cl_dte_core.group_dte_manager")
    caf_digest = fields.Char(required=True, index=True, copy=False, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validated", "Validated"),
            ("exhausted", "Exhausted"),
            ("revoked", "Revoked"),
        ],
        default="draft",
        required=True,
        index=True,
        copy=False,
    )
    validated_at = fields.Datetime(readonly=True, copy=False)
    validated_by = fields.Many2one("res.users", readonly=True, copy=False)
    folio_ids = fields.One2many("l10n_cl.caf.folio", "authorization_id")

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager()
        normalized_vals_list = []
        for vals in vals_list:
            vals = vals.copy()
            company = self.env["res.company"].browse(
                vals.get("company_id") or self.env.company.id
            )
            vals.setdefault("sii_environment", company.dte_sii_environment)
            content = self._decode_content(vals.get("caf_file"))
            if vals.get("state", "draft") != "draft":
                raise ValidationError(_("A CAF must be created in draft state."))
            vals["state"] = "draft"
            vals["caf_digest"] = hashlib.sha256(content).hexdigest()
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    def write(self, vals):
        self._check_manager()
        if {
            "state",
            "caf_digest",
            "validated_at",
            "validated_by",
            "is_synthetic",
        }.intersection(vals):
            raise UserError(
                _("CAF state and digest can only change through validated actions.")
            )
        for authorization in self:
            if authorization.state != "draft":
                raise UserError(_("A validated CAF is immutable."))
        values = vals.copy()
        if "caf_file" in values:
            values["caf_digest"] = hashlib.sha256(
                self._decode_content(values["caf_file"])
            ).hexdigest()
        return super().write(values)

    def unlink(self):  # pylint: disable=method-required-super
        raise AccessError(_("CAF authorizations cannot be deleted."))

    def action_validate_authorization(self):
        """Verify CAF structure, metadata, SII signature, and key pair."""
        self.ensure_one()
        self._check_manager()
        if self.state == "validated":
            return True
        if self.state != "draft":
            raise UserError(_("Only a draft CAF can be validated."))
        metadata = self._parse_and_verify_caf()
        today = fields.Date.context_today(self)
        if metadata["date_from"] > today:
            raise ValidationError(_("The CAF authorization date is in the future."))
        if self.date_to and self.date_to < today:
            raise ValidationError(_("The CAF has expired."))
        self._check_metadata_matches(metadata)
        with self.env.cr.savepoint():
            self._write_internal(
                {
                    "state": "validated",
                    "validated_at": fields.Datetime.now(),
                    "validated_by": self.env.uid,
                }
            )
        return True

    def action_revoke_authorization(self):
        self.ensure_one()
        self._check_manager()
        if self.state not in {"validated", "exhausted"}:
            raise UserError(_("Only a validated CAF can be revoked."))
        with self.env.cr.savepoint():
            self._write_internal({"state": "revoked"})
        return True

    def _write_internal(self, values):
        """Persist protected lifecycle fields from validated internal actions."""
        return super().write(values)

    def _parse_and_verify_caf(self):
        self.ensure_one()
        content = self._decode_content(self.caf_file)
        self._check_caf_integrity(content)
        if len(content) > _MAX_CAF_BYTES:
            raise ValidationError(_("The CAF file is larger than 1 MiB."))
        upper_content = content.upper()
        if b"<!DOCTYPE" in upper_content or b"<!ENTITY" in upper_content:
            raise ValidationError(
                _("DTD and entity declarations are not allowed in CAF.")
            )
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as error:
            raise ValidationError(_("The CAF file is not well-formed XML.")) from error
        if root.tag != "AUTORIZACION":
            raise ValidationError(_("The CAF root element must be AUTORIZACION."))
        caf = root.find("CAF")
        data = caf.find("DA") if caf is not None else None
        signature = caf.find("FRMA") if caf is not None else None
        if caf is None or data is None or signature is None:
            raise ValidationError(_("The CAF, DA, or FRMA section is missing."))
        required = {
            "issuer_vat": data.findtext("RE"),
            "document_code": data.findtext("TD"),
            "folio_start": data.findtext("RNG/D"),
            "folio_end": data.findtext("RNG/H"),
            "date_from": data.findtext("FA"),
            "key_id": data.findtext("IDK"),
            "modulus": data.findtext("RSAPK/M"),
            "exponent": data.findtext("RSAPK/E"),
        }
        if any(not (value or "").strip() for value in required.values()):
            raise ValidationError(_("The CAF is missing required DA values."))
        private_key_text = root.findtext("RSASK")
        public_key_text = root.findtext("RSAPUBK")
        if not private_key_text or not public_key_text:
            raise ValidationError(_("The CAF must include its RSA key pair."))
        signature_algorithm = signature.get("algoritmo")
        if signature_algorithm != "SHA1withRSA":
            raise ValidationError(
                _("Unsupported CAF signature algorithm: %s") % signature_algorithm
            )
        try:
            signature_bytes = base64.b64decode(signature.text or "", validate=True)
            modulus_bytes = base64.b64decode(required["modulus"], validate=True)
            exponent_bytes = base64.b64decode(required["exponent"], validate=True)
            private_key = serialization.load_pem_private_key(
                private_key_text.encode(), password=None
            )
            public_key = serialization.load_pem_public_key(public_key_text.encode())
        except (binascii.Error, TypeError, ValueError) as error:
            raise ValidationError(
                _("The CAF contains invalid encoded key material.")
            ) from error
        if not isinstance(private_key, rsa.RSAPrivateKey) or not isinstance(
            public_key, rsa.RSAPublicKey
        ):
            raise ValidationError(_("Only RSA CAF key pairs are supported."))
        private_public_numbers = private_key.public_key().public_numbers()
        public_numbers = public_key.public_numbers()
        caf_numbers = (
            int.from_bytes(modulus_bytes, "big"),
            int.from_bytes(exponent_bytes, "big"),
        )
        if (public_numbers.n, public_numbers.e) != (
            private_public_numbers.n,
            private_public_numbers.e,
        ) or caf_numbers != (public_numbers.n, public_numbers.e):
            raise ValidationError(_("The CAF RSA key pair does not match its DA."))
        try:
            signed_data = ElementTree.tostring(
                data, encoding="ISO-8859-1", short_empty_elements=True
            )
        except (LookupError, UnicodeEncodeError) as error:
            raise ValidationError(
                _("The CAF DA cannot be encoded as ISO-8859-1.")
            ) from error
        signed_data = _CAF_SIGNED_DATA_WHITESPACE.sub(b"><", signed_data)
        authorization_date = self._parse_date(required["date_from"])
        self.env["l10n_cl.caf.trust.key"].action_verify_caf_signature(
            required["key_id"].strip(),
            signed_data,
            signature_bytes,
            authorization_date,
            "demo" if self.sii_environment == "demo" else "official",
        )
        return {
            "issuer_vat": self._normalize_vat(required["issuer_vat"]),
            "document_code": required["document_code"].strip(),
            "folio_start": self._parse_positive_int(required["folio_start"]),
            "folio_end": self._parse_positive_int(required["folio_end"]),
            "date_from": authorization_date,
        }

    def _check_caf_integrity(self, content=None):
        self.ensure_one()
        if content is None:
            self.invalidate_recordset(["caf_file"])
            content = self._decode_content(self.caf_file)
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != self.caf_digest:
            raise ValidationError(
                _("The stored CAF content does not match its registered SHA-256.")
            )

    def _check_metadata_matches(self, metadata):
        self.ensure_one()
        company_vat = self._normalize_vat(self.company_id.partner_id.vat)
        issuer_vat = metadata["issuer_vat"]
        if not self._is_valid_vat(issuer_vat) or issuer_vat != company_vat:
            raise ValidationError(_("The CAF issuer RUT does not match the company."))
        if self._normalize_vat(self.issuer_vat) != issuer_vat:
            raise ValidationError(_("The CAF issuer RUT does not match its DA."))
        if self.document_code != metadata["document_code"]:
            raise ValidationError(_("The CAF document type does not match its DA."))
        if not self.document_code.isdigit() or int(self.document_code) <= 0:
            raise ValidationError(
                _("The CAF document type must be a positive numeric code.")
            )
        if (
            self.folio_start != metadata["folio_start"]
            or self.folio_end != metadata["folio_end"]
        ):
            raise ValidationError(_("The CAF folio range does not match its DA."))
        if self.folio_start <= 0 or self.folio_end < self.folio_start:
            raise ValidationError(_("The CAF folio range is invalid."))
        if self.date_from != metadata["date_from"]:
            raise ValidationError(
                _("The CAF authorization date does not match its DA.")
            )

    @api.constrains("sii_environment", "is_synthetic")
    def _check_synthetic_environment(self):
        for authorization in self:
            if authorization.is_synthetic and authorization.sii_environment != "demo":
                raise ValidationError(
                    _("Synthetic CAF authorizations can only use Demo environment.")
                )

    def _lock_range(self):
        self.ensure_one()
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            [f"l10n_cl_dte_caf:{self.company_id.id}:{self.document_code}"],
        )
        self.env.cr.execute(
            "SELECT id FROM l10n_cl_caf_authorization WHERE id = %s FOR UPDATE",
            [self.id],
        )
        self.invalidate_recordset(["state", "date_to"])

    @api.model
    def _decode_content(self, encoded_content):
        if not encoded_content:
            raise ValidationError(_("CAF file content is required."))
        try:
            return base64.b64decode(encoded_content, validate=True)
        except (binascii.Error, TypeError, ValueError) as error:
            raise ValidationError(
                _("CAF file content must be valid base64.")
            ) from error

    @api.model
    def _parse_positive_int(self, value):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(_("CAF folio values must be integers.")) from error
        if parsed <= 0:
            raise ValidationError(_("CAF folio values must be positive."))
        return parsed

    @api.model
    def _parse_date(self, value):
        try:
            return date.fromisoformat(value.strip())
        except (AttributeError, TypeError, ValueError) as error:
            raise ValidationError(
                _("The CAF authorization date is invalid.")
            ) from error

    @api.model
    def _normalize_vat(self, value):
        return re.sub(r"[.\-\s]", "", (value or "").upper()).removeprefix("CL")

    @api.model
    def _is_valid_vat(self, vat):
        if len(vat) < 2 or not vat[:-1].isdigit():
            return False
        total = sum(
            int(digit) * (index % 6 + 2)
            for index, digit in enumerate(reversed(vat[:-1]))
        )
        verifier = 11 - total % 11
        expected = "0" if verifier == 11 else "K" if verifier == 10 else str(verifier)
        return vat[-1] == expected

    def _check_manager(self):
        if not self.env.user.has_group("l10n_cl_dte_core.group_dte_manager"):
            raise AccessError(_("Only a DTE manager can manage CAF authorizations."))
