# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class EtdDocument(models.Model):
    _name = "etd.document"
    _description = "Electronic Tax Documents To Sign"

    name = fields.Char(string="Name", required=True)
    model = fields.Selection([], string="Odoo Model", required=True)
    file_ids = fields.One2many("etd.document.file", "document_id",
                               string="Files")
    compress = fields.Selection([
        ("none", "None"), ("zip", "ZIP"), ("tgz", "TAR GZ"),
        ("bzip2", "BZIP2")],
        default="none",
        string="Compression",
        help="Compress the file(s) before sending it")
