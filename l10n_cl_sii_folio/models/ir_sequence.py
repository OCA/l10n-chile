# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime
import logging
import pytz
from odoo import fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def get_qty_available(self, folio=None):
        folio = folio or self._get_folio()
        try:
            cafs = self.get_caf_files(folio)
        except UserError:
            cafs = False
        available = 0
        folio = int(folio)
        if cafs:
            for c in cafs:
                if folio >= c.start_nm and folio <= c.final_nm:
                    available += c.final_nm - folio
                elif folio <= c.final_nm:
                    available += (c.final_nm - c.start_nm) + 1
                if folio > c.start_nm:
                    available += 1
        return available

    def _compute_qty_available(self):
        for i in self:
            if i.class_id:
                i.qty_available = i.get_qty_available()

    class_id = fields.Many2one("sii.document.class", string="Document Type")
    is_dte = fields.Boolean(string="Is DTE?",
                            related="class_id.dte")
    folio_ids = fields.One2many("ir.sequence.folio", "sequence_id",
                                string="DTE Caf")
    qty_available = fields.Integer(
        string="Quantity Available", compute="_compute_qty_available")
    forced_by_caf = fields.Boolean(string="Forced By CAF", default=True)

    def _get_folio(self):
        return self.number_next_actual

    def time_stamp(self, formato="%Y-%m-%dT%H:%M:%S"):
        tz = pytz.timezone("America/Santiago")
        return datetime.now(tz).strftime(formato)

    def get_caf_file(self, folio=False):
        folio = folio or self._get_folio()
        caffiles = self.get_caf_files(folio)
        msg = """There is no folio for this document: {}, out of range.
                Request a new CAF on https://www.sii.cl""".format(folio)
        if not caffiles:
            raise UserError(
                _("There is no folio available for the document %s folio %s. "
                  "Please request a new CAF to SII." % (self.name, folio)))
        for caffile in caffiles:
            if caffile.start_nm <= int(folio) <= caffile.final_nm:
                if caffile.expiration_date:
                    if fields.Date.context_today(self) > \
                            caffile.expiration_date:
                        msg = "CAF Expired. %s" % msg
                        continue
                alert_msg = caffile.check_nivel(folio)
                if alert_msg != "":
                    self.env["bus.bus"].sendone(
                        (self._cr.dbname, "dte.caf",
                         self.env.user.partner_id.id),
                        {
                            "title": "Alert on CAF",
                            "message": alert_msg,
                            "url": "res_config",
                            "type": "dte_notif",
                        },
                    )
                return caffile.decode_caf()
        raise UserError(_(msg))

    def get_caf_files(self, folio=None):
        folio = folio or self._get_folio()
        if not self.folio_ids:
            raise UserError(
                _("There is no CAF available for the sequence of %s. "
                  "Please upload a new CAF or request a new one to SII."""
                  % (self.name)))
        cafs = self.folio_ids
        cafs = sorted(cafs, key=lambda e: e.start_nm)
        result = []
        for caffile in cafs:
            if int(folio) <= caffile.final_nm:
                result.append(caffile)
        if result:
            return result
        return False

    def update_next_by_caf(self, folio=None):
        if self.class_id:
            return
        folio = folio or self._get_folio()
        menor = False
        cafs = self.get_caf_files(folio)
        if not cafs:
            raise UserError(_("There is no CAF available for %s.") %
                            self.name)
        for c in cafs:
            if not menor or c.start_nm < menor.start_nm:
                menor = c
        if menor and int(folio) < menor.start_nm:
            self.sudo(SUPERUSER_ID).write({"number_next": menor.start_nm})

    def _next_do(self):
        number_next = self.number_next
        if self.implementation == "standard":
            number_next = self.number_next_actual
        folio = super(IrSequence, self)._next_do()
        if self.class_id and self.forced_by_caf and \
                self.folio_ids:
            self.update_next_by_caf(folio)
            actual = self.number_next
            if self.implementation == "standard":
                actual = self.number_next_actual
            if number_next + 1 != actual:  # Fue actualizado
                number_next = actual
            folio = self.get_next_char(number_next)
        return folio
