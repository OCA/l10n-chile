# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import os
import tempfile
import shutil
import ftplib
from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class BackendAcp(models.Model):
    _inherit = "backend.acp"

    connection_type = fields.Selection(selection_add=[("ftp", "FTP")])

    @api.model
    def _ftp_upload_directory(self, ftp_session, from_local_dir, to_server_dir):
        """
        Given a local directory, upload all files and subdirs.
        - change server work directory
        - search files in local directory, and upload them
        - search subdirs in local directory, and recursively upload them
        """
        # List and upload files
        ftp_session.cwd(to_server_dir)
        from_path, subdir_list, file_list = next(os.walk(from_local_dir))
        for file_name in file_list:
            file_path = os.path.join(from_path, file_name)
            with open(file_path, "rb") as file_obj:
                ftp_session.storlines("STOR %s" % file_name, file_obj)
        for subdir in subdir_list:
            if subdir not in ftp_session.nlst():
                ftp_session.mkd(subdir)
            self._ftp_upload_directory(
                ftp_session, os.path.join(from_local_dir, subdir), subdir
            )

    def _ftp_upload(self, from_local_dir, to_server_dir="."):
        """Send FTP files to the temp.

        This method is used to upload all file in temp directory.
        """
        self.ensure_one()
        with ftplib.FTP() as ftp:
            ftp.connect(self.host, self.port or 21)
            ftp.login(self.user, self.password)
            # if no local dir given, just try connection and exit
            if from_local_dir:
                self._ftp_upload_directory(ftp, from_local_dir, to_server_dir)

    def action_confirm(self):
        self.ensure_one()
        if self.connection_type == "ftp":
            # Interruped with an error if connection fails
            self._ftp_upload(None)
        return super().action_confirm()

    def _send_ftp(self, file_dict):
        temp_dir = tempfile.mkdtemp()
        _logger.info("FTP uploading %d files from %s" % (
            len(file_dict), temp_dir))
        for file_path, file_content in file_dict.items():
            if file_path.startswith("/"):
                file_path = file_path[1:]
            file_dir, file_name = os.path.split(file_path)
            full_dir = os.path.join(temp_dir, file_dir)
            full_path = os.path.join(full_dir, file_name)
            os.makedirs(full_dir, exist_ok=True)
            with open(full_path, "w") as file_obj:
                file_obj.write(file_content)
        self._ftp_upload(temp_dir)
        shutil.rmtree(temp_dir)
        return {"success": True, "message": "OK"}

    def send(self, file_dict):
        """Send the files to the backend.

        :param file_dict dictionary with 'name' for the filename and
        'content' for the content
        :return: A dictionary with:
         - a boolean 'success': True if the transfer was successful,
          False otherwise
         - a string 'message': Message to be displayed to the end user
         - a string 'ref': Reference of the transfer to request the status
        """
        self and self.ensure_one()
        if self.connection_type == "ftp" and file_dict:
            return self._send_ftp(file_dict)
        else:
            return super(BackendAcp, self).send(file_dict)
