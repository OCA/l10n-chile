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

    def test_state_transition_records_event(self):
        document = self.create_document()
        caf = self.create_artifact(document, "caf_source")

        document.action_record_transition(
            "authorized", "test_caf_validated", artifact_id=caf.id
        )

        self.assertEqual(document.preparation_state, "authorized")
        event = document.event_ids.filtered(
            lambda item: item.event_code == "test_caf_validated"
        )
        self.assertEqual(len(event), 1)
        self.assertEqual(event.create_uid, self.dte_manager)

    def test_forbidden_transition_preserves_state(self):
        document = self.create_document()

        with self.assertRaises(ValidationError):
            document.action_record_transition("signed", "invalid_transition")

        self.assertEqual(document.preparation_state, "draft")
        self.assertFalse(document.folio)

    def test_invalid_audit_event_rolls_back_state(self):
        document = self.create_document()
        caf = self.create_artifact(document, "caf_source")
        with self.assertRaises(ValidationError):
            document.action_record_transition(
                "authorized", "Invalid Event", artifact_id=caf.id
            )
        self.assertEqual(document.preparation_state, "draft")
        self.assertEqual(document.event_ids.mapped("event_code"), ["document_created"])

    def test_preparation_and_fiscal_lifecycle(self):
        document = self.create_document()
        caf = self.create_artifact(document, "caf_source")
        document.action_record_transition(
            "authorized", "caf_validated", artifact_id=caf.id
        )
        with self.assertRaises(ValidationError):
            document.action_record_transition(
                "numbered", "folio_reserved", folio_number=True
            )
        document.action_record_transition("numbered", "folio_reserved", folio_number=42)
        unsigned = self.create_artifact(document, "unsigned_xml")
        with self.assertRaises(ValidationError):
            document.action_record_transition(
                "prepared", "xml_prepared", artifact_id=unsigned.id
            )
        snapshot = self.create_artifact(document, "source_snapshot")
        with self.assertRaises(ValidationError):
            document.action_record_source_snapshot(caf.id)
        document.action_record_source_snapshot(snapshot.id)
        document.action_record_source_snapshot(snapshot.id)
        with self.assertRaises(ValidationError):
            document.action_record_source_snapshot(
                self.create_artifact(document, "source_snapshot", b"replacement").id
            )
        self.assertEqual(document.payload_digest, snapshot.sha256)
        self.assertEqual(
            len(
                document.event_ids.filtered(
                    lambda e: e.event_code == "source_snapshot_recorded"
                )
            ),
            1,
        )
        for state, role in (
            ("prepared", "unsigned_xml"),
            ("signed", "signed_xml"),
            ("queued", "sii_request"),
        ):
            evidence = (
                unsigned
                if state == "prepared"
                else self.create_artifact(document, role)
            )
            document.action_record_transition(
                state, f"dte_{state}", artifact_id=evidence.id
            )
        with self.assertRaises(ValidationError):
            document.action_record_transition("outcome_unknown", "remote_uncertain")
        document.action_record_transition(
            "outcome_unknown", "remote_uncertain", correlation_key="synthetic-request"
        )
        receipt = self.create_artifact(document, "sii_response")
        document.action_record_transition(
            "submitted", "sii_received", artifact_id=receipt.id
        )
        status = self.create_artifact(document, "status_response")
        document.action_record_transition(
            "accepted", "sii_accepted", artifact_id=status.id
        )
        self.assertEqual(document.folio, 42)
        self.assertEqual(document.preparation_state, "queued")
        self.assertEqual(document.fiscal_state, "accepted")
        event = document.event_ids.filtered(lambda e: e.event_code == "sii_accepted")
        self.assertEqual(event.from_state, "submitted")
        self.assertEqual(event.artifact_id, status)
        with self.assertRaises(AccessError):
            event.sudo().write({"message": "modified audit"})
        with self.assertRaises(AccessError):
            event.sudo().unlink()

    def test_transition_rejects_invalid_inputs(self):
        document = self.create_document()
        other_caf = self.create_artifact(self.create_document(), "caf_source")
        caf = self.create_artifact(document, "caf_source")
        for state, kwargs in (
            (False, {}),
            ("unsupported", {}),
            ("authorized", {}),
            ("authorized", {"artifact_id": other_caf.id}),
            ("authorized", {"artifact_id": caf.id, "folio_number": 1}),
            ("authorized", {"message": "x" * 4001}),
            ("authorized", {"correlation_key": "x" * 257}),
        ):
            with (
                self.subTest(state=state, keys=tuple(kwargs)),
                self.assertRaises(ValidationError),
            ):
                document.action_record_transition(state, "invalid_input", **kwargs)
        self.assertEqual(document.preparation_state, "draft")

    def test_fiscal_transition_requires_queued_document(self):
        document = self.create_document()
        receipt = self.create_artifact(document, "sii_response")
        with self.assertRaisesRegex(ValidationError, "queued"):
            document.action_record_transition(
                "submitted", "sii_response_received", artifact_id=receipt.id
            )
        self.assertEqual(document.fiscal_state, "unknown")
        self.assertEqual(document.event_ids.mapped("event_code"), ["document_created"])
