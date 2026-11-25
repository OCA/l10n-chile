# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
from unittest.mock import patch

import psycopg2

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user

from odoo.addons.l10n_cl_dte_base.tests.common import DteTestCase


class TestCafRegistration(DteTestCase):
    def _caf_model(self):
        return self.env["l10n_cl.caf.authorization"].with_user(self.dte_manager)

    def _values(self, **overrides):
        return {
            "name": "Synthetic draft CAF",
            "company_id": self.company.id,
            "document_code": "33",
            "issuer_vat": "12345678-5",
            "folio_start": 1,
            "folio_end": 10,
            "date_from": fields.Date.today(),
            "caf_file": base64.b64encode(b"synthetic registration payload"),
            **overrides,
        }

    def test_register_and_update_draft(self):
        model = self._caf_model()
        caf = model.with_context(default_state="draft").create(self._values())
        self.assertEqual(caf.state, "draft")
        self.assertEqual(caf.sii_environment, self.company.dte_sii_environment)
        self.assertEqual(
            caf.caf_digest,
            hashlib.sha256(b"synthetic registration payload").hexdigest(),
        )
        caf._check_caf_integrity()
        self.company.dte_sii_environment = "certification"
        self.assertEqual(caf.sii_environment, "demo")
        caf.write({"caf_file": base64.b64encode(b"replacement")})
        self.assertEqual(caf.caf_digest, hashlib.sha256(b"replacement").hexdigest())
        caf._check_caf_integrity()
        with self.assertRaises(ValidationError):
            caf._check_caf_integrity(b"tampered")
        with self.assertRaises(AccessError):
            caf.copy()
        with self.assertRaises(AccessError):
            caf.unlink()
        for key, value in (
            ("state", "validated"),
            ("caf_digest", "forged"),
            ("is_synthetic", True),
        ):
            with self.assertRaises(UserError):
                caf.write({key: value})

    def test_invalid_registration_rejected(self):
        model = self._caf_model()
        for values in (
            {"caf_file": False},
            {"caf_file": 42},
            {"caf_file": b"%%%"},
            {"caf_file": base64.b64encode(b"x" * (1024 * 1024 + 3))},
            {"caf_file": base64.b64encode(b"x" * (1024 * 1024 + 1))},
            {"state": "validated"},
            {"company_id": 2147483647},
            {"folio_start": 0},
            {"folio_end": 0},
            {"date_from": "2026-02-01", "date_to": "2026-01-01"},
            {"sii_environment": "production", "is_synthetic": True},
        ):
            with self.subTest(keys=list(values)), self.assertRaises(ValidationError):
                with self.env.cr.savepoint():
                    model.create(self._values(**values))
        self.assertFalse(model.search_count([("name", "=", "Synthetic draft CAF")]))

    def test_duplicate_digest_rejected(self):
        model = self._caf_model()
        caf = model.create(self._values())
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            model.create(self._values(name="Duplicate"))
        other = model.create(
            self._values(name="Another", caf_file=base64.b64encode(b"another"))
        )
        with (
            patch("odoo.sql_db._logger.error"),
            self.assertRaises(psycopg2.IntegrityError),
            self.env.cr.savepoint(),
        ):
            self.env.cr.execute(
                "UPDATE l10n_cl_caf_authorization SET caf_digest = %s WHERE id = %s",
                [caf.caf_digest, other.id],
            )

    def test_branch_registration_uses_branch_environment(self):
        branch = self.env["res.company"].create(
            {
                "name": "CAF test branch",
                "parent_id": self.company.id,
                "dte_sii_environment": "certification",
            }
        )
        self.dte_manager.sudo().write({"company_ids": [(4, branch.id)]})
        model = self._caf_model().with_company(branch)
        values = self._values()
        values.pop("company_id")
        caf = model.create(values)
        self.assertEqual(caf.company_id, branch)
        self.assertEqual(caf.sii_environment, "certification")
        parent = model.with_context(
            allowed_company_ids=[branch.id, self.company.id]
        ).create(self._values(name="Parent CAF", caf_file=base64.b64encode(b"parent")))
        self.assertEqual(parent.company_id, self.company)
        self.assertEqual(parent.sii_environment, self.company.dte_sii_environment)
        branch_manager = new_test_user(
            self.env,
            login="branch-caf-manager",
            groups="base.group_user,l10n_cl_dte_base.group_dte_manager",
            company_id=branch.id,
            company_ids=[(6, 0, [branch.id])],
        )
        restricted = model.with_user(branch_manager).with_context(
            allowed_company_ids=[branch.id]
        )
        self.assertTrue(restricted.browse(caf.id).name)
        self.assertFalse(restricted.search([("id", "=", parent.id)]))

    def test_access_and_company_isolation(self):
        model = self._caf_model()
        caf = model.create(self._values())
        reader = model.with_user(self.dte_user)
        self.assertTrue(reader.browse(caf.id).name)
        with self.assertRaises(AccessError):
            reader.browse(caf.id).read(["caf_file"])
        with self.assertRaises(AccessError):
            reader.create(self._values())
        with self.assertRaises(AccessError):
            reader.browse(caf.id).write({"name": "Unauthorized"})
        other = self.env["res.company"].create({"name": "Other CAF company"})
        outsider = new_test_user(
            self.env,
            login="other-caf-company-user",
            groups="base.group_user,l10n_cl_dte_base.group_dte_manager",
            company_id=other.id,
            company_ids=[(6, 0, [other.id])],
        )
        external = model.with_user(outsider).with_company(other)
        self.assertFalse(external.search([("id", "=", caf.id)]))
        with self.assertRaises(AccessError):
            external.browse(caf.id).check_access("read")
        with self.assertRaises(AccessError):
            external.browse(caf.id).write({"name": "Unauthorized"})
