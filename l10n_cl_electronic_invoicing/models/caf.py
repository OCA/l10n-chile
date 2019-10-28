# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging
import pytz
from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    pass

try:
    import base64
except ImportError:
    pass


class Caf(models.Model):
    _name = "dte.caf"
    _description = "DTE CAF"

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
        help="Upload the CAF XML File in this holder",
    )
    issued_date = fields.Date(string="Issued Date", compute="_compute_data",
                              store=True)
    expiration_date = fields.Date(
        string="Expiration Date", compute="_compute_data", store=True
    )
    sii_document_class = fields.Integer(
        string="SII Document Class", compute="_compute_data", store=True
    )
    start_nm = fields.Integer(
        string="Start Number",
        help="CAF Starts from this number",
        compute="_compute_data",
        store=True,
    )
    final_nm = fields.Integer(
        string="End Number",
        help="CAF Ends to this number",
        compute="_compute_data",
        store=True,
    )
    status = fields.Selection(
        [("draft", "Draft"), ("in_use", "In Use"), ("spent", "Spent")],
        string="Status",
        default="draft",
        help="""Draft: means it has not been used yet. You must put in in used
in order to make it available for use. Spent: means that the number interval
has been exhausted.""",
    )
    rut_n = fields.Char(string="RUT", compute="_compute_data", store=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=False,
        default=lambda self: self.env.user.company_id,
    )
    sequence_id = fields.Many2one("ir.sequence", string="Sequence")
    use_level = fields.Float(string="Use Level", compute="_compute_used_level")
    # TODO: hacerlo configurable
    nivel_minimo = fields.Integer(
        string="Nivel Mínimo de Folios", default=5)

    _sql_constraints = [
        ("filename_unique", "unique(filename)",
         "Error! Filename Already Exist!")
    ]

    @api.onchange("caf_file")
    def load_caf(self, flags=False):
        if not self.caf_file or not self.sequence_id:
            return
        result = self.decode_caf()["AUTORIZACION"]["CAF"]["DA"]
        self.start_nm = result["RNG"]["D"]
        self.final_nm = result["RNG"]["H"]
        self.sii_document_class = result["TD"]
        self.issued_date = result["FA"]
        if self.sequence_id.sii_document_class_id.sii_code not in [34, 52]:
            self.expiration_date = date(
                int(result["FA"][:4]),
                int(result["FA"][5:7]),
                int(result["FA"][8:10])
            ) + relativedelta(months=6)
        self.rut_n = "CL" + result["RE"].replace("-", "")
        if self.rut_n != self.company_id.vat.replace("L0", "L"):
            raise UserError(
                _("Company vat %s should be the same that assigned company's "
                  "vat: %s!")
                % (self.rut_n, self.company_id.vat)
            )
        elif self.sii_document_class != \
                self.sequence_id.sii_document_class_id.sii_code:
            raise UserError(
                _("""SII Document Type for this CAF is %s and selected
                sequence associated document class is %s. This values should be
                equal for DTE Invoicing to work properly!""")
                % (self.sii_document_class,
                   self.sequence_id.sii_document_class_id.sii_code)
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
                self.sequence_id.sii_document_class_id.name,
                diff,
            )
        return ""


class SequenceCaf(models.Model):
    _inherit = "ir.sequence"

    def get_qty_available(self, folio=None):
        folio = folio or self._get_folio()
        try:
            cafs = self.get_caf_files(folio)
        except:
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
            if i.sii_document_class_id:
                i.qty_available = i.get_qty_available()

    sii_document_class_id = fields.Many2one(
        "sii.document.class", string="Document Type")
    is_dte = fields.Boolean(string="IS DTE?",
                            related="sii_document_class_id.dte")
    dte_caf_ids = fields.One2many("dte.caf", "sequence_id", string="DTE Caf")
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
        msg = """No Hay caf para el documento: {}, está fuera de rango.
                Solicite un nuevo CAF en el sitio www.sii.cl""".format(folio)
        if not caffiles:
            raise UserError(
                _("""No hay caf disponible para el documento %s folio %s.
                Por favor solicite suba un CAF o solicite uno en el SII."""
                    % (self.name, folio))
            )
        for caffile in caffiles:
            if int(folio) >= caffile.start_nm and \
                    int(folio) <= caffile.final_nm:
                if caffile.expiration_date:
                    if fields.Date.context_today(self) > \
                            caffile.expiration_date:
                        msg = "CAF Vencido. %s" % msg
                        continue
                alert_msg = caffile.check_nivel(folio)
                if alert_msg != "":
                    self.env["bus.bus"].sendone(
                        (self._cr.dbname, "dte.caf",
                         self.env.user.partner_id.id),
                        {
                            "title": "Alerta sobre CAF",
                            "message": alert_msg,
                            "url": "res_config",
                            "type": "dte_notif",
                        },
                    )
                return caffile.decode_caf()
        raise UserError(_(msg))

    def get_caf_files(self, folio=None):
        """
            Devuelvo caf actual y futuros
        """
        folio = folio or self._get_folio()
        if not self.dte_caf_ids:
            raise UserError(
                _("""No hay CAFs disponibles para la secuencia de %s.
                 Por favor suba un CAF o solicite uno en el SII."""
                  % (self.name))
            )
        cafs = self.dte_caf_ids
        cafs = sorted(cafs, key=lambda e: e.start_nm)
        result = []
        for caffile in cafs:
            if int(folio) <= caffile.final_nm:
                result.append(caffile)
        if result:
            return result
        return False

    def update_next_by_caf(self, folio=None):
        if self.sii_document_class_id:
            return
        folio = folio or self._get_folio()
        menor = False
        cafs = self.get_caf_files(folio)
        if not cafs:
            raise UserError(_("No quedan CAFs para %s disponibles") %
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
        folio = super(SequenceCaf, self)._next_do()
        if self.sii_document_class_id and self.forced_by_caf and \
                self.dte_caf_ids:
            self.update_next_by_caf(folio)
            actual = self.number_next
            if self.implementation == "standard":
                actual = self.number_next_actual
            if number_next + 1 != actual:  # Fue actualizado
                number_next = actual
            folio = self.get_next_char(number_next)
        return folio
