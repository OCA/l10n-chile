# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import re
import secrets
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_SYNTHETIC_CAF_DOCUMENT_CODES = (
    "33",
    "34",
    "39",
    "41",
    "43",
    "52",
    "56",
    "61",
    "103",
    "110",
    "111",
    "112",
)


class DteDemoSetupWizard(models.TransientModel):
    _name = "l10n_cl.dte.demo.setup.wizard"
    _description = "Synthetic DTE Demo Configuration Wizard"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    allowed_document_type_ids = fields.Many2many(
        "l10n_latam.document.type",
        compute="_compute_allowed_document_type_ids",
    )
    document_type_ids = fields.Many2many(
        "l10n_latam.document.type",
        string="DTE types for synthetic CAFs",
        required=True,
        domain="[('id', 'in', allowed_document_type_ids)]",
        help=(
            "Select the Chilean DTE types for which Demo CAF authorizations "
            "are generated."
        ),
        default=lambda self: self._default_document_type_ids(),
    )
    confirm_synthetic_data = fields.Boolean(
        string="I understand these are synthetic Demo-only fiscal materials",
        required=True,
        default=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager()
        return super().create(vals_list)

    def action_create_configuration(self):
        self.ensure_one()
        self._check_manager()
        company = self.company_id
        if not self.confirm_synthetic_data:
            raise ValidationError(
                _("Confirm that the generated fiscal materials are synthetic.")
            )
        if company.dte_sii_environment != "demo":
            raise UserError(_("Set the company's DTE SII environment to Demo first."))
        if not self.document_type_ids:
            raise ValidationError(
                _("Select at least one Chilean DTE type for synthetic CAF creation.")
            )

        selected_types = self.document_type_ids.sorted("code")
        allowed_types = self.allowed_document_type_ids
        if selected_types - allowed_types:
            raise ValidationError(
                _("Only supported Chilean DTE types can receive a synthetic CAF.")
            )

        caf_model = self.env["l10n_cl.caf.authorization"]
        profile_model = self.env["l10n_cl.dte.signing.profile"]
        existing_profiles = profile_model.search(
            [
                ("company_id", "=", company.id),
                ("sii_environment", "=", "demo"),
            ]
        )
        if len(existing_profiles) > 1 or (
            existing_profiles
            and (not existing_profiles.is_synthetic or not existing_profiles.active)
        ):
            raise UserError(
                _(
                    "An existing Demo signing profile is not synthetic and active. "
                    "Review it before creating synthetic material; it was not changed."
                )
            )

        cafs_to_create = self.env["l10n_latam.document.type"]
        existing_cafs = caf_model.search(
            [
                ("company_id", "=", company.id),
                ("document_code", "in", selected_types.mapped("code")),
                ("sii_environment", "=", "demo"),
            ]
        )
        for document_type in selected_types:
            matching_cafs = existing_cafs.filtered(
                lambda caf, code=document_type.code: caf.document_code == code
            )
            if not matching_cafs:
                cafs_to_create |= document_type
                continue
            if (
                len(matching_cafs) != 1
                or not matching_cafs.is_synthetic
                or matching_cafs.state != "validated"
            ):
                raise UserError(
                    _(
                        "A Demo CAF for type %(code)s already exists and is not a "
                        "single validated synthetic CAF. Review it before continuing."
                    )
                    % {"code": document_type.code}
                )

        today = fields.Date.context_today(self)
        created_codes = []
        key_id = False
        if cafs_to_create:
            issuer_vat = self._get_company_vat(company)
            trust_private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048
            )
            key_id = self._new_trust_key_id()
            trust_public_pem = (
                trust_private_key.public_key()
                .public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                .decode("ascii")
            )
            self.env["l10n_cl.caf.trust.key"].create(
                {
                    "name": _("SYNTHETIC DEMO trust key for %s") % company.display_name,
                    "key_id": key_id,
                    "scope": "demo",
                    "is_synthetic": True,
                    "algorithm": "SHA1withRSA",
                    "public_key_pem": trust_public_pem,
                    "valid_from": today,
                    "source_url": "urn:oca:l10n-chile:synthetic-demo-configuration",
                }
            )
            for document_type in cafs_to_create:
                caf_private_key = rsa.generate_private_key(
                    public_exponent=65537, key_size=2048
                )
                folio_start = 900000 + company.id * 1000 + int(document_type.code) * 100
                self._create_synthetic_caf(
                    company,
                    issuer_vat,
                    key_id,
                    trust_private_key,
                    caf_private_key,
                    today,
                    folio_start,
                    document_type.code,
                )
                created_codes.append(document_type.code)

        if not existing_profiles:
            certificate = self._create_synthetic_certificate(company)
            profile_model.create(
                {
                    "name": _("SYNTHETIC DEMO signing profile for %s")
                    % company.display_name,
                    "company_id": company.id,
                    "sii_environment": "demo",
                    "certificate_id": certificate.id,
                    "is_synthetic": True,
                }
            )
        if not created_codes:
            return self._notification(
                _("All selected Demo CAFs and the signing profile already exist.")
            )
        return self._notification(
            _(
                "Synthetic Demo configuration created: trust key %(key)s, "
                "validated CAF types %(codes)s, and signing profile for %(company)s."
            )
            % {
                "key": key_id,
                "codes": ", ".join(created_codes),
                "company": company.display_name,
            }
        )

    @api.depends("company_id")
    def _compute_allowed_document_type_ids(self):
        for wizard in self:
            country = wizard.company_id.country_id
            wizard.allowed_document_type_ids = (
                self.env["l10n_latam.document.type"].search(
                    [
                        ("country_id", "=", country.id),
                        ("code", "in", _SYNTHETIC_CAF_DOCUMENT_CODES),
                    ]
                )
                if country
                else False
            )

    @api.model
    def _default_document_type_ids(self):
        country = self.env.company.country_id
        if not country:
            return False
        return self.env["l10n_latam.document.type"].search(
            [
                ("country_id", "=", country.id),
                ("code", "=", "33"),
            ],
            limit=1,
        )

    def _create_synthetic_caf(
        self,
        company,
        issuer_vat,
        key_id,
        trust_private_key,
        caf_private_key,
        today,
        folio_start,
        document_code,
    ):
        public_numbers = caf_private_key.public_key().public_numbers()
        data = ElementTree.Element("DA")
        for tag, value in (
            ("RE", issuer_vat),
            ("RS", company.name),
            ("TD", document_code),
        ):
            ElementTree.SubElement(data, tag).text = value
        folio_range = ElementTree.SubElement(data, "RNG")
        ElementTree.SubElement(folio_range, "D").text = str(folio_start)
        ElementTree.SubElement(folio_range, "H").text = str(folio_start + 99)
        ElementTree.SubElement(data, "FA").text = today.isoformat()
        rsa_public = ElementTree.SubElement(data, "RSAPK")
        ElementTree.SubElement(data, "IDK").text = key_id
        ElementTree.SubElement(rsa_public, "M").text = base64.b64encode(
            public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
        ).decode("ascii")
        ElementTree.SubElement(rsa_public, "E").text = base64.b64encode(
            public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
        ).decode("ascii")
        signed_data = ElementTree.tostring(data, encoding="ISO-8859-1")
        signed_data = re.sub(rb">[\r\n\t ]+<", b"><", signed_data)
        signature = trust_private_key.sign(
            signed_data, padding.PKCS1v15(), hashes.SHA1()
        )

        root = ElementTree.Element("AUTORIZACION")
        caf_node = ElementTree.SubElement(root, "CAF", {"version": "1.0"})
        caf_node.append(data)
        frma = ElementTree.SubElement(caf_node, "FRMA", {"algoritmo": "SHA1withRSA"})
        frma.text = base64.b64encode(signature).decode("ascii")
        ElementTree.SubElement(root, "RSASK").text = caf_private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ).decode("ascii")
        ElementTree.SubElement(root, "RSAPUBK").text = (
            caf_private_key.public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )
        caf_content = ElementTree.tostring(root, encoding="ISO-8859-1")
        caf = self.env["l10n_cl.caf.authorization"].create(
            {
                "name": _("SYNTHETIC DEMO CAF type %(code)s for %(company)s")
                % {"code": document_code, "company": company.display_name},
                "company_id": company.id,
                "sii_environment": "demo",
                "is_synthetic": True,
                "document_code": document_code,
                "issuer_vat": issuer_vat,
                "folio_start": folio_start,
                "folio_end": folio_start + 99,
                "date_from": today,
                "caf_file": base64.b64encode(caf_content).decode("ascii"),
                "caf_filename": f"synthetic_demo_type_{document_code}.xml",
            }
        )
        caf.action_validate_authorization()
        return caf

    def _create_synthetic_certificate(self, company):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic DTE Demo Certificate")]
        )
        now = datetime.utcnow()
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=365))
            .sign(private_key, hashes.SHA256())
        )
        content = pkcs12.serialize_key_and_certificates(
            b"synthetic-demo-dte",
            private_key,
            certificate,
            None,
            serialization.NoEncryption(),
        )
        return (
            self.env["certificate.certificate"]
            .sudo()
            .create(
                {
                    "name": _("SYNTHETIC DEMO certificate for %s")
                    % company.display_name,
                    "company_id": company.id,
                    "content": base64.b64encode(content),
                }
            )
        )

    def _new_trust_key_id(self):
        key_model = self.env["l10n_cl.caf.trust.key"]
        while True:
            key_id = str(secrets.randbelow(900000) + 100000)
            if not key_model.search_count(
                [("key_id", "=", key_id), ("scope", "=", "demo")]
            ):
                return key_id

    def _get_company_vat(self, company):
        vat = (company.partner_id.vat or "").strip()
        normalized = self.env["l10n_cl.caf.authorization"]._normalize_vat(vat)
        caf_model = self.env["l10n_cl.caf.authorization"]
        if not caf_model._is_valid_vat(normalized):
            raise UserError(
                _(
                    "Set a valid Chilean company RUT before generating the synthetic "
                    "Demo CAF."
                )
            )
        return vat

    @api.model
    def _check_manager(self):
        if not self.env.user.has_group("l10n_cl_dte_core.group_dte_manager"):
            raise AccessError(_("Only a DTE manager can prepare Demo configuration."))

    def _notification(self, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("DTE Demo Configuration"),
                "message": message,
                "type": "success",
                "sticky": True,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
