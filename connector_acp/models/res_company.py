# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    document_ids = fields.Many2many("res.company.document",
                                   string="Documents To Sign")
    signer = fields.Selection((
        ("odoo", "Odoo"),
        ("backend", "Third Party")), string="Who is signing?",
        required=True, default="odoo",
        help="""Please note that the signing authority is in charge of
        sending the document for validation.""")
    backend_id = fields.Many2one("backend.acp", string="Third Party")
    cert_id = fields.Many2one("ssl.certificate", string="SSL Certificate")
