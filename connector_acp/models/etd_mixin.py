# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import base64
import logging
import time
from jinja2 import Environment, BaseLoader
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...queue_job.job import job
from ...queue_job.exception import RetryableJobError


_logger = logging.getLogger(__name__)


class EtdMixin(models.AbstractModel):
    _name = "etd.mixin"
    _description = "Electronic Tax Document Mixin"

    signature_id = fields.Many2one(
        "etd.signature", string="SSL Signature", help="SSL Signature of the Document"
    )

    _env = None

    @api.model
    def set_jinja_env(self):
        """Set the Jinja2 environment.

        The environment will helps the system to find the templates to render.
        :return: jinja2.Environment instance.
        """
        if self._env is None:
            self._env = Environment(
                lstrip_blocks=True, trim_blocks=True, loader=BaseLoader()
            )
        return self._env

    def get_etd_document(self):
        """
        Return one etd.document to generate the XML file of the record.

        :return: The etd.document that needs be used to generate the
         XML file
        """
        res = self.company_id.etd_ids.filtered(lambda x: x.model == self._name)
        return res

    def prepare_keywords(self):
        """Return a dictionary of keywords used in the template.

        :return: Dictionary of keywords used in the template
        """
        return {
            "o": self,
            "now": fields.datetime.now(),
            "today": fields.datetime.today(),
            "date_to_string": fields.Date.to_string,
            "time_to_string": fields.Datetime.to_string,
            "date": datetime.date,
            "datetime": datetime.datetime,
            "timedelta": datetime.timedelta,
        }

    def _render_jinja_template(self, template_text):
        """
        In: self recordset and template string
        Out: string with the processed template
        """
        self.set_jinja_env()
        template = self._env.from_string(template_text)
        # Additional keywords used in the template
        kwargs = self.prepare_keywords()
        # Render the file
        res = template.render(kwargs)
        return res

    def get_etd_template(self, etd_file):
        """
        Get the file template to render.
        """
        file_template = etd_file.template_text or base64.b64decode(
            etd_file.template
        ).decode("utf-8")
        if etd_file.file_type == 'txt':
            # Make text templates more comformatable to edit:
            # Remove initial and trailing whitespace
            # Remove implicit line breaks
            # Consider explicit line breaks entered as "\n"
            file_template = file_template.strip()
            file_template = file_template.replace("\r\n", "")
            file_template = file_template.replace("\n", "")
            file_template = file_template.replace("\\n", "\n")
        return file_template

    def get_etd_filename(self, etd_file):
        """
        Get the file name.
        This can be a relative path with a directory name.
        """
        if etd_file.template_name:
            res = self._render_jinja_template(etd_file.template_name)
        else:
            res = "%s.%s" % (self.display_name, etd_file.file_type)
        return res

    def _build_file(self, etd_file, file_dict=None):
        """Build File.

        Build the file of the record using the company documents and the
        related template.
        file_dict is a dictionary mapping file names (paths) to text content.

        May accept a file_dict, to return with this generated file
        added to it.

        :return: A file_dict dictionary with the filename and the content
        """
        file_dict = file_dict or {}
        for rec in self:
            file_template = rec.get_etd_template(etd_file)
            file_name = rec.get_etd_filename(etd_file)
            file_text = rec._render_jinja_template(file_template)

            if etd_file.grouped:
                # Append text to an already existing file
                prev_file_text = file_dict.get(file_name) or ''
                # TODO: not optimal, consider using a list of lines instead
                file_text = prev_file_text + file_text

            if etd_file.validator and etd_file.file_type == "xml":
                # Check the rendered file against the validator
                validator = base64.b64decode(etd_file.validator).decode("utf-8")
                try:
                    xmlschema = etree.XMLSchema(validator)
                    xml_doc = etree.fromstring(file_text)
                    result = xmlschema.validate(xml_doc)
                    if not result:
                        xmlschema.assert_(xml_doc)
                except AssertionError as e:
                    _logger.warning(etree.tostring(xml_doc))
                    raise UserError(_("XML Malformed Error: %s") % e.args)

            if etd_file.save:
                # Attach file to the record
                self.env["ir.attachment"].create(
                    {
                        "name": file_name,
                        "type": "binary",
                        "datas": base64.b64encode(file_text.encode("utf-8")),
                        "datas_fname": file_name,
                        "res_model": rec._name,
                        "res_id": rec.id,
                    }
                )
            # Update the file_dict with the result
            file_dict[file_name] = file_text
        return file_dict

    def build_files(self, file_dict=None):
        """Build Files.

        Build the files and returns a dictionary with file name and string
        :return: Dictionary of filename and content
        """
        file_dict = file_dict or {}
        etd = self.get_etd_document()
        for etd_file in etd.file_ids:
            file_dict = self._build_file(etd_file, file_dict)
        return file_dict

    def sign_file(self, file_text, certificate):
        """Sign one File.

        Sign the file using the certificate
        Store the signature and link it to the record

        :param file_text:string with the original file content
        :param certificate: SSL Certificate record
        :return: XML string with the SSL signature included
        """
        return file_text  # to implement

    def sign_files(self, file_dict, certificate):
        """Sign Files.

        Sign the file using the certificate

        :param file_dict: dict mapping file names to file text contents
        :param certificate: SSL Certificate record
        :return: dict mapping file names to signed content text strings
        """
        res_dict = {}
        for file_name, file_text in file_dict.items():
            file_signed = self.sign_file(file_text, certificate)
            res_dict[file_name] = file_signed
        return file_dict

    @job
    def document_sign(self):
        """Document Sign.

        Sign or get the document signed, attach the ETD to the record and log
         a message in the chatter with the status
        :param res_model: ir.model of the document to sign
        :param res_id: id of the document to sign
        """
        # Build the files for the document
        file_dict = self.build_files()
        # Sign the document
        if self.company_id.signer == "odoo":
            # Use the SSL Certificate to sign the files
            file_dict = self.sign_files(file_dict, self.company_id.cert_id)
            # Use the backend of the Tax Authority
            backend = self.company_id.partner_id.country_id.backend_acp_id
        else:
            # Use the backend of the ACP
            backend = self.company_id.backend_acp_id
        # Determine if the backend is usable
        if backend.status != "confirmed":
            raise UserError(
                _(
                    "The backend is not confirmed. Please check the"
                    " connection to the backend first."
                )
            )
        # Send the files to backend
        response = backend.send(file_dict)
        # Check the response
        if response.get("success"):
            # Check the status of the document
            status = backend.check_status(response.get("ref"))
            i = 1
            while not (status and status.get('success')):
                time.sleep(i)
                i += 1
                status = backend.check_status(response.get("ref"))
            message = _("%s Status: <b>%s</b>" % (backend.name,
                                                  status.get('message')))
            self.message_post(body=message)
        else:
            message = _(
                "ETD has been sent to %s but failed with"
                " the following message: <b>%s</b>"
                % (backend.name, response.get("message"))
            )
            self.message_post(body=message)
            raise RetryableJobError(response)
        return True
