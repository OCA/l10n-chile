# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import os
from odoo import api, fields, models


class BackendAcp(models.Model):
    _inherit = "backend.acp"

    xerox_company_code = fields.Char(
        help="Use only for Xerox ETD Services")
    xerox_company_short_name = fields.Char(
        help="Use only for Xerox ETD Services")
    xerox_path = fields.Char(
        help="""Use only for Xerox ETD Services:
        * 1st parameter: Current month with 2 digits
        * 2nd parameter: Xerox code from the warehouse with 5 digits
        * 3rd parameter: Current day with 2 digits""")
    xerox_company_queue = fields.Char(
        help="Use only for Xerox ETD Services")
    send_immediately = fields.Boolean(
        default=True,
        help="Send documents immediately to this backend"
        " Otherwise they should wait to be sent by a"
        " background scheduler job.",
    )

    @api.model
    def _build_xerox_control_file(self, file_dict):
        PREFIX = 'dte_ctr_ot_000_'
        res = {}
        index = 0
        ctl_leg = self.xerox_company_code + self.xerox_company_short_name
        ctl_leg += "" if self.prod_environment else "Desa"
        ctl_no_leg = "Ctl" if self.prod_environment else "00CtlDesa"
        today = fields.Date.context_today(self)
        for file_path, file_text in file_dict.items():
            file_dir, file_name = os.path.split(file_path)
            control_name = PREFIX + file_name[len(PREFIX):]
            control_path = os.path.join(file_dir, control_name)
            res.setdefault(control_path, '')
            # Xerox Path
            xerox_code = file_name[47:52]
            xerox_path = self.xerox_path % (
                today.strftime("%m"), xerox_code, today.strftime("%d"))
            # Ctl for non-legal documents, file_set_leg for legal ones
            ctl = ctl_no_leg if file_name[8:10] == "ot" else ctl_leg
            # Number of lines of the file
            line_count = len(file_text.rstrip().splitlines())
            # Generate the line of the file
            control_line = '%s;%s;%s;%d\n' % (
                file_name, xerox_path, ctl, line_count)
            res[control_path] += control_line
            index += 1
        # Adding the control file in its own content
        ctl = "Ctl" if self.prod_environment else "00CtlDesa"
        res[control_path] += '%s;%s;%s;%d\n' % (
            control_name, xerox_path, ctl, index + 1)
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
