from odoo import fields, models


class PartnerActivities(models.Model):
    _description = 'SII Economical Activities Description'
    _name = 'sii.activity.description'
    _order = 'name asc'

    name = fields.Char('Name', required=True, translate=True)
