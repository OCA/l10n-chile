# -*- encoding: utf-8 -*-
from odoo import models, fields

class ResStateRegion(models.Model):
    _name = 'res.country.state.region'

    name = fields.Char(
            string='Region Name',
            help='The state code.\n',
            required=True,
        )
    code = fields.Char(
            string='Region Code',
            help='The region code.\n',
            required=True,
        )
    child_ids = fields.One2many(
            'res.country.state',
            'region_id',
            string='Child Regions',
    )
