# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournalSiiDocumentClass(models.Model):
    _name = "account.journal.sii.document.class"
    _description = "Journal SII Documents"
    _order = "sequence"

    @api.depends("sii_document_class_id", "sequence_id")
    def _compute_sequence_name(self):
        for r in self:
            sequence_name = (": " + r.sequence_id.name) if r.sequence_id \
                else ""
            name = (r.sii_document_class_id.name or "") + sequence_name
            r.name = name

    name = fields.Char(compute="_compute_sequence_name")
    sii_document_class_id = fields.Many2one(
        "sii.document.class", string="Document Type", required=True
    )
    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Entry Sequence",
        help="""This field contains the information related to the numbering \
            of the documents entries of this document type.""",
    )
    journal_id = fields.Many2one("account.journal", string="Journal",
                                 required=True)
    sequence = fields.Integer(string="Sequence")

    @api.onchange("sii_document_class_id")
    def check_sii_document_class(self):
        if (
            self.sii_document_class_id
            and self.sequence_id
            and self.sii_document_class_id !=
                self.sequence_id.sii_document_class_id
        ):
            raise UserError(_(
                "The document type of the sequence is different"))
