# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ref_etd = fields.Char(
        string="ETD Code", size=8,
        help="Product code used for electronic invoicing and shipping. "
             "Limited to 8 digits. Unique by company.")

    _sql_constraints = [(
        "company_ref_etd",
        "unique(company_id, ref_etd)",
        "ETD code must be unique per company!"
    )]

    @api.constrains('ref_etd')
    def check_ref_etd(self):
        for rec in self:
            if not rec.ref_etd.isdigit():
                raise ValidationError(_(
                    "ETD code must contain numeric characters only."))
