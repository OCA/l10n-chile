# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user

from .common import DteTestCase


class TestElectronicDocument(DteTestCase):
    def test_document_captures_environment(self):
        document = self.create_document()
        self.assertEqual(document.sii_environment, "demo")
        self.company.dte_sii_environment = "certification"
        self.assertEqual(document.sii_environment, "demo")
        self.assertEqual(self.create_document().sii_environment, "certification")
        with self.assertRaises(ValidationError):
            self.create_document(sii_environment="demo")

    def test_identity_is_immutable(self):
        document = self.create_document()
        with self.assertRaises(UserError):
            document.write({"source_key": "other"})
        with self.assertRaises(UserError):
            document.copy()

    def test_user_cannot_create_or_read_evidence_bytes(self):
        document = self.create_document()
        artifact = self.create_artifact(document, "source_snapshot")
        self.assertEqual(document.with_user(self.dte_user).name, document.name)
        self.assertEqual(artifact.with_user(self.dte_user).role, artifact.role)
        with self.assertRaises(AccessError):
            artifact.with_user(self.dte_user).read(["content"])
        with self.assertRaises(AccessError):
            document.with_user(self.dte_user).create(
                {
                    "name": "Unauthorized",
                    "document_code": "33",
                    "source_key": "unauthorized",
                }
            )

    def test_company_record_rules_isolate_documents_and_evidence(self):
        document = self.create_document()
        artifact = self.create_artifact(document, "source_snapshot")
        other_company = self.env["res.company"].create({"name": "Other DTE company"})
        outsider = new_test_user(
            self.env,
            login="other-dte-company-user",
            groups="base.group_user,l10n_cl_dte_base.group_dte_user",
            company_id=other_company.id,
            company_ids=[(6, 0, [other_company.id])],
        )
        for record in (document, artifact):
            with self.assertRaises(AccessError):
                record.with_user(outsider).with_company(other_company).check_access(
                    "read"
                )
