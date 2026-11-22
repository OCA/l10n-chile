# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import uuid

from odoo.tests.common import TransactionCase, new_test_user


class DteTestCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.dte_manager = new_test_user(
            cls.env,
            login="dte-test-manager",
            groups=(
                "base.group_user,base.group_partner_manager,"
                "account.group_account_invoice,l10n_cl_dte_base.group_dte_manager"
            ),
            company_id=cls.company.id,
            company_ids=[(6, 0, [cls.company.id])],
        )
        cls.dte_user = new_test_user(
            cls.env,
            login="dte-test-user",
            groups="base.group_user,l10n_cl_dte_base.group_dte_user",
            company_id=cls.company.id,
            company_ids=[(6, 0, [cls.company.id])],
        )

    def create_document(self, **values):
        vals = {
            "name": "DTE test document",
            "company_id": self.company.id,
            "sii_environment": self.company.dte_sii_environment,
            "document_code": "33",
            "source_key": f"test-source-{uuid.uuid4().hex}",
        }
        vals.update(values)
        if vals.get("source_key") is None:
            vals["source_key"] = f"test-source-{uuid.uuid4().hex}"
        return (
            self.env["l10n_cl.electronic.document"]
            .with_user(self.dte_manager)
            .with_company(self.company)
            .create(vals)
        )

    def create_artifact(self, document, role, payload=b"synthetic evidence"):
        return (
            self.env["l10n_cl.electronic.artifact"]
            .with_user(self.dte_manager)
            .create(
                {
                    "document_id": document.id,
                    "role": role,
                    "content": base64.b64encode(payload),
                    "mimetype": "application/xml",
                }
            )
        )


def digest(payload):
    return hashlib.sha256(payload).hexdigest()
