# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL

_PREPARATION_TRANSITIONS = {
    "draft": {"authorized"},
    "authorized": {"numbered"},
    "numbered": {"prepared"},
    "prepared": {"signed"},
    "signed": {"queued"},
    "queued": set(),
}
_FISCAL_TRANSITIONS = {
    "unknown": {"submitted", "outcome_unknown"},
    "submitted": {"submitted", "processing", "accepted", "rejected", "outcome_unknown"},
    "processing": {"processing", "accepted", "rejected", "outcome_unknown"},
    "outcome_unknown": {
        "submitted",
        "processing",
        "accepted",
        "rejected",
        "outcome_unknown",
    },
    "accepted": {"accepted"},
    "rejected": {"rejected"},
}
_PREPARATION_ARTIFACT_ROLES = {
    "authorized": "caf_source",
    "prepared": "unsigned_xml",
    "signed": "signed_xml",
    "queued": "sii_request",
}
_FISCAL_ARTIFACT_ROLES = {
    "submitted": "sii_response",
    "processing": "status_response",
    "accepted": "status_response",
    "rejected": "status_response",
}


class ElectronicDocument(models.Model):
    _name = "l10n_cl.electronic.document"
    _description = "Chilean Electronic Tax Document"
    _order = "id desc"
    _check_company_auto = True
    _sql_constraints = [
        (
            "source_key_company_uniq",
            "unique(company_id, source_key)",
            "A source invoice can only have one electronic document per company.",
        )
    ]

    name = fields.Char(required=True, index=True, copy=False)
    company_id = fields.Many2one(
        "res.company", required=True, index=True, default=lambda self: self.env.company
    )
    sii_environment = fields.Selection(
        [
            ("demo", "Demo / Simulated"),
            ("certification", "Certification"),
            ("production", "Production"),
        ],
        required=True,
        readonly=True,
        index=True,
        copy=False,
    )
    document_code = fields.Char(required=True, index=True)
    folio = fields.Integer(readonly=True, index=True, copy=False)
    preparation_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("authorized", "CAF Authorized"),
            ("numbered", "Folio Reserved"),
            ("prepared", "XML Prepared"),
            ("signed", "Signed"),
            ("queued", "Queued"),
        ],
        required=True,
        default="draft",
        index=True,
        copy=False,
    )
    fiscal_state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("submitted", "Submitted"),
            ("processing", "Processing"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("outcome_unknown", "Outcome Unknown"),
        ],
        required=True,
        default="unknown",
        index=True,
        copy=False,
    )
    source_key = fields.Char(required=True, index=True, copy=False)
    payload_digest = fields.Char(readonly=True, index=True, copy=False)
    artifact_ids = fields.One2many(
        "l10n_cl.electronic.artifact", "document_id", string="Evidence"
    )
    event_ids = fields.One2many("l10n_cl.electronic.event", "document_id")

    def init(self):
        """Index reserved folios while ignoring the unnumbered zero value."""
        self.env.cr.execute(
            SQL(
                "CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s "
                "(company_id, document_code, folio) WHERE folio > 0",
                SQL.identifier("l10n_cl_electronic_document_folio_uniq"),
                SQL.identifier(self._table),
            )
        )

    @api.constrains("document_code", "source_key")
    def _check_document_identity(self):
        for document in self:
            if not (document.document_code or "").isdigit():
                raise ValidationError(
                    self.env._("The DTE type code must contain digits only.")
                )
            if not (document.source_key or "").strip():
                raise ValidationError(self.env._("The source key cannot be empty."))

    @api.constrains("folio", "preparation_state")
    def _check_folio_state(self):
        numbered_states = {"numbered", "prepared", "signed", "queued"}
        for document in self:
            if document.folio < 0:
                raise ValidationError(self.env._("A DTE folio cannot be negative."))
            if document.preparation_state in numbered_states and document.folio <= 0:
                raise ValidationError(
                    self.env._("A positive folio is required after the numbered state.")
                )
            if document.preparation_state not in numbered_states and document.folio:
                raise ValidationError(
                    self.env._("A folio cannot be assigned before the numbered state.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Create a new document only in its initial, unnumbered state."""
        initial_values = {
            "preparation_state": "draft",
            "fiscal_state": "unknown",
            "folio": False,
            "payload_digest": False,
        }
        normalized_vals_list = []
        for vals in vals_list:
            vals = vals.copy()
            company_id = vals.get("company_id") or self.env.company.id
            vals["company_id"] = company_id
            company = self.env["res.company"].browse(company_id).exists()
            if len(company) != 1:
                raise ValidationError(
                    self.env._("A valid company is required for a DTE.")
                )
            environment = vals.get("sii_environment") or company.dte_sii_environment
            if environment != company.dte_sii_environment:
                raise ValidationError(
                    self.env._(
                        "A new DTE must capture the company's current SII environment."
                    )
                )
            vals["sii_environment"] = environment
            if vals.get("source_key"):
                vals["source_key"] = vals["source_key"].strip()
            if vals.get("document_code"):
                vals["document_code"] = vals["document_code"].strip()
            for field_name, initial_value in initial_values.items():
                if field_name in vals and vals[field_name] not in (
                    False,
                    initial_value,
                ):
                    raise ValidationError(
                        self.env._(
                            "A DTE must be created in its initial unnumbered state."
                        )
                    )
                vals[field_name] = initial_value
            normalized_vals_list.append(vals)
        with self.env.cr.savepoint():
            documents = super().create(normalized_vals_list)
            documents._create_audit_events(
                [
                    {
                        "event_code": "document_created",
                        "state_domain": "preparation",
                        "to_state": "draft",
                    }
                ]
                * len(documents)
            )
        return documents

    def write(self, vals):
        """Keep identity and lifecycle fields behind validated actions."""
        protected_fields = {
            "name",
            "company_id",
            "sii_environment",
            "document_code",
            "folio",
            "preparation_state",
            "fiscal_state",
            "source_key",
            "payload_digest",
        }
        if protected_fields.intersection(vals):
            raise UserError(
                self.env._(
                    "DTE identity and state fields can only change through "
                    "validated actions."
                )
            )
        return super().write(vals)

    def unlink(self):  # pylint: disable=method-required-super
        raise UserError(self.env._("Electronic tax documents cannot be deleted."))

    def copy(self, default=None):  # pylint: disable=method-required-super
        raise UserError(self.env._("Electronic tax documents cannot be duplicated."))

    @api.model
    def _check_dte_manager(self, message):
        if not self.env.su and not self.env.user.has_group(
            "l10n_cl_dte_base.group_dte_manager"
        ):
            raise AccessError(message)

    def _lock_lifecycle(self):
        """Serialize updates before reading state or binding evidence."""
        self.ensure_one()
        self.flush_recordset()
        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id = %s FOR UPDATE",
                SQL.identifier(self._table),
                self.id,
            )
        )
        self.invalidate_recordset()

    def action_record_transition(
        self,
        target_state,
        event_code,
        message=None,
        correlation_key=None,
        artifact_id=False,
        folio_number=False,
    ):
        """Apply one valid lifecycle transition and persist its audit event."""
        self.ensure_one()
        self._check_dte_manager(
            self.env._("Only a DTE manager can change document state.")
        )
        self.check_access("write")
        if message and (not isinstance(message, str) or len(message) > 4000):
            raise ValidationError(
                self.env._("The event message cannot exceed 4,000 characters.")
            )
        if correlation_key and (
            not isinstance(correlation_key, str) or len(correlation_key) > 256
        ):
            raise ValidationError(
                self.env._("The correlation key cannot exceed 256 characters.")
            )
        artifact = self.env["l10n_cl.electronic.artifact"].browse(artifact_id).exists()
        if artifact_id and (len(artifact) != 1 or artifact.document_id != self):
            raise ValidationError(
                self.env._("The audit artifact must belong to the electronic document.")
            )
        self._lock_lifecycle()
        state_domain, current_state, transitions, field_name = (
            self._get_transition_details(target_state)
        )
        if target_state not in transitions[current_state]:
            raise ValidationError(
                self.env._("Transition from %(source)s to %(target)s is not allowed.")
                % {"source": current_state, "target": target_state}
            )
        self._validate_transition_evidence(
            target_state, state_domain, artifact, correlation_key
        )
        write_values = self._get_transition_write_values(
            target_state, field_name, state_domain, folio_number
        )
        previous_state = current_state
        with self.env.cr.savepoint():
            super().write(write_values)
            self._create_audit_events(
                [
                    {
                        "event_code": event_code,
                        "state_domain": state_domain,
                        "from_state": previous_state,
                        "to_state": target_state,
                        "message": message or False,
                        "correlation_key": correlation_key or False,
                        "artifact_id": artifact.id if artifact else False,
                    }
                ]
            )
        return True

    def _get_transition_details(self, target_state):
        if not isinstance(target_state, str):
            raise ValidationError(self.env._("A valid DTE state is required."))
        if target_state in _PREPARATION_TRANSITIONS:
            return (
                "preparation",
                self.preparation_state,
                _PREPARATION_TRANSITIONS,
                "preparation_state",
            )
        if target_state in _FISCAL_TRANSITIONS:
            return "fiscal", self.fiscal_state, _FISCAL_TRANSITIONS, "fiscal_state"
        raise ValidationError(self.env._("Unsupported DTE state: %s") % target_state)

    def _get_transition_artifact_role(
        self, target_state, state_domain, artifact, correlation_key
    ):
        artifact_roles = (
            _PREPARATION_ARTIFACT_ROLES
            if state_domain == "preparation"
            else _FISCAL_ARTIFACT_ROLES
        )
        return artifact_roles.get(target_state)

    def _validate_transition_evidence(
        self, target_state, state_domain, artifact, correlation_key
    ):
        required_role = self._get_transition_artifact_role(
            target_state, state_domain, artifact, correlation_key
        )
        if required_role and (len(artifact) != 1 or artifact.role != required_role):
            raise ValidationError(
                self.env._("Transition to %(state)s requires %(role)s evidence.")
                % {"state": target_state, "role": required_role}
            )
        if (
            state_domain == "preparation"
            and target_state in {"prepared", "signed", "queued"}
            and not self.payload_digest
        ):
            raise ValidationError(
                self.env._(
                    "A source snapshot and its digest are required before "
                    "XML preparation."
                )
            )
        if state_domain == "fiscal":
            if target_state == "outcome_unknown" and not correlation_key:
                raise ValidationError(
                    self.env._(
                        "An unknown remote outcome must include a correlation key."
                    )
                )
            if self.preparation_state != "queued":
                raise ValidationError(
                    self.env._(
                        "SII status cannot be recorded before the signed DTE is queued."
                    )
                )

    def _get_transition_write_values(
        self, target_state, field_name, state_domain, folio_number
    ):
        write_values = {field_name: target_state}
        if target_state == "numbered":
            if (
                not isinstance(folio_number, int)
                or isinstance(folio_number, bool)
                or folio_number <= 0
            ):
                raise ValidationError(
                    self.env._(
                        "A positive folio number is required for the numbered state."
                    )
                )
            write_values["folio"] = folio_number
        elif folio_number not in (False, None):
            raise ValidationError(
                self.env._(
                    "A folio number can only be assigned with the numbered state."
                )
            )
        if (
            state_domain == "preparation"
            and target_state
            in {
                "prepared",
                "signed",
                "queued",
            }
            and not self.folio
        ):
            raise ValidationError(
                self.env._("A folio must be reserved before preparing XML.")
            )
        return write_values

    def action_record_source_snapshot(self, artifact_id):
        """Bind one immutable source snapshot artifact to this document."""
        self.ensure_one()
        self._check_dte_manager(
            self.env._("Only a DTE manager can record a source snapshot.")
        )
        self.check_access("write")
        artifact = self.env["l10n_cl.electronic.artifact"].browse(artifact_id).exists()
        if (
            len(artifact) != 1
            or artifact.document_id != self
            or artifact.role != "source_snapshot"
        ):
            raise ValidationError(
                self.env._(
                    "The source snapshot must be evidence for this electronic document."
                )
            )
        self._lock_lifecycle()
        previous_snapshot = self.env["l10n_cl.electronic.event"].search(
            [
                ("document_id", "=", self.id),
                ("event_code", "=", "source_snapshot_recorded"),
            ],
            limit=1,
        )
        if self.payload_digest:
            if previous_snapshot.artifact_id == artifact:
                artifact.action_verify_integrity()
                return True
            raise ValidationError(self.env._("The source snapshot cannot be replaced."))
        if self.preparation_state in {"prepared", "signed", "queued"}:
            raise ValidationError(
                self.env._("A source snapshot must be recorded before XML preparation.")
            )
        artifact.action_verify_integrity()
        with self.env.cr.savepoint():
            super().write({"payload_digest": artifact.sha256})
            self._create_audit_events(
                [
                    {
                        "event_code": "source_snapshot_recorded",
                        "state_domain": "preparation",
                        "from_state": self.preparation_state,
                        "to_state": self.preparation_state,
                        "artifact_id": artifact.id,
                    }
                ]
            )
        return True

    def _create_audit_events(self, event_values_list):
        """Create immutable audit events through a narrowly scoped elevation."""
        event_model = self.env["l10n_cl.electronic.event"].sudo()
        for document, event_values in zip(self, event_values_list, strict=True):
            event_model.create(
                {
                    **event_values,
                    "document_id": document.id,
                }
            )
