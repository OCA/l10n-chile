# Copyright (c) 2018 Konos
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    sii_code = fields.Integer(string='SII Code')
    sii_type = fields.Selection([
        ('A', 'Anticipated'),
        ('R', 'Retention')],
        string="Tax Type for SII")
    retention = fields.Float(string="Retention Value", default=0.00)
    no_rec = fields.Boolean(string="Can be Retrieved", default=False)
    fixed_asset = fields.Boolean(string="Fixed Asset", default=False)
    sii_detailed = fields.Boolean(string='Details of VAT', default=False)

    def _get_tax_vals(self, company, tax_template_to_tax):
        """
         This method generates a dictionnary of all the values for the tax
         that will be created.
        """
        self.ensure_one()
        val = super(AccountTaxTemplate, self)._get_tax_vals(
            company, tax_template_to_tax)
        val.update({
            'sii_code': self.sii_code,
            'sii_type': self.sii_type,
            'retention': self.retention,
            'no_rec': self.no_rec,
            'fixed_asset': self.fixed_asset,
            'sii_detailed': self.sii_detailed,
        })
        return val


class AccountTax(models.Model):
    _inherit = 'account.tax'

    sii_code = fields.Integer(string='SII Code')
    sii_type = fields.Selection([
        ('A', 'Anticipated'),
        ('R', 'Retention')],
        string="Tax Type for SII")
    retention = fields.Float(string="Retention Value", default=0.00)
    no_rec = fields.Boolean(string="Can be Retrieved", default=False)
    fixed_asset = fields.Boolean(string="Fixed Asset", default=False)
    sii_detailed = fields.Boolean(string='Details of VAT', default=False)
