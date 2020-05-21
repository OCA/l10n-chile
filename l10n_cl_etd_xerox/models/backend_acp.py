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
    send_immediately = fields.Boolean(
        default=True,
        help="Send documents immediately to this backend"
        " Otherwise they should wait to be sent by a"
        " background scheduler job.",
    )

    @api.model
    def _build_xerox_control_file(self, file_dict):
        res = {}
        index = 0
        ctl_legal = self.xerox_company_code + self.xerox_company_short_name
        ctl_legal += "" if self.prod_environment else "Desa"
        ctl_no_legal = "Ctl" if self.prod_environment else "00CtlDesa"
        today = fields.Date.context_today(self)
        code = self.env.context.get('xerox', False)
        if code in (33, 34, 39, 41, 52, 56, 61):
            PREFIX = 'dte_ctr_' + self.xerox_company_code + '_0' + str(code)
            ctl = ctl_legal
        else:
            PREFIX = 'dte_ctr_ot_000_'
            ctl = ctl_no_legal

        for file_path, file_text in file_dict.items():
            file_dir, file_name = os.path.split(file_path)
            control_name = PREFIX + file_name[len(PREFIX):]
            control_path = os.path.join(ctl + '/', control_name)
            res.setdefault(control_path, '')
            # Xerox Path
            xerox_code = file_name[47:52]
            xerox_path = self.xerox_path % (
                today.strftime("%m"), xerox_code, today.strftime("%d"))
            # 'Ctl'/'00CtlDesa' for non-legal documents
            # '81Man'/'81ManDesa' for legal ones
            ctl_file = ctl_no_legal if file_name[8:10] == "ot" else ctl_legal
            # Number of lines of the file
            line_count = len(file_text.rstrip().splitlines())
            # Generate the line of the file
            control_line = '%s;%s;%s;%d\n' % (
                file_name, xerox_path, ctl_file, line_count)
            res[control_path] += control_line
            index += 1
        # Adding the control file in its own content
        res[control_path] += '%s;%s;%s;%d\n' % (
            control_name, xerox_path, ctl_no_legal, index + 1)
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
