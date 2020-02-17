# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import os
from odoo import api, fields, models


class BackendAcp(models.Model):
    _inherit = "backend.acp"

    send_immediately = fields.Boolean(
        default=True,
        help="Send documents immediately to this backend"
        " Otherwise they should wait to be sent by a"
        " backgroung scheduler job.",
    )

    @api.model
    def _build_xerox_control_file(self, file_dict):
        PREFIX = 'dte_ctr_ot_000'
        res = {}
        for file_path, file_text in file_dict.items():
            file_dir, file_name = os.path.split(file_path)
            control_name = PREFIX + file_name[len(PREFIX):]
            control_path = os.path.join(file_dir, control_name)
            res.setdefault(control_path, '')
            line_count = len(file_text.rstrip().splitlines())
            control_line = '%s;%s;%d\n' % (
                file_name, file_dir, line_count)
            res[control_path] += control_line
        return res

    def _send_ftp(self, file_dict):
        """
        After uploading files, build and upload
        the corresponding control files.
        """
        res = super()._send_ftp(file_dict)
        control_file_dict = self._build_xerox_control_file(file_dict)
        res = super()._send_ftp(control_file_dict)
        return res
