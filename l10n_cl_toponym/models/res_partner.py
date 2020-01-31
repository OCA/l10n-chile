# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_default_country(self):
        return self.env.user.company_id.country_id.id or \
            self.env.user.partner_id.country_id.id

    state_id = fields.Many2one("res.country.state", 'State')

    @api.onchange('city_id')
    def _onchange_city(self):
        if self.city_id:
            self.country_id = self.city_id.state_id.country_id.id
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name

    @api.constrains("vat", "commercial_partner_id")
    def _vat_unique(self):
        for r in self:
            if not r.vat or r.parent_id:
                continue
            partner = self.env["res.partner"].search([
                ("vat", "=", r.vat),
                ("id", "!=", r.id),
                ("commercial_partner_id", "!=", r.commercial_partner_id.id)])
            if r.vat != "CL555555555" and partner:
                raise UserError(_("The VAT %s already exists."
                                  " VAT must be unique") % r.vat)
            return False

    @api.onchange('vat')
    def onchange_vat(self):
        vat = self.vat
        if vat:
            if len(vat) == 9:
                # Format: XX.XXX.XXX-X
                formatted_vat = \
                    vat[0:2] + "." + vat[2:5] + "." + vat[5:8] + "-" + vat[8]
                self.vat = formatted_vat
            elif len(vat) != 12:
                raise UserError(_("The VAT is not valid."))

    @api.multi
    @api.constrains('vat')
    def check_vat(self):
        for rec in self:
            if rec.vat:
                if len(rec.vat) != 12:
                    raise UserError(_("The VAT must contain 12 characters."))
                vat_raw = rec.vat.replace('.', '').replace('-', '')
                body, vdig = vat_raw[:-1], vat_raw[-1].upper()
                try:
                    vali = list(range(2, 8)) + [2, 3]
                    operar = "0123456789K0"[
                        11 - (sum([int(digit) * factor
                                   for digit, factor in
                                   zip(body[::-1], vali)]) % 11)]
                    if operar != vdig:
                        raise UserError(_("The VAT is not valid."))
                except IndexError:
                    raise UserError(_("The VAT is not valid."))
