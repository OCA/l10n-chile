# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
from datetime import datetime
import re
import logging
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
try:
    from OpenSSL import crypto

    type_ = crypto.FILETYPE_PEM
except ImportError:
    _logger.warning("Error importing crypto")

zero_values = {
    "filename": "",
    "key_file": False,
    "dec_pass": "",
    "not_before": False,
    "not_after": False,
    "status": "unverified",
    "final_date": False,
    "subject_title": "",
    "subject_c": "",
    "subject_serial_number": "",
    "subject_common_name": "",
    "subject_email_address": "",
    "issuer_country": "",
    "issuer_serial_number": "",
    "issuer_common_name": "",
    "issuer_email_address": "",
    "issuer_organization": "",
    "cert_serial_number": "",
    "cert_signature_algor": "",
    "cert_version": "",
    "cert_hash": "",
    "private_key_bits": "",
    "private_key_check": "",
    "private_key_type": "",
    "cacert": "",
    "cert": "",
}


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_default_tp_type(self):
        try:
            return self.env.ref("l10n_cl_electronic_invoicing.res_IVARI")
        except:
            return self.env["sii.responsability"]

    def _get_default_doc_type(self):
        try:
            return self.env.ref("l10n_cl_electronic_invoicing.dt_RUT")
        except:
            return self.env["sii.document.type"]

    dte_email = fields.Char(
        string="DTE Email", related="partner_id.dte_email", readonly=False
    )

    dte_service_provider = fields.Selection(
        (("SIICERT", "SII - Certification process"), ("SII", "www.sii.cl")),
        string="DTE Service Provider",
        help="""Please select your company service \
provider for DTE service.
    """,
        default="SIICERT",
    )
    dte_resolution_number = fields.Char(
        string="SII Exempt Resolution Number",
        help="""This value must be provided \
and must appear in your pdf or printed tribute document, under the electronic \
stamp to be legally valid.""",
        default="0",
    )
    dte_resolution_date = fields.Date("SII Exempt Resolution Date")
    sii_regional_office_id = fields.Many2one(
        "sii.regional.offices", string="SII Regional Office"
    )
    state_id = fields.Many2one(
        related="partner_id.state_id",
        readonly=False,
        relation="res.country.state",
        string="Ubication",
    )
    company_activities_ids = fields.Many2many(
        "partner.activities",
        id1="company_id",
        id2="activities_id",
        string="Activities Names",
    )
    responsability_id = fields.Many2one(
        related="partner_id.responsability_id",
        readonly=False,
        relation="sii.responsability",
        string="Responsability",
        default=lambda self: self._get_default_tp_type(),
    )
    start_date = fields.Date(
        related="partner_id.start_date", readonly=False, string="Start-up Date"
    )
    invoice_vat_discrimination_default = fields.Selection(
        [
            ("no_discriminate_default", "Yes, No Discriminate Default"),
            ("discriminate_default", "Yes, Discriminate Default"),
        ],
        string="Invoice VAT discrimination default",
        default="no_discriminate_default",
        required=True,
        help="""Define behaviour on invoices reports. Discrimination or not \
 will depend in partner and company responsability and SII letters\
        setup:
            * If No Discriminate Default, if no match found it won't \
            discriminate by default.
            * If Discriminate Default, if no match found it would \
            discriminate by default.
            """,
    )
    activity_description = fields.Many2one(
        string="Glosa Giro",
        related="partner_id.activity_description",
        readonly=False,
        relation="sii.activity.description",
    )
    document_number = fields.Char(
        related="partner_id.document_number",
        readonly=False,
        string="Document Number",
        required=True,
    )
    document_type_id = fields.Many2one(
        related="partner_id.document_type_id",
        readonly=False,
        relation="sii.document.type",
        string="Document type",
        default=lambda self: self._get_default_doc_type(),
        required=True,
    )

    @api.onchange("document_number", "document_type_id")
    def onchange_document(self):
        mod_obj = self.env["ir.model.data"]
        if self.document_number and (
            ("sii.document.type", self.document_type_id.id)
            == mod_obj.get_object_reference("l10n_cl_electronic_invoicing",
                                            "dt_RUT")
            or ("sii.document.type", self.document_type_id.id)
            == mod_obj.get_object_reference("l10n_cl_electronic_invoicing",
                                            "dt_RUN")
        ):
            document_number = (
                (re.sub("[^1234567890Kk]", "", str(self.document_number)))
                .zfill(9)
                .upper()
            )
            if not self.partner_id.check_vat_cl(document_number):
                self.vat = ""
                self.document_number = ""
                return {
                    "warning": {"title": _("Rut Erróneo"),
                                "message": _("Rut Erróneo")}
                }
            vat = "CL%s" % document_number
            exist = self.env["res.partner"].search(
                [
                    ("vat", "=", vat),
                    ("vat", "!=", "CL555555555"),
                    ("commercial_partner_id", "!=", self.id),
                ],
                limit=1,
            )
            if exist:
                self.vat = ""
                self.document_number = ""
                return {
                    "warning": {
                        "title": "Informacion para el Usuario",
                        "message": _("El usuario %s está utilizando este "
                                     "documento")
                        % exist.name,
                    }
                }
            self.vat = vat
            self.document_number = "%s.%s.%s-%s" % (
                document_number[0:2],
                document_number[2:5],
                document_number[5:8],
                document_number[-1],
            )
        elif self.document_number and (
            "sii.document.type",
            self.document_type_id.id,
        ) == mod_obj.get_object_reference("l10n_cl_electronic_invoicing",
                                          "dt_Sigd"):
            self.document_number = ""
        else:
            self.vat = ""

    @api.onchange("city_id")
    def _asign_city(self):
        if self.city_id:
            self.country_id = self.city_id.state_id.country_id.id
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name

    def _compute_check_signature(self):
        for s in self:
            if not s.cert:
                s.status = "unverified"
                continue
            expired = s.not_after < fields.Date.context_today(self)
            s.status = "expired" if expired else "valid"

    def load_cert_pk12(self, filecontent):
        try:
            p12 = crypto.load_pkcs12(filecontent, self.dec_pass)
        except UserError:
            raise UserError(_(
                "Error when opening the signature. You may have entered the "
                "wrong key or the file is not compatible."))

        cert = p12.get_certificate()
        privky = p12.get_privatekey()
        issuer = cert.get_issuer()
        subject = cert.get_subject()

        self.not_before = datetime.strptime(
            cert.get_notBefore().decode("utf-8"), "%Y%m%d%H%M%SZ"
        ).date()
        self.not_after = datetime.strptime(
            cert.get_notAfter().decode("utf-8"), "%Y%m%d%H%M%SZ"
        ).date()

        # self.final_date =
        self.subject_c = subject.C
        self.subject_title = subject.title
        self.subject_common_name = subject.CN
        self.subject_serial_number = subject.serialNumber
        self.subject_email_address = subject.emailAddress

        self.issuer_country = issuer.C
        self.issuer_organization = issuer.O
        self.issuer_common_name = issuer.CN
        self.issuer_serial_number = issuer.serialNumber
        self.issuer_email_address = issuer.emailAddress

        self.cert_serial_number = cert.get_serial_number()
        self.cert_signature_algor = cert.get_signature_algorithm()
        self.cert_version = cert.get_version()
        self.cert_hash = cert.subject_name_hash()

        # data privada
        self.private_key_bits = privky.bits()
        self.private_key_check = privky.check()
        self.private_key_type = privky.type()
        # self.cacert = cacert

        certificate = p12.get_certificate()
        private_key = p12.get_privatekey()

        self.priv_key = crypto.dump_privatekey(type_, private_key)
        self.cert = crypto.dump_certificate(type_, certificate)
        self.dec_pass = False

    filename = fields.Char(string="File Name")
    key_file = fields.Binary(
        string="Signature File",
        required=False,
        store=True,
        help="Upload the Signature File")
    dec_pass = fields.Char(string="Pasword")
    # vigencia y estado
    not_before = fields.Date(
        string="Not Before", help="Not Before this Date", readonly=True)
    not_after = fields.Date(
        string="Not After", help="Not After this Date", readonly=True)
    status = fields.Selection(
        [("unverified", "Unverified"),
         ("valid", "Valid"),
         ("expired", "Expired")],
        string="Status",
        compute="_compute_check_signature",
        help="""Draft: means it has not been checked yet.\nYou must press the\
"check" button.""")
    final_date = fields.Date(
        string="Last Date", help="Last Control Date", readonly=True)
    # sujeto
    subject_title = fields.Char(string="Subject Title", readonly=True)
    subject_c = fields.Char(string="Subject Country", readonly=True)
    subject_serial_number = fields.Char(string="Subject Serial Number")
    subject_common_name = fields.Char(
        string="Subject Common Name", readonly=True)
    subject_email_address = fields.Char(string="Subject Email Address",
                                        readonly=True)
    # emisor
    issuer_country = fields.Char(string="Issuer Country", readonly=True)
    issuer_serial_number = fields.Char(string="Issuer Serial Number",
                                       readonly=True)
    issuer_common_name = fields.Char(string="Issuer Common Name",
                                     readonly=True)
    issuer_email_address = fields.Char(string="Issuer Email Address",
                                       readonly=True)
    issuer_organization = fields.Char(string="Issuer Organization",
                                      readonly=True)
    # data del certificado
    cert_serial_number = fields.Char(string="Serial Number", readonly=True)
    cert_signature_algor = fields.Char(string="Signature Algorithm",
                                       readonly=True)
    cert_version = fields.Char(string="Version", readonly=True)
    cert_hash = fields.Char(string="Hash", readonly=True)
    # data privad, readonly=Truea
    private_key_bits = fields.Char(string="Private Key Bits", readonly=True)
    private_key_check = fields.Char(string="Private Key Check", readonly=True)
    private_key_type = fields.Char(string="Private Key Type", readonly=True)
    # cacert = fields.Char('CA Cert', readonly=True)
    cert = fields.Text(string="Certificate", readonly=True)
    priv_key = fields.Text(string="Private Key", readonly=True)
    authorized_users_ids = fields.Many2many("res.users",
                                            string="Authorized Users")

    @api.multi
    def action_clean1(self):
        self.write(zero_values)

    @api.multi
    def action_process(self):
        filecontent = base64.b64decode(self.key_file)
        self.load_cert_pk12(filecontent)
