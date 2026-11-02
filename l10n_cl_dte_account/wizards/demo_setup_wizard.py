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


class DteDemoSetupWizard(models.TransientModel):
    _name = "l10n_cl.dte.demo.setup.wizard"
    _description = "Synthetic DTE Demo Configuration Wizard"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
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

        caf_model = self.env["l10n_cl.caf.authorization"]
        profile_model = self.env["l10n_cl.dte.signing.profile"]
        existing_cafs = caf_model.search(
            [
                ("company_id", "=", company.id),
                ("document_code", "=", "33"),
                ("sii_environment", "=", "demo"),
            ]
        )
        existing_profiles = profile_model.search(
            [
                ("company_id", "=", company.id),
                ("sii_environment", "=", "demo"),
            ]
        )
        if existing_cafs or existing_profiles:
            if (
                len(existing_cafs) == 1
                and existing_cafs.is_synthetic
                and existing_cafs.state == "validated"
                and len(existing_profiles) == 1
                and existing_profiles.is_synthetic
                and existing_profiles.active
            ):
                return self._notification(
                    _("Synthetic Demo configuration already exists; nothing changed.")
                )
            raise UserError(
                _(
                    "This company already has Demo CAF or signing configuration. "
                    "Review it before creating synthetic material; existing records "
                    "were not changed."
                )
            )

        issuer_vat = self._get_company_vat(company)
        trust_private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        caf_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_id = self._new_trust_key_id()
        today = fields.Date.context_today(self)
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
        caf_start = 900000 + company.id * 100
        caf = self._create_synthetic_caf(
            company,
            issuer_vat,
            key_id,
            trust_private_key,
            caf_private_key,
            today,
            caf_start,
        )
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
        return self._notification(
            _(
                "Synthetic Demo configuration created: trust key %(key)s, "
                "validated type-33 CAF %(caf)s, and signing profile %(profile)s."
            )
            % {"key": key_id, "caf": caf.name, "profile": company.display_name}
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
    ):
        public_numbers = caf_private_key.public_key().public_numbers()
        data = ElementTree.Element("DA")
        for tag, value in (
            ("RE", issuer_vat),
            ("RS", company.name),
            ("TD", "33"),
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
                "name": _("SYNTHETIC DEMO CAF type 33 for %s") % company.display_name,
                "company_id": company.id,
                "sii_environment": "demo",
                "is_synthetic": True,
                "document_code": "33",
                "issuer_vat": issuer_vat,
                "folio_start": folio_start,
                "folio_end": folio_start + 99,
                "date_from": today,
                "caf_file": base64.b64encode(caf_content).decode("ascii"),
                "caf_filename": "synthetic_demo_type_33.xml",
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
