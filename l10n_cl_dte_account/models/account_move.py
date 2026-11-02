import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.l10n_cl_dte_signing.services.signature_service import SignatureService
from odoo.addons.l10n_cl_dte_xml.services.invoice_snapshot import InvoiceSnapshotService
from odoo.addons.l10n_cl_dte_xml.services.xml_composer import DteXmlComposer


class AccountMove(models.Model):
    _inherit = "account.move"

    dte_document_ids = fields.One2many(
        "l10n_cl.electronic.document", "source_move_id", string="Electronic Documents"
    )
    dte_document_type_code = fields.Char(
        related="l10n_latam_document_type_id.code",
        string="DTE Document Type Code",
    )

    def issue_dte(self):
        """Issue the selected Chilean DTE through the complete lifecycle."""
        self.ensure_one()
        if not self.env.user.has_group("l10n_cl_dte_core.group_dte_user"):
            raise AccessError(_("Only a DTE user can issue electronic documents."))
        if self.state != "posted" or self.move_type != "out_invoice":
            raise UserError(_("Only posted customer invoices can issue a DTE."))
        if not self.l10n_latam_document_type_id:
            raise UserError(_("Select a Chilean DTE document type before issuing."))
        document_code = self.l10n_latam_document_type_id.code
        if document_code not in InvoiceSnapshotService.SUPPORTED_DOCUMENT_CODES:
            raise UserError(
                _("DTE document type %(code)s is not supported by this issuance flow.")
                % {"code": document_code}
            )
        document_model = self.env["l10n_cl.electronic.document"]
        environment = self.company_id.dte_sii_environment
        source_key = f"account.move:{self.id}:type-{document_code}"
        document = document_model.search(
            [("company_id", "=", self.company_id.id), ("source_key", "=", source_key)],
            limit=1,
        )
        if document:
            if document.preparation_state != "queued":
                raise UserError(
                    _(
                        "A DTE already exists for this invoice and is not ready "
                        "to resend."
                    )
                )
            submission = self.env["l10n_cl.electronic.submission"].search(
                [("document_id", "=", document.id)], limit=1
            )
            if submission:
                submission.action_enqueue_submission()
                return document
            raise UserError(_("The existing DTE has no submission record."))

        InvoiceSnapshotService().validate_invoice_source(self, document_code)
        caf = self._select_dte_caf(environment, document_code)
        document = document_model.create(
            {
                "name": self.name or self.display_name,
                "company_id": self.company_id.id,
                "document_code": document_code,
                "sii_environment": environment,
                "source_key": source_key,
                "source_move_id": self.id,
            }
        )
        folio = caf.action_reserve_folio(document, f"{source_key}:folio")
        snapshot = InvoiceSnapshotService().capture_invoice(
            self, caf, folio.number, document_code
        )
        snapshot_bytes = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("UTF-8")
        snapshot_artifact = self.env["l10n_cl.electronic.artifact"].create(
            {
                "document_id": document.id,
                "role": "source_snapshot",
                "content": base64.b64encode(snapshot_bytes),
                "mimetype": "application/json",
                "encoding": "UTF-8",
                "producer_version": "l10n_cl_dte_xml/18.0",
            }
        )
        document.action_record_source_snapshot(snapshot_artifact.id)
        ted = DteXmlComposer().compose_ted(snapshot, caf)
        snapshot["ted_xml"] = ted
        unsigned_xml = DteXmlComposer().compose_unsigned_document(snapshot)
        unsigned_artifact = self._create_dte_artifact(
            document, "unsigned_xml", unsigned_xml
        )
        document.action_record_transition(
            "prepared", "dte_xml_prepared", artifact_id=unsigned_artifact.id
        )
        signed_xml = SignatureService().sign_document(
            self.company_id, document.sii_environment, unsigned_xml
        )
        DteXmlComposer().validate_document(signed_xml)
        signed_artifact = self._create_dte_artifact(document, "signed_xml", signed_xml)
        document.action_record_transition(
            "signed", "dte_xml_signed", artifact_id=signed_artifact.id
        )
        request_artifact = self._create_dte_artifact(
            document, "sii_request", signed_xml
        )
        document.action_record_transition(
            "queued", "dte_submission_queued", artifact_id=request_artifact.id
        )
        submission = self.env["l10n_cl.electronic.submission"].create(
            {
                "document_id": document.id,
                "environment": document.sii_environment,
                "demo_scenario": (
                    self.env.context.get("dte_demo_scenario", "accepted")
                    if document.sii_environment == "demo"
                    else "accepted"
                ),
                "idempotency_key": f"{source_key}:submission",
            }
        )
        folio.action_consume()
        submission.action_enqueue_submission()
        return document

    @api.onchange("l10n_latam_document_type_id")
    def _onchange_l10n_latam_document_type_id(self):
        result = super()._onchange_l10n_latam_document_type_id()
        for move in self.filtered(
            lambda item: (
                item.state == "draft"
                and item.posted_before
                and not item.dte_document_ids
            )
        ):
            move.l10n_latam_document_number = False
            move.name = False
            move._compute_name()
        return result

    def _select_dte_caf(self, environment, document_code):
        self.ensure_one()
        selected_id = self.env.context.get("dte_caf_authorization_id")
        domain = [
            ("company_id", "=", self.company_id.id),
            ("document_code", "=", document_code),
            ("sii_environment", "=", environment),
            ("state", "=", "validated"),
            "|",
            ("date_to", "=", False),
            ("date_to", ">=", fields.Date.context_today(self)),
        ]
        if selected_id:
            domain.append(("id", "=", selected_id))
        authorizations = self.env["l10n_cl.caf.authorization"].search(domain)
        if len(authorizations) != 1:
            raise UserError(
                _(
                    "Select exactly one current validated CAF for DTE type "
                    "%(code)s before issuance."
                )
                % {"code": document_code}
            )
        authorizations._check_caf_integrity()
        return authorizations

    def _create_dte_artifact(self, document, role, xml_bytes):
        return self.env["l10n_cl.electronic.artifact"].create(
            {
                "document_id": document.id,
                "role": role,
                "content": base64.b64encode(xml_bytes),
                "mimetype": "application/xml",
                "encoding": "ISO-8859-1",
                "producer_version": "l10n_cl_dte_account/18.0",
            }
        )
