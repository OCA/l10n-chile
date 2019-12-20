# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import tempfile
import shutil
from odoo import fields, models


class BackendAcp(models.Model):
    _inherit = "backend.acp"
    _description = "Backend of Authorized Certification Providers"

    connection_type = fields.Selection(selection_add=[('ftp', 'FTP')])

    def _send_ftp_files(self, tempdir):
        """Send FTP files to the temp.

        This method is used to upload all file in temp directory.
        """
        pass

    def send(self, files):
        """Send the files to the backend.

        :param files: List of dictionary with 'name' for the filename and
        'content' for the content
        :return: A dictionary with:
         - a boolean 'success': True if the transfer was successful,
          False otherwise
         - a string 'message': Message to be displayed to the end user
         - a string 'ref': Reference of the transfer to request the status
        """
        for rec in self:
            if rec.connection_type == 'ftp':
                for file in files:
                    if file.get('directory'):
                        file_dir = rec._send_ftp_files(file.get('directory'))
                        doc_directory_name = tempfile.mkdtemp()
                        doc_filename = (
                            file.get('directory') + "/%s/%s" % (
                                file_dir, file.get('name')))
                        file_content = open(doc_filename, 'wb')
                        file_content.write(file.get('content'))
                        rec._send_ftp_files()
                        shutil.rmtree(doc_directory_name)
        return super(BackendAcp, self).send(files)
