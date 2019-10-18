# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class PartnerActivities(models.Model):
    _name = "partner.activities"
    _description = "SII Economical Activities"

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
                limit=limit
            )
        if not recs:
            recs = self.search(
                ["|", ("name", operator, name),
                 ("code", operator, name)] + args,
                limit=limit,
            )
        return recs.name_get()

    code = fields.Char(string="Activity Code", required=True, translate=True)
    parent_id = fields.Many2one(
        "partner.activities", string="Parent Activity", ondelete="cascade")
    name = fields.Char(string="Nombre Completo", required=True, translate=True)
    vat_affected = fields.Selection(
        (("SI", "Si"), ("NO", "No"), ("ND", "ND")),
        string="VAT Affected",
        required=True,
        translate=True,
        default="SI")
    tax_category = fields.Selection(
        (("1", "1"), ("2", "2"), ("ND", "ND")),
        string="TAX Category",
        required=True,
        translate=True,
        default="1")
    internet_available = fields.Boolean(string="Available at Internet",
                                        default=True)
    active = fields.Boolean(
        string="Active",
        help="Allows you to hide the activity without removing it.",
        default=True)
    company_ids = fields.Many2many(
        "res.company", id1="activities_id", id2="company_id", string="Company")
    journal_ids = fields.Many2many(
        "account.journal", id1="activities_id", id2="journal_id",
        string="Journals")
