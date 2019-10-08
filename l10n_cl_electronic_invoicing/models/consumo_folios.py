# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import sys
import os
import textwrap
from datetime import datetime
import dateutil.relativedelta as relativedelta
import logging
from lxml import etree
from lxml.etree import Element, SubElement
import pytz
import collections

from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

try:
    from suds.client import Client
except ImportError:
    pass
try:
    import urllib3
except ImportError:
    pass

pool = urllib3.PoolManager(timeout=30)
_logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import \
        load_pem_private_key
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except ImportError:
    _logger.warning("Cannot import OpenSSL library")

try:
    import xmltodict
except ImportError:
    _logger.info("Cannot import xmltodict library")

try:
    import dicttoxml
    dicttoxml.set_debug(False)
except ImportError:
    _logger.info("Cannot import dicttoxml library")

try:
    import base64
except ImportError:
    _logger.info("Cannot import base64 library")

try:
    import hashlib
except ImportError:
    _logger.info("Cannot import hashlib library")

server_url = {
    "SIICERT": "https://maullin.sii.cl/DTEWS/",
    "SII": "https://palena.sii.cl/DTEWS/",
}

BC = """-----BEGIN CERTIFICATE-----\n"""
EC = """\n-----END CERTIFICATE-----\n"""

# hardcodeamos este valor por ahora

USING_PYTHON2 = True if sys.version_info < (3, 0) else False
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace("/models",
                                                              "/static/xsd/")

connection_status = {
    "0": "Upload OK",
    "1": "El Sender no tiene permiso para enviar",
    "2": "Error en tamaño del archivo (muy grande o muy chico)",
    "3": "Archivo cortado (tamaño <> al parámetro size)",
    "5": "No está autenticado",
    "6": "Empresa no autorizada a enviar archivos",
    "7": "Esquema Invalido",
    "8": "Firma del Documento",
    "9": "Sistema Bloqueado",
    "Otro": "Error Interno.",
}


class ConsumoFolios(models.Model):
    _name = "account.move.consumo_folios"
    _description = "Account Move Consumo Folios"

    sii_message = fields.Text(
        string="SII Message",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    sii_xml_request = fields.Text(
        string="SII XML Request",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    sii_xml_response = fields.Text(
        string="SII XML Response",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    sii_send_ident = fields.Text(
        string="SII Send Identification",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("NoEnviado", "No Enviado"),
            ("Enviado", "Enviado"),
            ("Aceptado", "Aceptado"),
            ("Rechazado", "Rechazado"),
            ("Reparo", "Reparo"),
            ("Proceso", "Proceso"),
            ("Reenviar", "Reenviar"),
            ("Anulado", "Anulado"),
        ],
        "Resultado",
        index=True,
        readonly=True,
        default="draft",
        track_visibility="onchange",
        copy=False,
        help="""
         * The 'Draft' status is used when a user is encoding a new and
           unconfirmed Invoice.\n"
         * The 'Pro-forma' status is used the invoice does not have an invoice
           number.\n"
         * The 'Open' status is used when user create invoice, an invoice
           number is generated. Its in open status till user does not pay
           invoice.\n"
         * The 'Paid' status is set automatically when the invoice is paid.
           Its related journal entries may or may not be reconciled.\n"
         * The 'Cancelled' status is used when user cancel invoice.""")
    move_ids = fields.Many2many(
        "account.move", readonly=True, states={"draft": [("readonly", False)]}
    )
    fecha_inicio = fields.Date(
        string="Fecha Inicio",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: fields.Date.context_today(self),
    )
    fecha_final = fields.Date(
        string="Fecha Final",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: fields.Date.context_today(self),
    )
    correlativo = fields.Integer(
        string="Correlativo",
        readonly=True,
        states={"draft": [("readonly", False)]},
        invisible=True,
    )
    sec_envio = fields.Integer(
        string="Secuencia de Envío",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    total_neto = fields.Monetary(string="Total Net", store=True, readonly=True,
                                 compute="_compute_totales")
    total_iva = fields.Monetary(string="Total Tax", store=True, readonly=True,
                                compute="_compute_totales")
    total_exento = fields.Monetary(string="Total Exempt", store=True,
                                   readonly=True, compute="_compute_totales")
    total = fields.Monetary(string="Total Amount", store=True, readonly=True,
                            compute="_compute_totales")
    total_boletas = fields.Integer(string="Total Boletas", store=True,
                                   readonly=True, compute="_compute_totales")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.user.company_id.id,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    name = fields.Char(
        string="Detalle",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date = fields.Date(
        string="Date",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: fields.Date.context_today(self),
    )
    detalles = fields.One2many(
        "account.move.consumo_folios.detalles",
        "cf_id",
        string="Detalle Rangos",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    impuestos = fields.One2many(
        "account.move.consumo_folios.impuestos",
        "cf_id",
        string="Detalle Impuestos",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    anulaciones = fields.One2many(
        "account.move.consumo_folios.anulaciones",
        "cf_id",
        string="Anulaciones",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility="always",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    responsable_envio = fields.Many2one("res.users")
    sii_result = fields.Selection(
        [
            ("draft", "Borrador"),
            ("NoEnviado", "No Enviado"),
            ("Enviado", "Enviado"),
            ("Aceptado", "Aceptado"),
            ("Rechazado", "Rechazado"),
            ("Reparo", "Reparo"),
            ("Proceso", "Proceso"),
            ("Reenviar", "Reenviar"),
            ("Anulado", "Anulado"),
        ],
        related="state",
        string="SII Result"
    )

    _order = "fecha_inicio desc"

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False,
            lazy=True):
        res = super(ConsumoFolios, self).read_group(
            domain, fields, groupby, offset, limit=limit, orderby=orderby,
            lazy=lazy)
        if "total_iva" in fields:
            for line in res:
                if "__domain" in line:
                    lines = self.search(line["__domain"])
                    line.update(
                        {
                            "total_neto": 0,
                            "total_iva": 0,
                            "total_exento": 0,
                            "total": 0,
                            "total_boletas": 0,
                        }
                    )
                    for l in lines:
                        line.update({
                            "total_neto": line["total_neto"] + l.total_neto,
                            "total_iva": line["total_iva"] + l.total_iva,
                            "total_exento":
                                line["total_exento"] + l.total_exento,
                            "total": line["total"] + l.total,
                            "total_boletas":
                                line["total_boletas"] + l.total_boletas,
                            }
                        )
        return res

    @api.onchange("impuestos")
    @api.depends("impuestos")
    def _compute_totales(self):
        for r in self:
            total_iva = 0
            total_exento = 0
            total = 0
            total_boletas = 0
            for d in r.impuestos:
                total_iva += d.monto_iva
                total_exento += d.monto_exento
                total += d.monto_total
            for d in r.detalles:
                if d.tpo_doc.sii_code in [39, 41] and \
                        d.tipo_operacion == "utilizados":
                    total_boletas += d.cantidad
            r.total_neto = total - total_iva - total_exento
            r.total_iva = total_iva
            r.total_exento = total_exento
            r.total = total
            r.total_boletas = total_boletas

    @api.onchange("move_ids", "anulaciones")
    def _resumenes(self):
        resumenes, TpoDocs = self._get_resumenes()
        if self.impuestos and isinstance(self.id, int):
            self._cr.execute(
                "DELETE FROM account_move_consumo_folios_impuestos WHERE "
                "cf_id=%s",
                (self.id,),
            )
            self.invalidate_cache()
        if self.detalles and isinstance(self.id, int):
            self._cr.execute(
                "DELETE FROM account_move_consumo_folios_detalles WHERE "
                "cf_id=%s",
                (self.id,),
            )
            self.invalidate_cache()
        detalles = [[5]]

        def pushItem(key_item, item, tpo_doc):
            rango = {
                "tipo_operacion": "utilizados"
                if key_item == "RangoUtilizados"
                else "anulados",
                "folio_inicio": item["Inicial"],
                "folio_final": item["Final"],
                "cantidad": int(item["Final"]) - int(item["Inicial"]) + 1,
                "tpo_doc": self.env["sii.document.class"]
                .search([("sii_code", "=", tpo_doc)])
                .id,
            }
            detalles.append([0, 0, rango])

        for r, value in resumenes.items():
            if "%s_folios" % str(r) in value:
                Rangos = value[str(r) + "_folios"]
                if "itemUtilizados" in Rangos:
                    for rango in Rangos["itemUtilizados"]:
                        pushItem("RangoUtilizados", rango, r)
                if "itemAnulados" in Rangos:
                    for rango in Rangos["itemAnulados"]:
                        pushItem("RangoAnulados", rango, r)
        self.detalles = detalles
        docs = collections.OrderedDict()
        for r, value in resumenes.items():
            if value.get("FoliosUtilizados", False):
                docs[r] = {
                    "tpo_doc": self.env["sii.document.class"]
                    .search([("sii_code", "=", r)])
                    .id,
                    "cantidad": value["FoliosUtilizados"],
                    "monto_neto": value["MntNeto"],
                    "monto_iva": value["MntIva"],
                    "monto_exento": value["MntExento"],
                    "monto_total": value["MntTotal"],
                }
        lines = [[5]]
        for key, i in docs.items():
            i["currency_id"] = self.env.user.company_id.currency_id.id
            lines.append([0, 0, i])
        self.impuestos = lines

    @api.onchange("fecha_inicio", "company_id", "fecha_final")
    def set_data(self):
        self.name = self.fecha_inicio
        self.fecha_final = self.fecha_inicio
        self.move_ids = (
            self.env["account.move"]
            .search(
                [
                    ("document_class_id.sii_code", "in", [39, 41]),
                    #            ('sended','=', False),
                    ("date", "=", self.fecha_inicio),
                    ("company_id", "=", self.company_id.id),
                ]
            )
            .ids
        )
        consumos = self.search_count(
            [
                ("fecha_inicio", "=", self.fecha_inicio),
                ("state", "not in", ["draft", "Rechazado"]),
                ("company_id", "=", self.company_id.id),
            ]
        )
        if consumos > 0:
            self.sec_envio = consumos + 1
        self._resumenes()

    @api.multi
    def copy(self, default=None):
        res = super(ConsumoFolios, self).copy(default)
        res.set_data()
        return res

    @api.multi
    def unlink(self):
        for libro in self:
            if libro.state not in ("draft", "cancel"):
                raise UserError(_("You cannot delete a Validated book."))
        return super(ConsumoFolios, self).unlink()

    def split_cert(self, cert):
        certf = ""
        for i in range(0, 29):
            certf += cert[76 * i: 76 * (i + 1)] + "\n"
        return certf

    def create_template_envio(
        self,
        RutEmisor,
        FchResol,
        NroResol,
        FchInicio,
        FchFinal,
        Correlativo,
        SecEnvio,
        EnvioDTE,
        signature_d,
        IdEnvio="SetDoc",
    ):
        if Correlativo != 0:
            Correlativo = "<Correlativo>" + str(Correlativo) + "</Correlativo>"
        else:
            Correlativo = ""
        xml = """<DocumentoConsumoFolios ID="{10}">
<Caratula  version="1.0" >
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<FchResol>{2}</FchResol>
<NroResol>{3}</NroResol>
<FchInicio>{4}</FchInicio>
<FchFinal>{5}</FchFinal>{6}
<SecEnvio>{7}</SecEnvio>
<TmstFirmaEnv>{8}</TmstFirmaEnv>
</Caratula>
{9}
</DocumentoConsumoFolios>
""".format(
            RutEmisor,
            signature_d["subject_serial_number"],
            FchResol,
            NroResol,
            FchInicio,
            FchFinal,
            str(Correlativo),
            str(SecEnvio),
            self.time_stamp(),
            EnvioDTE,
            IdEnvio,
        )
        return xml

    def time_stamp(self, formato="%Y-%m-%dT%H:%M:%S"):
        tz = pytz.timezone("America/Santiago")
        return datetime.now(tz).strftime(formato)

    def xml_validator(self, some_xml_string, validacion="doc"):
        validacion_type = {
            "consu": "ConsumoFolio_v10.xsd",
            "sig": "xmldsignature_v10.xsd",
        }
        xsd_file = xsdpath + validacion_type[validacion]
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            xml_doc = etree.fromstring(some_xml_string)
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            raise UserError(_("XML Malformed Error:  %s") % e.args)

    def get_seed(self, company_id):
        return self.env["account.move.book"].get_seed(company_id)

    def create_template_seed(self, seed):
        return self.env["account.move.book"].create_template_seed(seed)

    def create_template_env(self, doc, simplificado=False):
        xsd = "http://www.sii.cl/SiiDte ConsumoFolio_v10.xsd"
        xml = """<ConsumoFolios xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="{0}" \
version="1.0">
{1}</ConsumoFolios>""".format(
            xsd, doc
        )
        return xml

    def sign_seed(self, message, privkey, cert):
        return self.env["account.move.book"].sign_seed(message, privkey, cert)

    def get_token(self, seed_file, company_id):
        return self.env["account.move.book"].get_token(seed_file, company_id)

    def ensure_str(self, x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x

    def sign_full_xml(self, message, privkey, cert, uri,
                      validation_type="consu"):
        doc = etree.fromstring(message)
        string = etree.tostring(doc[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        digest = base64.b64encode(self.digest(mess))
        reference_uri = "#" + uri
        signed_info = Element("SignedInfo")
        SubElement(signed_info, "CanonicalizationMethod",
                   Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        SubElement(signed_info, "SignatureMethod",
                   Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1")
        reference = SubElement(signed_info, "Reference", URI=reference_uri)
        transforms = SubElement(reference, "Transforms")
        SubElement(
            transforms,
            "Transform",
            Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        SubElement(reference, "DigestMethod",
                   Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_value = SubElement(reference, "DigestValue")
        digest_value.text = digest
        signed_info_c14n = etree.tostring(
            signed_info, method="c14n", exclusive=False, with_comments=False,
            inclusive_ns_prefixes=None)
        att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" ' \
              'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        # @TODO Find better way to add xmlns:xsi attrib
        signed_info_c14n = signed_info_c14n.decode().replace(
            "<SignedInfo>", "<SignedInfo %s>" % att)
        sig_root = Element(
            "Signature", attrib={"xmlns": "http://www.w3.org/2000/09/xmldsig#"}
        )
        sig_root.append(etree.fromstring(signed_info_c14n))
        signature_value = SubElement(sig_root, "SignatureValue")
        key = crypto.load_privatekey(type_, privkey.encode("ascii"))
        signature = crypto.sign(key, signed_info_c14n, "sha1")
        signature_value.text = \
            textwrap.fill(base64.b64encode(signature).decode(), 64)
        key_info = SubElement(sig_root, "KeyInfo")
        key_value = SubElement(key_info, "KeyValue")
        rsa_key_value = SubElement(key_value, "RSAKeyValue")
        modulus = SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(
            privkey.encode("ascii"), password=None, backend=default_backend())
        longs = self.env["account.move.book"].long_to_bytes(
            key.public_key().public_numbers().n)
        modulus.text = textwrap.fill(base64.b64encode(longs).decode(), 64)
        exponent = SubElement(rsa_key_value, "Exponent")
        longs = self.env["account.move.book"].long_to_bytes(
            key.public_key().public_numbers().e)
        exponent.text = self.ensure_str(base64.b64encode(longs).decode())
        x509_data = SubElement(key_info, "X509Data")
        x509_certificate = SubElement(x509_data, "X509Certificate")
        x509_certificate.text = "\n" + textwrap.fill(cert, 64)
        msg = etree.tostring(sig_root).decode()
        msg = msg if self.xml_validator(msg, "sig") else ""
        fulldoc = \
            message.replace("</ConsumoFolios>", msg + "\n</ConsumoFolios>")
        fulldoc = fulldoc
        fulldoc = (
            '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + fulldoc
            if self.xml_validator(fulldoc, validation_type) else "")
        return fulldoc

    def get_digital_signature_pem(self, comp_id):
        obj = self.env["res.users"].browse([self.env.user.id])
        if not obj.cert:
            obj = self.env["res.company"].browse([comp_id.id])
            if not obj.cert:
                obj = self.env["res.users"].search(
                    domain=[("authorized_users_ids", "=", self.env.user.id)]
                )
            if not obj.cert or self.env.user.id not in \
                    obj.authorized_users_ids.ids:
                return False
        signature_data = {
            "subject_name": obj.name,
            "subject_serial_number": obj.subject_serial_number,
            "priv_key": obj.priv_key,
            "cert": obj.cert,
            "rut_envia": obj.subject_serial_number,
        }
        return signature_data

    def get_digital_signature(self, comp_id):
        obj = self.env["res.users"].browse([self.env.user.id])
        if not obj.cert:
            obj = self.env["res.company"].browse([comp_id.id])
            if not obj.cert:
                obj = self.env["res.users"].search(
                    domain=[("authorized_users_ids", "=", self.env.user.id)]
                )
            if not obj.cert or self.env.user.id not in \
                    obj.authorized_users_ids.ids:
                return False
        signature_data = {
            "subject_name": obj.name,
            "subject_serial_number": obj.subject_serial_number,
            "priv_key": obj.priv_key,
            "cert": obj.cert,
        }
        return signature_data

    def get_resolution_data(self, comp_id):
        resolution_data = {
            "dte_resolution_date": comp_id.dte_resolution_date,
            "dte_resolution_number": comp_id.dte_resolution_number,
        }
        return resolution_data

    @api.multi
    def get_xml_file(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/download/xml/cf/%s" % (self.id),
            "target": "self",
        }

    def format_vat(self, value):
        """ Se Elimina el 0 para prevenir problemas con el sii, ya que las
         muestras no las toma si va con el 0 , y tambien internamente se
          generan problemas"""
        if not value or value == "" or value == 0:
            value = "CL666666666"
            # @TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + "-" + value[10:]
        rut = rut.replace("CL0", "").replace("CL", "")
        return rut

    def digest(self, data):
        sha1 = hashlib.new("sha1", data)
        return sha1.digest()

    @api.multi
    def validar_consumo_folios(self):
        self._validar()
        consumos = self.search(
            [
                ("fecha_inicio", "=", self.fecha_inicio),
                ("state", "not in", ["draft", "Rechazado", "Anulado"]),
                ("company_id", "=", self.company_id.id),
                ("id", "!=", self.id),
            ]
        )
        for r in consumos:
            r.state = "Anulado"
        return self.write({"state": "NoEnviado"})

    def _acortar_str(self, texto, size=1):
        c = 0
        cadena = ""
        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1
        return cadena

    def _es_iva(self, tax):
        if tax.sii_code in [
            14,
            15,
            17,
            18,
            19,
            30,
            31,
            32,
            33,
            34,
            36,
            37,
            38,
            39,
            41,
            47,
            48,
        ]:
            return True
        return False

    def getResumen(self, rec):
        det = collections.OrderedDict()
        det["TpoDoc"] = rec.document_class_id.sii_code
        det["NroDoc"] = int(rec.sii_document_number)
        for a in self.anulaciones:
            if (
                a.rango_inicio <= det["NroDoc"]
                and det["NroDoc"] <= a.rango_final
                and a.tpo_doc.id == rec.document_class_id.id
            ):
                rec.canceled = True
        if rec.canceled:
            det["Anulado"] = "A"
            return det
        Neto = 0
        MntExe = 0
        TaxMnt = 0
        MntTotal = 0
        if "lines" in rec:
            # NC pasar a positivo
            TaxMnt = \
                rec.amount_tax if rec.amount_tax > 0 else rec.amount_tax * -1
            MntTotal = (
                rec.amount_total if rec.amount_total > 0 else
                rec.amount_total * -1)
            Neto = rec.pricelist_id.currency_id.round(
                sum(line.price_subtotal for line in rec.lines)
            )
            if Neto < 0:
                Neto *= -1
            MntExe = rec.exento()
            TasaIVA = (
                self.env["pos.order.line"]
                .search(
                    [("order_id", "=", rec.id), ("tax_ids.amount", ">", 0)],
                    limit=1
                )
                .tax_ids.amount
            )
            Neto -= MntExe
        else:  # si la boleta fue hecha por contabilidad
            for l in rec.line_ids:
                if l.tax_line_id:
                    # supuesto iva único
                    if l.tax_line_id and l.tax_line_id.amount > 0:
                        if self._es_iva(
                            l.tax_line_id
                        ):  # diferentes tipos de IVA retenidos o no
                            if l.credit > 0:
                                TaxMnt += l.credit
                            else:
                                TaxMnt += l.debit
                elif l.tax_ids and l.tax_ids[0].amount > 0:
                    if l.credit > 0:
                        Neto += l.credit
                    else:
                        Neto += l.debit
                # caso monto exento
                elif l.tax_ids and l.tax_ids[0].amount == 0:
                    if l.credit > 0:
                        MntExe += l.credit
                    else:
                        MntExe += l.debit
            TasaIVA = (
                self.env["account.move.line"]
                .search(
                    [("move_id", "=", rec.id),
                     ("tax_line_id.amount", ">", 0)], limit=1
                )
                .tax_line_id.amount
            )
            MntTotal = Neto + MntExe + TaxMnt
        if MntExe > 0:
            det["MntExe"] = self.currency_id.round(MntExe)
        if TaxMnt > 0:
            det["MntIVA"] = self.currency_id.round(TaxMnt)
            det["TasaIVA"] = TasaIVA
        det["MntNeto"] = self.currency_id.round(Neto)
        det["MntTotal"] = self.currency_id.round(MntTotal)
        return det

    def _last(self, folio, items):
        # se asumen que vienen ordenados de menor a mayor
        last = False
        for c in items:
            if folio > c["Final"] and folio > c["Inicial"]:
                if not last or last["Inicial"] < c["Inicial"]:
                    last = c
        return last

    def _nuevo_rango(self, folio, f_contrario, contrarios):
        last = self._last(
            folio, contrarios
        )  # obtengo el último tramo de los contrarios
        if last and last["Inicial"] > f_contrario:
            return True
        return False

    def _orden(self, folio, rangos, contrarios, continuado=True):
        last = self._last(folio, rangos)
        if (
            not continuado
            or not last
            or self._nuevo_rango(folio, last["Final"], contrarios)
        ):
            r = collections.OrderedDict()
            r["Inicial"] = folio
            r["Final"] = folio
            rangos.append(r)
            return rangos
        result = []
        for r in rangos:
            if r["Final"] == last["Final"] and folio > last["Final"]:
                r["Final"] = folio
            result.append(r)
        return result

    def _rangosU(self, resumen, rangos, continuado=True):
        if not rangos:
            rangos = collections.OrderedDict()
        folio = resumen["NroDoc"]
        if "Anulado" in resumen and resumen["Anulado"]:
            utilizados = rangos["itemUtilizados"] if "itemUtilizados" in \
                                                     rangos else []
            if "itemAnulados" not in rangos:
                rangos["itemAnulados"] = []
                r = collections.OrderedDict()
                r["Inicial"] = folio
                r["Final"] = folio
                rangos["itemAnulados"].append(r)
            else:
                rangos["itemAnulados"] = self._orden(
                    resumen["NroDoc"], rangos["itemAnulados"], utilizados,
                    continuado)
            return rangos
        anulados = rangos["itemAnulados"] if "itemAnulados" in rangos else []
        if "itemUtilizados" not in rangos:
            rangos["itemUtilizados"] = []
            r = collections.OrderedDict()
            r["Inicial"] = folio
            r["Final"] = folio
            rangos["itemUtilizados"].append(r)
        else:
            rangos["itemUtilizados"] = self._orden(
                resumen["NroDoc"], rangos["itemUtilizados"], anulados,
                continuado)
        return rangos

    def _setResumen(self, resumen, resumenP, continuado=True):
        resumenP["TipoDocumento"] = resumen["TpoDoc"]
        if "Anulado" not in resumen:
            if "MntNeto" in resumen and "MntNeto" not in resumenP:
                resumenP["MntNeto"] = resumen["MntNeto"]
            elif "MntNeto" in resumen:
                resumenP["MntNeto"] += resumen["MntNeto"]
            elif "MntNeto" not in resumenP:
                resumenP["MntNeto"] = 0
            if "MntIVA" in resumen and "MntIva" not in resumenP:
                resumenP["MntIva"] = resumen["MntIVA"]
            elif "MntIVA" in resumen:
                resumenP["MntIva"] += resumen["MntIVA"]
            elif "MntIva" not in resumenP:
                resumenP["MntIva"] = 0
            if "TasaIVA" in resumen and "TasaIVA" not in resumenP:
                resumenP["TasaIVA"] = resumen["TasaIVA"]
            if "MntExe" in resumen and "MntExento" not in resumenP:
                resumenP["MntExento"] = resumen["MntExe"]
            elif "MntExe" in resumen:
                resumenP["MntExento"] += resumen["MntExe"]
            elif "MntExento" not in resumenP:
                resumenP["MntExento"] = 0
        if "MntTotal" not in resumenP:
            resumenP["MntTotal"] = resumen.get("MntTotal", 0)
        else:
            resumenP["MntTotal"] += resumen.get("MntTotal", 0)
        if "FoliosEmitidos" in resumenP:
            resumenP["FoliosEmitidos"] += 1
        else:
            resumenP["FoliosEmitidos"] = 1

        if "FoliosAnulados" not in resumenP:
            resumenP["FoliosAnulados"] = 0
        if (
            "Anulado" in resumen
        ):  # opción de indiar de que está anulado por panel SII no por nota
            resumenP["FoliosAnulados"] += 1
        elif "FoliosUtilizados" in resumenP:
            resumenP["FoliosUtilizados"] += 1
        else:
            resumenP["FoliosUtilizados"] = 1
        if not resumenP.get("FoliosUtilizados", False):
            resumenP["FoliosUtilizados"] = 0
        if not str(resumen["TpoDoc"]) + "_folios" in resumenP:
            resumenP[str(resumen["TpoDoc"]) + "_folios"] = \
                collections.OrderedDict()
        resumenP[str(resumen["TpoDoc"]) + "_folios"] = self._rangosU(
            resumen, resumenP[str(resumen["TpoDoc"]) + "_folios"], continuado
        )
        return resumenP

    def _get_resumenes(self, marc=False):
        resumenes = collections.OrderedDict()
        TpoDocs = []
        recs = []
        for rec in self.with_context(lang="es_CL").move_ids:
            document_class_id = (
                rec.document_class_id
                if "document_class_id" in rec
                else rec.sii_document_class_id
            )
            if not document_class_id or document_class_id.sii_code not in \
                    [39, 41, 61]:
                _logger.warning(
                    "Por este medio solamente se pueden declarar Boletas o "
                    "Notas de crédito Electrónicas, por favor elimine el "
                    "documento %s del listado" % rec.name
                )
                continue
            if rec.sii_document_number:
                recs.append(rec)
            # rec.sended = marc
        if (
            "pos.order" in self.env
        ):  # @TODO mejor forma de verificar si está instalado módulo POS
            current = self.fecha_inicio.strftime(DF) + " 00:00:00"
            tz = pytz.timezone("America/Santiago")
            tz_current = \
                tz.localize(datetime.strptime(current, DTF)).astimezone(
                    pytz.utc)
            current = tz_current.strftime(DTF)
            next_day = \
                (tz_current + relativedelta.relativedelta(days=1)).\
                strftime(DTF)
            orders_array = (
                self.env["pos.order"]
                .search(
                    [
                        ("invoice_id", "=", False),
                        ("sii_document_number", "not in", [False, "0"]),
                        ("document_class_id.sii_code", "in", [39, 41, 61]),
                        ("date_order", ">=", current),
                        ("date_order", "<", next_day),
                    ]
                )
                .with_context(lang="es_CL")
            )
            for order in orders_array:
                recs.append(order)
        if recs:
            recs = sorted(recs, key=lambda t: int(t.sii_document_number))
            ant = {}
            for order in recs:
                canceled = hasattr(order, "canceled") and order.canceled
                resumen = self.getResumen(order)
                TpoDoc = str(resumen["TpoDoc"])
                if TpoDoc not in ant:
                    ant[TpoDoc] = [0, canceled]
                if int(order.sii_document_number) == ant[TpoDoc][0]:
                    raise UserError(_(
                        "The folio %s has been duplicated!") %
                        order.sii_document_number)
                if TpoDoc not in TpoDocs:
                    TpoDocs.append(TpoDoc)
                if TpoDoc not in resumenes:
                    resumenes[TpoDoc] = collections.OrderedDict()
                continuado = (ant[TpoDoc][0] + 1) == int(
                    order.sii_document_number
                ) and (ant[TpoDoc][1]) == canceled
                resumenes[TpoDoc] = self._setResumen(
                    resumen, resumenes[TpoDoc], continuado
                )
                ant[TpoDoc] = [int(order.sii_document_number), canceled]
        for an in self.anulaciones:
            TpoDoc = str(an.tpo_doc.sii_code)
            if TpoDoc not in TpoDocs:
                TpoDocs.append(TpoDoc)
            if TpoDoc not in resumenes:
                resumenes[TpoDoc] = collections.OrderedDict()
            i = an.rango_inicio
            while i <= an.rango_final:
                continuado = False
                seted = False
                for r, value in resumenes.items():
                    Rangos = value.get(str(r) + "_folios",
                                       collections.OrderedDict())
                    if "itemAnulados" in Rangos:
                        for rango in Rangos["itemAnulados"]:
                            if rango["Inicial"] <= i and i <= rango["Final"]:
                                seted = True
                            if not (seted) and (i - 1) == rango["Final"]:
                                continuado = True
                if not seted:
                    resumen = {"TpoDoc": TpoDoc, "NroDoc": i, "Anulado": "A"}
                    if not resumenes.get(TpoDoc):
                        resumenes[TpoDoc] = collections.OrderedDict()
                    resumenes[TpoDoc] = self._setResumen(
                        resumen, resumenes[TpoDoc], continuado
                    )
                i += 1
        return resumenes, TpoDocs

    def _validar(self):
        company_id = self.company_id
        signature_d = self.env.user.get_digital_signature(self.company_id)
        if not signature_d:
            raise UserError(_(
                """There is no Signer Person with an authorized signature for
                you in the system. Please make sure that 'user_signature_key'
                module has been installed and enable a digital signature, for
                you or make the signer to authorize you to use his
                signature."""))
        certp = signature_d["cert"].replace(BC, "").replace(EC, "").\
            replace("\n", "")
        resumenes, TpoDocs = self._get_resumenes(marc=True)
        Resumen = []
        listado = [
            "TipoDocumento",
            "MntNeto",
            "MntIva",
            "TasaIVA",
            "MntExento",
            "MntTotal",
            "FoliosEmitidos",
            "FoliosAnulados",
            "FoliosUtilizados",
            "itemUtilizados",
        ]
        xml = "<Resumen>" \
              "<TipoDocumento>39</TipoDocumento>" \
              "<MntTotal>0</MntTotal>" \
              "<FoliosEmitidos>0</FoliosEmitidos>" \
              "<FoliosAnulados>0</FoliosAnulados>" \
              "<FoliosUtilizados>0</FoliosUtilizados>" \
              "</Resumen>"
        if resumenes:
            for r, value in resumenes.items():
                ordered = collections.OrderedDict()
                for i in listado:
                    if i in value:
                        ordered[i] = value[i]
                    elif i == "itemUtilizados":
                        Rangos = value[str(r) + "_folios"]
                        folios = []
                        if "itemUtilizados" in Rangos:
                            utilizados = []
                            for rango in Rangos["itemUtilizados"]:
                                utilizados.append({"RangoUtilizados": rango})
                            folios.append({"itemUtilizados": utilizados})
                        if "itemAnulados" in Rangos:
                            anulados = []
                            for rango in Rangos["itemAnulados"]:
                                anulados.append({"RangoAnulados": rango})
                            folios.append({"itemAnulados": anulados})
                        ordered[str(r) + "_folios"] = folios
                Resumen.extend([{"Resumen": ordered}])
            dte = collections.OrderedDict({"item": Resumen})
            xml = \
                dicttoxml.dicttoxml(dte, root=False, attr_type=False).decode()
        resol_data = self.get_resolution_data(company_id)
        RUTEmisor = self.format_vat(company_id.vat)
        doc_id = "CF_" + self.date.strftime(DF)
        Correlativo = self.correlativo
        SecEnvio = self.sec_envio
        cf = self.create_template_envio(
            RUTEmisor,
            resol_data["dte_resolution_date"],
            resol_data["dte_resolution_number"],
            self.fecha_inicio,
            self.fecha_final,
            Correlativo,
            SecEnvio,
            xml,
            signature_d,
            doc_id,
        )
        xml = self.create_template_env(cf)
        root = etree.XML(xml)
        xml_pret = (
            etree.tostring(root, pretty_print=True)
            .decode()
            .replace("<item>", "\n")
            .replace("</item>", "")
            .replace("<itemNoRec>", "")
            .replace("</itemNoRec>", "\n")
            .replace("<itemOtrosImp>", "")
            .replace("</itemOtrosImp>", "\n")
            .replace("<itemUtilizados>", "")
            .replace("</itemUtilizados>", "\n")
            .replace("<itemAnulados>", "")
            .replace("</itemAnulados>", "\n")
        )
        for TpoDoc in TpoDocs:
            xml_pret = (
                xml_pret.replace('<key name="' + str(TpoDoc) + '_folios">', "")
                .replace("</key>", "\n")
                .replace('<key name="' + str(TpoDoc) + '_folios"/>', "\n")
            )
        envio_dte = self.sign_full_xml(
            xml_pret, signature_d["priv_key"], certp, doc_id, "consu"
        )
        doc_id += ".xml"
        self.sii_xml_request = envio_dte
        return envio_dte, doc_id

    @api.multi
    def do_dte_send_consumo_folios(self):
        if self.state not in ["NoEnviado", "Rechazado"]:
            raise UserError(_("The ledger has already been sent."))
        envio_dte, doc_id = self._validar()
        company_id = self.company_id
        result = self.env["account.move.book"].send_xml_file(
            envio_dte, doc_id, company_id
        )
        if result["sii_result"] == "Enviado":
            self.env["sii.cola_envio"].create(
                {
                    "doc_ids": [self.id],
                    "model": "account.move.consumo_folios",
                    "user_id": self.env.user.id,
                    "tipo_trabajo": "consulta",
                }
            )
        self.write(
            {
                "sii_xml_response": result["sii_xml_response"],
                "sii_send_ident": result["sii_send_ident"],
                "state": result["sii_result"],
                "sii_xml_request": envio_dte,
            }
        )

    def _get_send_status(self):
        token = self.env["sii.xml.envio"].get_token(self.env.user,
                                                    self.company_id)
        url = server_url[self.company_id.dte_service_provider] + \
            "QueryEstUp.jws?WSDL"
        _server = Client(url)
        try:
            respuesta = _server.service.getEstUp(
                self.company_id.vat[2:-1],
                self.company_id.vat[-1],
                self.sii_send_ident,
                token,
            )
        except:
            raise UserError(_("SII Service Temporarily Unavailable 503"))
        self.sii_message = respuesta
        resp = xmltodict.parse(respuesta)
        status = False
        if resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] == "-11":
            status = {
                "warning": {
                    "title": _("Error -11"),
                    "message": _(
                        "Error -11: Espere a que sea aceptado por el SII, "
                        "intente en 5s más"
                    ),
                }
            }
        if resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] == "EPR":
            self.state = "Proceso"
            if (
                "SII:RESP_BODY" in resp["SII:RESPUESTA"]
                and resp["SII:RESPUESTA"]["SII:RESP_BODY"]["RECHAZADOS"] == "1"
            ):
                self.sii_result = "Rechazado"
        elif resp["SII:RESPUESTA"]["SII:RESP_HDR"]["ESTADO"] in \
                ["RCT", "RCH", "RSC"]:
            self.state = "Rechazado"
            status = {
                "warning": {
                    "title": _("Error RCT"),
                    "message": _(resp["SII:RESPUESTA"]["SII:RESP_HDR"]
                                 ["GLOSA"]),
                }
            }
        return status

    @api.multi
    def ask_for_dte_status(self):
        if self.state == "Enviado":
            status = self._get_send_status()
            if self.state != "Proceso":
                return status


class DetalleCOnsumoFolios(models.Model):
    _name = "account.move.consumo_folios.detalles"
    _description = "Account Move Consumo Folios Detalles"

    cf_id = fields.Many2one("account.move.consumo_folios",
                            string="Consumo de Folios")
    tpo_doc = fields.Many2one("sii.document.class",
                              string="Tipo de Documento")
    tipo_operacion = fields.Selection(
        [("utilizados", "Utilizados"), ("anulados", "Anulados")]
    )
    folio_inicio = fields.Integer(string="Folio Inicio")
    folio_final = fields.Integer(string="Folio Final")
    cantidad = fields.Integer(string="Cantidad Emitidos")


class DetalleImpuestos(models.Model):
    _name = "account.move.consumo_folios.impuestos"
    _description = "Account Move Consumo Folios Impuestos"

    cf_id = fields.Many2one("account.move.consumo_folios",
                            string="Consumo de Folios")
    tpo_doc = fields.Many2one("sii.document.class", string="Tipo de Documento")
    impuesto = fields.Many2one("account.tax")
    cantidad = fields.Integer(string="Cantidad")
    monto_neto = fields.Monetary(string="Monto Neto")
    monto_iva = fields.Monetary(string="Monto IVA")
    monto_exento = fields.Monetary(string="Monto Exento")
    monto_total = fields.Monetary(string="Monto Total")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility="always",
    )


class Anulaciones(models.Model):
    _name = "account.move.consumo_folios.anulaciones"
    _description = "Account Move Consumo Folios Anulaciones"

    cf_id = fields.Many2one("account.move.consumo_folios",
                            string="Consumo de Folios")
    tpo_doc = fields.Many2one(
        "sii.document.class",
        string="Tipo de documento",
        required=True,
        domain=[("sii_code", "in", [39, 41, 61])],
    )
    rango_inicio = fields.Integer(required=True, string="Rango Inicio")
    rango_final = fields.Integer(required=True, string="Rango Final")
