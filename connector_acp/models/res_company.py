# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    etd_ids = fields.Many2many("etd.document", string="Documents To Sign")
    signer = fields.Selection(
        (("odoo", "Odoo"), ("backend", "Authorized Certification Provider")),
        string="Who is signing?",
        required=True,
        default="odoo",
        help="""Please note that the signing authority is in charge of
        sending the document for validation.""",
    )
    backend_acp_id = fields.Many2one(
        "backend.acp", string="Authorized Certification Provider"
    )
    cert_id = fields.Many2one("etd.certificate", string="SSL Certificate")
