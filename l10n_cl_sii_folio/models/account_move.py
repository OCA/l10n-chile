# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def post(self, invoice=False):
        res = {}
        for move in self:
            if move.journal_id.type not in ('sale', 'purchase') or \
                    not move.journal_id.journal_document_class_ids:
                res = super(AccountMove, move).post(invoice)
                continue
            move._post_validate()
            # Create the analytic lines in batch is faster as it leads to
            # less cache invalidation.
            move.mapped('line_ids').create_analytic_lines()
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.move_name and invoice.move_name != '/':
                    new_name = invoice.move_name
                else:
                    # Determine the sequence to be used
                    if invoice and invoice.class_id:
                        journal_document = \
                            move.journal_id.journal_document_class_ids.\
                            filtered(lambda x: x.class_id == invoice.class_id)
                        sequence = journal_document and \
                            journal_document.sequence_id or False

                    else:
                        # If invoice is actually refund and journal has a
                        # refund_sequence then use that one or use the regular
                        # one
                        sequence = journal.sequence_id
                        if invoice and \
                                invoice.type in ['out_refund', 'in_refund'] \
                                and journal.refund_sequence:
                            if not journal.refund_sequence_id:
                                raise UserError(_(
                                    'Please define a sequence for the credit '
                                    'notes'))
                            sequence = journal.refund_sequence_id

                    # Get the new name from the sequence
                    if sequence:
                        new_name = sequence.with_context(
                            ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError(
                            _('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name

            if move == move.company_id.account_opening_move_id and \
                    not move.company_id.account_bank_reconciliation_start:
                # For opening moves, we set the reconciliation date threshold
                # to the move's date if it wasn't already set (we don't want
                # to have to reconcile all the older payments -made before
                # installing Accounting- with bank statements)
                move.company_id.account_bank_reconciliation_start = move.date

            res = move.write({'state': 'posted'})
        return res
