# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SslSignature(models.Model):
    _name = "ssl.signature"
    _description = "SSL Signature"

    name = fields.Char(string="Name", required=True)
    signature_value = fields.Text(string="Signature Value", required=True)
    exponent = fields.Char(string="Exponent", required=True)
    modulus = fields.Char(string="Modulus", required=True)
    digest_value = fields.Char(string="Digest Value", required=True)
    cert_id = fields.Many2one("ssl.certificate", string="X509 Certificate",
                              required=True)
    model_id = fields.Many2one("ir.model", string="Model", required=True)
    res_id = fields.Integer(string="Record ID", required=True)
