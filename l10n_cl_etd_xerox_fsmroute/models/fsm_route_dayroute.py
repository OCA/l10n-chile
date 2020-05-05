# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models, _


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

    def get_xerox_data(self):
        """
        Returns a list of lines for Xerox reports
        """
        lines = {}
        sections = {}
        pickings = self.mapped(
            'order_ids.picking_ids.move_ids_without_package')
        for line in pickings:
            section_key = line.product_id.categ_id
            section_name = section_key.complete_name
            sections.setdefault(section_key, section_name or '')

            key = (line.product_id, line.product_uom)
            lines.setdefault(
                key,
                {'code': line.product_id.default_code,
                 'name': line.product_id.name,
                 'uom': line.product_uom.name,
                 'quantity': 0,
                 'price': 0,
                 'section_key': section_key,
                 })
            lines[key]['quantity'] += (
                line.quantity_done or line.product_uom_qty)
            lines[key]['price'] = max(
                lines[key]['price'],
                line.sale_line_id.price_unit,
                )

        report_lines = []
        index = 1
        for section_key, section_name in sections.items():
            section_lines = [
                x for x in lines.values()
                if x['section_key'] == section_key]
            if section_lines:
                report_lines.append({
                    'index': index,
                    'code': '',
                    'name': _("***** %s *****") % section_name,
                    'uom': '',
                    'quantity': '',
                    'price': '',
                    })
                index = index + 1
                for line in section_lines:
                    line['index'] = index
                    report_lines.append(line)
                    index = index + 1

        tot_qty = sum(x['quantity'] for x in lines.values())
        report_lines.append({
            'index': index,
            'code': '',
            'name': _('***** TOTAL *****'),
            'uom': _('TT'),
            'quantity': tot_qty,
            'price': '',
        })
        return report_lines
