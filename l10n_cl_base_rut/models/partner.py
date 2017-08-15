# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import except_orm, UserError
import re


class res_partner(models.Model):
    _inherit = 'res.partner'

    document_number = fields.Char(string='Document Number')
    formated_vat = fields.Char(
        translate=True, string='Printable VAT',
        help='Show formatted vat')
    vat = fields.Char(
        string='VAT',
        compute='_compute_vat', inverse='_inverse_vat',
        store=True, compute_sudo=False)

    def check_vat_cl(self, vat):
        body, vdig = '', ''
        if len(vat) > 9:
            vat = vat.replace('-', '', 1).replace('.', '', 2)
        if len(vat) != 9:
            return False
        else:
            body, vdig = vat[:-1], vat[-1].upper()
        try:
            vali = range(2, 8) + [2, 3]
            operar = '0123456789K0'[11 - (
                sum([int(digit)*factor for digit, factor in zip(
                    body[::-1], vali)]) % 11)]
            if operar == vdig:
                return True
            else:
                return False
        except IndexError:
            return False

    @staticmethod
    def format_document_number(vat):
        clean_vat = (
            re.sub('[^1234567890Kk]', '',
                   str(vat))).zfill(9).upper()
        return '%s.%s.%s-%s' % (
            clean_vat[0:2], clean_vat[2:5], clean_vat[5:8], clean_vat[-1])

    @api.onchange('document_number')
    def onchange_document(self):
        self.document_number = self.format_document_number(self.document_number)

    @api.depends('document_number')
    def _compute_vat(self):
        for x in self:
            clean_vat = (
                re.sub('[^1234567890Kk]', '',
                       str(x.document_number))).zfill(9).upper()
            x.vat = 'CL%s' % clean_vat

    def _inverse_vat(self):
        self.document_number = self.format_document_number(self.vat)
