# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import logging
import time
from collections import namedtuple
from jinja2 import Environment, BaseLoader
from lxml import etree
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
        Return one etd.document to generate the XML file of the record
        :return: The etd.document that needs be used to generate the
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

    def get_etd_filename(self, file):
        return '%s.%s' % (self.name or self.number, file.file_type)

    def build_file(self, file):
        """
        Build the file of the record using the company documents and the
        related template and
        :return: A dictionary with the filename and the content
        """
        self.set_jinja_env()
        # Get the template
        template = self._env.from_string(base64.b64decode(file.template).
                                         decode('utf-8'))
        # Additional keywords used in the template
        kwargs = self.prepare_keywords()
        kwargs.update({
            'o': self,
            'now': fields.datetime.now(),
            'today': fields.datetime.today()})
        filename = self.get_etd_filename(file)
        # Render the file
        res_file = self.File_details(filename, template.render(kwargs))
        res_content = str.encode(res_file.filecontent)
        if file.validator:
            # Check the rendered file against the validator
            validator = base64.b64decode(file.validator).decode('utf-8')
            if file.file_type == "xml":
                try:
                    xmlschema = etree.XMLSchema(validator)
                    xml_doc = etree.fromstring(res_content)
                    result = xmlschema.validate(xml_doc)
                    if not result:
                        xmlschema.assert_(xml_doc)
                except AssertionError as e:
                    _logger.warning(etree.tostring(xml_doc))
                    raise UserError(_("XML Malformed Error: %s") % e.args)
        # Attach file to the record
        if file.save:
            self.env['ir.attachment'].create({
                'name': res_file.filename,
                'type': 'binary',
                'datas':
                    base64.b64encode(res_file.filecontent.encode("utf-8")),
                'datas_fname': res_file.filename,
                'res_model': self._name,
                'res_id': self.id})
        return {'name': filename, 'content': res_content}

    def build_files(self):
        """
        Build the files and returns a dictionary with file name and string
        :return: Dictionary of file and string
        """
        # Get the document
        etd = self.get_etd_document()
        res = []
        for file in etd.file_ids:
            res.append(self.build_file(file))
        return res

    def sign_files(self, files, certificate):
        """
        Sign the file using the certificate
        Store the signature and link it to the record
        :param files: List of string
        :param certificate: SSL Certificate record
        :return: XML string with the SSL signature included
        """
        for file in files:
            pass
        return True

    @job
    def document_sign(self):
        """
        Sign or get the document signed, attach the ETD to the record and log
         a message in the chatter with the status
        :param res_model: ir.model of the document to sign
        :param res_id: id of the document to sign
        """
        # Build the files for the document
        files = self.build_files()
        # Sign the document
        if self.company_id.signer == 'odoo':
            # Use the SSL Certificate to sign the files
            files = self.sign_files(files, self.company_id.cert_id)
            # Use the backend of the Tax Authority
            backend = self.company_id.partner_id.country_id.backend_acp_id
        else:
            # Use the backend of the ACP
            backend = self.company_id.backend_acp_id
        # Determine if the backend is usable
        if backend.status != 'confirmed':
            raise UserError(_("The backend is not confirmed. Please check the"
                              " connection to the backend first."))
        # Send the files to backend
        response = backend.send(files)
        # Check the response
        if response.success:
            # Check the status of the document
            status = backend.check_status(response.ref)
            i = 1
            while not (status and status.success):
                time.sleep(i)
                i += 1
                status = backend.check_status(response.ref)
            message = _("%s Status: <b>%s</b>" % (backend.name,
                                                  status.message))
            self.message_post(body=message)
        else:
            message = _("ETD has been sent to %s but failed with"
                        " the following message: <b>%s</b>" %
                        (backend.name, response.message))
            self.message_post(body=message)
            raise RetryableJobError(response)
