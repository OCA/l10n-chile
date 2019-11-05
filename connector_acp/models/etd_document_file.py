# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class EtdDocumentFile(models.Model):
    _name = "etd.document.file"
    _description = "Template for Electronic Tax Documents To Sign"

    name = fields.Char(string="Name", required=True)
    document_id = fields.Many2one("etd.document", string="Document",
                                  required=True)
    file_type = fields.Selection([("xml", "XML"), ("txt", "TXT")],
                                 default="xml",
                                 string="File Type")
    grouped = fields.Boolean(string="1 file for multiple documents")
    save = fields.Boolean(
        default=True,
        string="Attach the generated file to the record")
    template = fields.Binary(string="Template File")
    validator = fields.Binary(string="Validator File")
