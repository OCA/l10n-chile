# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import AccessError, UserError, ValidationError

from .common import DteTestCase, digest


class TestSignatureRevisions(DteTestCase):
    def _signed_document(self):
        document = self.create_document()
        caf = self.create_artifact(document, "caf_source")
        document.action_record_transition("authorized", "test_caf", artifact_id=caf.id)
        document.action_record_transition(
            "numbered", "test_folio", folio_number=document.id
        )
        snapshot = self.create_artifact(document, "source_snapshot", b"{}")
        document.action_record_source_snapshot(snapshot.id)
        unsigned = self.create_artifact(document, "unsigned_xml", b"<DTE/>")
        document.action_record_transition(
            "prepared", "test_xml", artifact_id=unsigned.id
        )
        signed = self.create_artifact(document, "signed_xml", b"synthetic signature v1")
        document.action_record_transition(
            "signed", "test_signature", artifact_id=signed.id
        )
        return document, signed

    def _revise(self, previous, payload=b"synthetic signature v2"):
        return previous.env["l10n_cl.electronic.artifact"]._create_signature_revision(
            previous, payload, "tests/18.0"
        )

    def test_revision_chain_retains_every_previous_byte_and_fiscal_identity(self):
        document, original = self._signed_document()
        before = (
            original.content,
            original.sha256,
            document.folio,
            document.payload_digest,
        )
        second = self._revise(original)
        third = self._revise(second, b"synthetic signature v3")
        self.assertEqual(document._get_signed_artifact(), third)
        self.assertEqual(document.signature_revision, 2)
        self.assertEqual(third.supersedes_id, second)
        self.assertEqual(second.supersedes_id, original)
        self.assertEqual(
            (
                original.content,
                original.sha256,
                document.folio,
                document.payload_digest,
            ),
            before,
        )
        self.assertEqual(second.sha256, digest(b"synthetic signature v2"))
        self.assertEqual(third.byte_count, len(b"synthetic signature v3"))
        self.assertEqual(document.preparation_state, "signed")
        for artifact in original | second | third:
            self.assertTrue(artifact.action_verify_integrity())
            with self.assertRaises(AccessError):
                artifact.write({"producer_version": "changed"})
            with self.assertRaises(AccessError):
                artifact.unlink()

    def test_only_the_current_signature_can_be_replaced(self):
        document, original = self._signed_document()
        current = self._revise(original)
        with self.assertRaisesRegex(ValidationError, "current signature"):
            self._revise(original)
        self.assertEqual(document._get_signed_artifact(), current)

    def test_public_creation_cannot_forge_a_successor(self):
        document, original = self._signed_document()
        with self.assertRaises(AccessError):
            original.create(
                {
                    "document_id": document.id,
                    "role": "signed_xml",
                    "supersedes_id": original.id,
                    "content": base64.b64encode(b"synthetic forged successor"),
                    "mimetype": "application/xml",
                }
            )

    def test_context_default_cannot_forge_a_successor(self):
        document, original = self._signed_document()
        with self.assertRaises(AccessError):
            original.with_context(default_supersedes_id=original.id).create(
                {
                    "document_id": document.id,
                    "role": "signed_xml",
                    "content": base64.b64encode(b"synthetic forged successor"),
                }
            )

    def test_evidence_cannot_be_copied(self):
        _document, original = self._signed_document()
        with self.assertRaises(AccessError):
            original.copy({"content": original.content})

    def test_missing_or_ambiguous_current_signature_is_rejected(self):
        document = self.create_document()
        with self.assertRaisesRegex(ValidationError, "exactly one"):
            document._get_signed_artifact()
        document, _original = self._signed_document()
        self.create_artifact(document, "signed_xml", b"synthetic unrelated signature")
        with self.assertRaisesRegex(ValidationError, "exactly one"):
            document._get_signed_artifact()

    def test_transmission_evidence_blocks_revision(self):
        for role in ["sii_request", "sii_response", "status_response"]:
            with self.subTest(role=role):
                document, original = self._signed_document()
                self.create_artifact(document, role, b"synthetic transmission evidence")
                with self.assertRaisesRegex(UserError, "transmission evidence"):
                    self._revise(original)
                self.assertEqual(document._get_signed_artifact(), original)

    def test_queue_transition_blocks_revision(self):
        document, original = self._signed_document()
        request = self.create_artifact(document, "sii_request")
        document.action_record_transition(
            "queued", "test_queued", artifact_id=request.id
        )
        with self.assertRaisesRegex(UserError, "never been queued"):
            self._revise(original)

    def test_operator_cannot_create_revision(self):
        _document, original = self._signed_document()
        with self.assertRaises(AccessError):
            self._revise(original.with_user(self.dte_user))

    def test_tampered_previous_evidence_blocks_revision(self):
        document, original = self._signed_document()
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", original._name),
                    ("res_id", "=", original.id),
                    ("res_field", "=", "content"),
                ]
            )
        )
        attachment.write({"datas": base64.b64encode(b"synthetic tampering")})
        original.invalidate_recordset(["content"])
        with self.assertRaisesRegex(ValidationError, "recorded digest"):
            self._revise(original)
        self.assertEqual(document._get_signed_artifact(), original)
