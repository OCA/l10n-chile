# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import AccessError, ValidationError

from .common import DteTestCase, digest


class TestElectronicArtifact(DteTestCase):
    def test_artifact_digest_matches(self):
        payload = b"deterministic synthetic evidence"
        artifact = self.create_artifact(self.create_document(), "sii_response", payload)

        self.assertEqual(artifact.sha256, digest(payload))
        self.assertEqual(artifact.byte_count, len(payload))
        self.assertTrue(artifact.action_verify_integrity())

    def test_tampering_breaks_integrity(self):
        artifact = self.create_artifact(self.create_document(), "sii_response")
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", "l10n_cl.electronic.artifact"),
                    ("res_id", "=", artifact.id),
                    ("res_field", "=", "content"),
                ],
                limit=1,
            )
        )
        self.assertTrue(attachment, "Binary evidence should be stored as an attachment")
        attachment.write({"datas": base64.b64encode(b"tampered payload")})
        artifact.invalidate_recordset(["content"])

        with self.assertRaises(ValidationError):
            artifact.action_verify_integrity()

    def test_evidence_is_immutable(self):
        artifact = self.create_artifact(self.create_document(), "sii_response")

        with self.assertRaises(AccessError):
            artifact.write({"mimetype": "text/plain"})
        with self.assertRaises(AccessError):
            artifact.unlink()
