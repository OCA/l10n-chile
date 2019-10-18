# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    sucursal_id = fields.Many2one("sii.sucursal", string="Sucursal")
    sii_code = fields.Char(
        related="sucursal_id.name", string="Código SII Sucursal", readonly=True
    )
    journal_document_class_ids = fields.One2many(
        "account.journal.sii.document.class", "journal_id", "Documents Class"
    )
    use_documents = fields.Boolean(string="Use Documents?",
                                   default="_get_default_doc")
    journal_activities_ids = fields.Many2many(
        "partner.activities",
        id1="journal_id",
        id2="activities_id",
        string="Journal Turns",
        help="""Select the turns you want to \
            invoice in this Journal""",
    )
    restore_mode = fields.Boolean(string="Restore Mode", default=False)
    send_book_dte = fields.Boolean(
        string="¿No Enviar los libros de Compra/Venta al SII?",
        help="Para saber si se envian los Libros Fiscales al SII o se "
             "mantienen para control interno de la empresa.",
        store=True,
    )

    @api.onchange("journal_activities_ids")
    def max_actecos(self):
        if len(self.journal_activities_ids) > 4:
            raise UserError(_(
                "It must be 4 activities maximum per journal, select the most "
                "significant ones for this journal."))

    @api.multi
    def _get_default_doc(self):
        self.ensure_one()
        if self.type == "sale" or self.type == "purchase":
            self.use_documents = True

    @api.multi
    def name_get(self):
        res = []
        for journal in self:
            currency = journal.currency_id or journal.company_id.currency_id
            name = "%s (%s)" % (journal.name, currency.name)
            if journal.sucursal_id and self.env.context.get("show_full_name",
                                                            False):
                name = "%s (%s)" % (name, journal.sucursal_id.name)
            res.append((journal.id, name))
        return res
