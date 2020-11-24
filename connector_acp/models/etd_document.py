# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


@api.model
def _get_model_list(self):
    ETDDoc = self.env['etd.document']
    return ETDDoc._fields['model'].selection


class EtdDocument(models.Model):
    _name = "etd.document"
    _description = "Electronic Tax Documents To Sign"

    name = fields.Char(string="Name", required=True)
    model = fields.Selection([], string="Odoo Model", required=True)
    invoicing_policy = fields.Selection(
        [("ticket", "Ticket"), ("invoice", "Invoice"), ("eguide", "Electronic Guide")],
    )
    file_ids = fields.One2many("etd.document.file", "document_id", string="Files")
    test_document = fields.Reference(_get_model_list)
    template_text_include = fields.Text(
        string="Include Template Text",
        help="Common text template to add "
        "at the header of file name and file content text templates. "
        "Use to set common variables reused in the several file templates."
    )
