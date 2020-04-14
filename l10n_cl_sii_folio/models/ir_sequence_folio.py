# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import logging
from datetime import date

import xmltodict
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrSequenceFolio(models.Model):
    _name = "ir.sequence.folio"
    _description = "Ir Sequence Folios"

    @api.depends("caf_file")
    def _compute_data(self):
        for Caf in self:
            if Caf:
                Caf.load_caf()

    name = fields.Char(string="Name", readonly=True,
                       compute="_compute_filename")
    filename = fields.Char(string="File Name")
    caf_file = fields.Binary(
        string="CAF XML File",
        filters="*.xml",
        required=True,
        help="Upload the CAF XML File in this holder")
    issued_date = fields.Date(string="Issued Date", compute="_compute_data",
                              store=True)
    expiration_date = fields.Date(
        string="Expiration Date", compute="_compute_data", store=True)
    sii_document_class = fields.Integer(
        string="SII Document Class", compute="_compute_data", store=True)
    start_nm = fields.Integer(
        string="Start Number",
        help="CAF Starts from this number",
        compute="_compute_data",
        store=True)
    final_nm = fields.Integer(
        string="End Number",
        help="CAF Ends to this number",
        compute="_compute_data",
        store=True)
    status = fields.Selection(
        [("draft", "Draft"), ("in_use", "In Use"), ("spent", "Spent")],
        string="Status",
        default="draft",
        help="""Draft: means it has not been used yet. You must put it in used
        in order to make it available for use.
        Spent: means that the number interval has been exhausted.""")
    rut_n = fields.Char(string="VAT", compute="_compute_data", store=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=False,
        default=lambda self: self.env.user.company_id)
    sequence_id = fields.Many2one("ir.sequence", string="Sequence")
    use_level = fields.Float(string="Use Level", compute="_compute_used_level")
    # TODO: hacerlo configurable
    nivel_minimo = fields.Integer(
        string="Nivel Mínimo de Folios", default=5)

    _sql_constraints = [("filename_unique", "unique(filename)",
                         "Error! Filename Already Exist!")]

    @api.onchange("caf_file")
    def load_caf(self, flags=False):
        if not self.caf_file or not self.sequence_id:
            return
        result = self.decode_caf()["AUTORIZACION"]["CAF"]["DA"]
        self.start_nm = result["RNG"]["D"]
        self.final_nm = result["RNG"]["H"]
        self.sii_document_class = result["TD"]
        self.issued_date = result["FA"]
        if self.sequence_id.class_id.code not in [34, 52]:
            self.expiration_date = date(
                int(result["FA"][:4]),
                int(result["FA"][5:7]),
                int(result["FA"][8:10])
            ) + relativedelta(months=6)
        if result["RE"] != self.company_id.vat:
            self.rut_n = "CL" + result["RE"].replace("-", "")
            if self.rut_n != self.company_id.vat.replace("L0", "L"):
                raise UserError(
                    _("Company vat %s should be the same"
                      " that assigned company's vat: %s!")
                    % (self.rut_n, self.company_id.vat)
                )
        if self.sii_document_class != \
                self.sequence_id.class_id.code:
            raise UserError(
                _("""SII Document Type for this CAF is %s and selected
                sequence associated document class is %s. This values should be
                equal for DTE Invoicing to work properly!""")
                % (self.sii_document_class,
                   self.sequence_id.class_id.code)
            )
        if flags:
            return True
        self.status = "in_use"
        self._compute_used_level()

    def _compute_used_level(self):
        for r in self:
            if r.status not in ["draft"]:
                folio = r.sequence_id.number_next_actual
                try:
                    if folio > r.final_nm:
                        r.use_level = 100
                    elif folio < r.start_nm:
                        r.use_level = 0
                    else:
                        r.use_level = 100.0 * (
                            (int(folio) - r.start_nm)
                            / float(r.final_nm - r.start_nm + 1)
                        )
                except ZeroDivisionError:
                    r.use_level = 0
            else:
                r.use_level = 0

    def _compute_filename(self):
        for r in self:
            r.name = r.filename

    def decode_caf(self):
        post = base64.b64decode(self.caf_file).decode("ISO-8859-1")
        post = xmltodict.parse(post.replace('<?xml version="1.0"?>', "", 1))
        return post

    def check_nivel(self, folio):
        if not folio:
            return ""
        diff = self.final_nm - int(folio)
        if diff <= self.nivel_minimo:
            return "Nivel bajo de CAF para %s, quedan %s folios" % (
                self.sequence_id.class_id.name,
                diff,
            )
        return ""
