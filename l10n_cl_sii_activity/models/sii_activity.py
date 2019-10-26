# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class SiiActivity(models.Model):
    _name = "sii.activity"
    _description = "SII Economic Activity"

    @api.multi
    def name_get(self):
        res = []
        for r in self:
            res.append((r.id, (r.code and "[" + r.code + "] " + r.name or "")))
        return res

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(
                ["|", ("name", "=", name), ("code", "=", name)] + args,
                limit=limit)
        if not recs:
            recs = self.search(["|", ("name", operator, name),
                                ("code", operator, name)] + args, limit=limit)
        return recs.name_get()

    code = fields.Char(string="Activity Code", required=True, translate=True)
    parent_id = fields.Many2one("sii.activity", string="Parent Activity",
                                ondelete="cascade", index=True)
    name = fields.Char(string="Complete Name", required=True, translate=True)
    vat_affected = fields.Selection((
        ("SI", "Yes"),
        ("NO", "No"),
        ("ND", "Not Available")),
        string="VAT Affected", required=True, translate=True, default="yes")
    tax_category = fields.Selection((
        ("1", "1"),
        ("2", "2"),
        ("ND", "Not Available")),
        string="Tax Category", required=True, translate=True, default="1")
    internet_available = fields.Boolean(string="Available on the Internet",
                                        default=True)
    active = fields.Boolean(string="Active", default=True,
                            help="Allow you to hide the activity without "
                                 "removing it.")
    company_ids = fields.Many2many("res.company", id1="sii_activity_id",
                                   id2="company_id", string="Companies")
