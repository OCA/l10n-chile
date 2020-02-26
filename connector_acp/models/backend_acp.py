# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class BackendAcp(models.Model):
    _name = "backend.acp"
    _description = "Backend of Authorized Certification Providers"

    name = fields.Char(string="Name", required=True)
    host = fields.Char(string="Host", required=True)
    port = fields.Integer(string="Port",)
    user = fields.Char(string="User",)
    password = fields.Char(string="Password",)
    active = fields.Boolean(string="Active", default=True)
    status = fields.Selection(
        (("unconfirmed", "Unconfirmed"), ("confirmed", "Confirmed")),
        default="unconfirmed",
        required="True",
    )
    connection_type = fields.Selection(
        [("nd", "Not defined")],
        default="nd",
        required="True",
    )

    @api.onchange('host', 'port', 'user', 'password')
    def onchange_status(self):
        self.status = "unconfirmed"

    def action_confirm(self):
        """
        Called by the Check button on the form view
        Set the status to 'confirmed' if the backend:
         - accepts connections
         - authorizes the given credentials
        :return: True or False whether the backend is usable
        """
        self.status = "confirmed"
        return True

    def send(self, file_dict):
        """
        Send the files to the backend
        :param files: dictionary with 'name' for the filename and
        'content' for the content
        :return: A dictionary with:
         - a boolean 'success': True if the transfer was successful,
          False otherwise
         - a string 'message': Message to be displayed to the end user
         - a string 'ref': Reference of the transfer to request the status
        """
        return {"success": True, "message": "OK", "ref": "1"}

    def check_status(self, ref):
        """
        Check the status of the file processing with the backend
        :param ref: String to identify the files you want to get the status
        :return: A dictionary with:
         - a boolean 'success': True if the status is completed,
                                False otherwise
         - a string 'message': Message to be displayed to the end user
        """
        return {"success": True, "message": "OK"}
