# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import fields, models


class BackendAcp(models.Model):
    _inherit = "backend.acp"

    send_immediately = fields.Boolean(
        default=True,
        help="Send documents immediately to this backend"
        " Otherwise they should wait to be sent by a"
        " backgroung scheduler job.",
    )
