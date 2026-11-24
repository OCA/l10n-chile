# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError

from .common import DteTestCase


class TestElectronicEvent(DteTestCase):
    def test_event_records_actor(self):
        document = self.create_document()
        caf = self.create_artifact(document, "caf_source")

        document.action_record_transition(
            "authorized", "test_actor_recorded", artifact_id=caf.id
        )

        event = document.event_ids.filtered(
            lambda item: item.event_code == "test_actor_recorded"
        )
        self.assertEqual(event.create_uid, self.dte_manager)
        self.assertEqual(event.document_id, document)

    def test_unauthorized_event_append_denied(self):
        with self.assertRaises(AccessError):
            self.env["l10n_cl.electronic.event"].with_user(self.dte_user).create(
                {
                    "document_id": 1,
                    "event_code": "fabricated_event",
                    "state_domain": "preparation",
                }
            )
