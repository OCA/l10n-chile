# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _


class SiiConceptType(models.Model):
    _name = "sii.concept.type"
    _description = "SII concept types"

    name = fields.Char("Name", size=120, required=True)
    sii_code = fields.Integer("SII Code", required=True)
    active = fields.Boolean("Active", default=True)
    product_types = fields.Char(
        "Product Types",
        help="Translate the product type to this SII concept. Types must be "
             "a subset of adjust, consu and service separated by commas.",
        required=True)

    @api.constrains("product_types")
    def _check_product_types(self):
        for record in self:
            if record.product_types:
                types = set(record.product_types.split(","))
                if not types.issubset(["adjust", "consu", "service"]):
                    return {'warning': {
                        'title': _("Warning!"),
                        'message': _("You provided an invalid list of product "
                                     "types. Must be separated by commas.")}}
