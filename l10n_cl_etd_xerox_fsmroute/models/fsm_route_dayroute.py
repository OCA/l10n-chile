# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class FSMDayRoute(models.Model):
    _name = 'fsm.route.dayroute'
    _inherit = ['fsm.route.dayroute', 'etd.mixin']

    date_close = fields.Datetime()
    # TODO: move this this fieldservice_route
    company_id = fields.Many2one(
        'res.company',
        default=lambda s: s.env.user.company_id)

    def write(self, values):
        if values.get('stage_id', False) and not \
                self.env.context.get('is_writing_flag', False):
            new_stage = self.stage_id.browse(values.get('stage_id'))
            if new_stage.is_closed:
                values.update({'date_close': fields.Datetime.now()})
        return super().write(values)
