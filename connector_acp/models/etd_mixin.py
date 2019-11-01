# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import logging
from collections import namedtuple
from jinja2 import Environment, BaseLoader
# TODO: Uncomment when the XSD validation works
# from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...queue_job.job import job
from ...queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)


class EtdMixin(models.AbstractModel):
    _name = 'etd.mixin'
    _description = 'Electronic Tax Document Mixin'

    signature_id = fields.Many2one(
        'etd.signature', string='SSL Signature',
        help="SSL Signature of the Document")

    _env = None
    File_details = namedtuple('file_details', ['filename', 'filecontent'])

    @api.model
    def set_jinja_env(self):
        """Set the Jinja2 environment.
        The environment will helps the system to find the templates to render.
        :return: jinja2.Environment instance.
        """
        if self._env is None:
            self._env = Environment(
                lstrip_blocks=True,
                trim_blocks=True,
                loader=BaseLoader())
        return self._env

    def get_etd_document(self):
        """
        Return one res.company.document to generate the XML file of the record
        :return: The res.company.document that needs be used to generate the
         XML file
        """
        res = self.company_id.etd_ids.filtered(
            lambda x: x.model == self._name)
        return res

    def prepare_keywords(self):
        """
        Returns a dictionary of keywords used in the template
        :return: Dictionary of keywords used in the template
        """
        return {}

    def get_etd_filename(self):
        return self.name or self.number

    def build_xml(self):
        """
        Build the XML of the record using the company documents and the
        related XML template and XSD
        :return: XML string of the record
        """
        self.set_jinja_env()
        etd_id = self.get_etd_document()
        # Get the template
        template = self._env.from_string(base64.b64decode(etd_id.xml).
                                         decode('utf-8'))
        # Additional keywords used in the template
        kwargs = self.prepare_keywords()
        kwargs.update({
            'o': self,
            'now': fields.datetime.now(),
            'today': fields.datetime.today()})
        xml_filename = self.get_etd_filename()
        # Render the XML
        xml_file = self.File_details(xml_filename + '.xml',
                                     template.render(kwargs))
        # TODO: Uncomment once the XSD validation works
        # xml = str.encode(xml_file.filecontent)
        # Attache XML file to the document
        self.env['ir.attachment'].create({
            'name': xml_file.filename,
            'type': 'binary',
            'datas': base64.b64encode(xml_file.filecontent.encode("utf-8")),
            'datas_fname': xml_file.filename,
            'res_model': self._name,
            'res_id': self.id})
        # TODO: Uncomment once the XSD files are properly formed
        # Check the rendered XML against the XSD
        # xsd = base64.b64decode(document_id.xsd).decode('utf-8')
        # try:
        #     xmlschema = etree.XMLSchema(xsd)
        #     xml_doc = etree.fromstring(xml)
        #     result = xmlschema.validate(xml_doc)
        #     if not result:
        #         xmlschema.assert_(xml_doc)
        #     return xml
        # except AssertionError as e:
        #     _logger.warning(etree.tostring(xml_doc))
        #     raise UserError(_("XML Malformed Error: %s") % e.args)

    def sign_xml(self, xml):
        """
        Sign the XML using the certificate
        Store the signature and link it to the record
        :param xml: XML string of the record
        :param certificate: SSL Certificate record
        :return: XML string with the SSL signature included
        """
        return True

    @job
    def document_sign(self):
        """
        Sign or get the document signed, attach the ETD to the record and log
         a message in the chatter with the status
        :param res_model: ir.model of the document to sign
        :param res_id: id of the document to sign
        """
        # Build the XML of the document
        xml = self.build_xml()
        # Sign the document
        if self.company_id.signer == 'odoo':
            # Use the SSL Certificate to sign the XML
            xml = self.sign_xml(xml)
            # Use the backend of the Tax Authority
            backend = self.company_id.partner_id.country_id.backend_acp_id
        else:
            # Use the backend of the ACP
            backend = self.company_id.backend_acp_id
        # Determine the backend to send the XML
        if backend.status != 'confirmed':
            raise UserError(_("The backend is not confirmed. Please check the"
                              " connection to the backend first."))
        # Send the XML to backend
        reply = backend.send(xml)
        # Send the XML
        if reply:
            # Check the status of the document
            status = backend.check_status()
            message = _("%s Status: <b>%s</b>" % (backend.name, status))
            self.message_post(body=message)
        else:
            message = _("ETD has been sent to %s but failed with"
                        " the following message: <b>%s</b>" %
                        (backend.name, reply))
            self.message_post(body=message)
            raise RetryableJobError(reply)
