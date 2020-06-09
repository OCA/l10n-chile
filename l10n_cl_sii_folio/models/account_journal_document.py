# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountJournalDocument(models.Model):
    _name = "account.journal.document"
    _description = "Journal SII Documents"
    _order = "sequence"

    @api.depends('class_id', 'sequence_id')
    def _compute_name(self):
        for rec in self:
            sequence_name = \
                rec.sequence_id and (': ' + rec.sequence_id.name) or ''
            name = (rec.class_id.name or '') + sequence_name
            rec.name = name

    name = fields.Char(compute="_compute_name", store=True)
    class_id = fields.Many2one(
        'sii.document.class', string='Document Class', required=True)
    sequence_id = fields.Many2one(
        'ir.sequence', string='Entry Sequence',
        help="""This field contains the information related to the numbering
        of the documents entries of this document type.""")
    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True)
    sequence = fields.Integer(string='Sequence')

    _sql_constraints = \
        [("journal_class_unique",
          "unique(journal_id, class_id)",
          "You can only have one sequence per journal and document class.")]

    @api.constrains('class_id')
    def check_class(self):
        if self.class_id and self.sequence_id and \
                self.class_id != self.sequence_id.class_id:
            raise UserError(_("The document class must be the same as the one"
                              " on the sequence!"))
