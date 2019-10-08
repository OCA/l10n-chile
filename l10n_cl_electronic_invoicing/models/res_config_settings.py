# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_send_dte = fields.Integer(
        string="Tiempo de Espera para Enviar DTE automático al SII (en horas)",
        default=12)
    auto_send_email = fields.Boolean(
        string="Enviar Email automático al Auto Enviar DTE al SII",
        default=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        account_auto_send_dte = int(
            ICPSudo.get_param("account.auto_send_dte", default=12))
        account_auto_send_email = ICPSudo.get_param(
            "account.auto_send_email", default=True)
        res.update(
            auto_send_email=account_auto_send_email,
            auto_send_dte=account_auto_send_dte)
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        ICPSudo.set_param("account.auto_send_dte", self.auto_send_dte)
        ICPSudo.set_param("account.auto_send_email", self.auto_send_email)
