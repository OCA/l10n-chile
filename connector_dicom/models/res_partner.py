# Copyright (C) 2020 Konos
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import requests
import xml.etree.ElementTree as ET
from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    dicom_score = fields.Char(compute="_compute_dicom",
                              inverse="_inverse_dicom", string="Dicom Score")
    dicom_date = fields.Date(compute="_compute_dicom",
                             inverse="_inverse_dicom", string="Dicom Date")
    dicom_count = fields.Integer(
        compute="_compute_dicom_count", string="Dicom Count")
    dicom_ids = fields.Many2many(
        "res.partner.dicom", string='Dicoms', compute="_compute_dicom_count",
        readonly=True, copy=False)

    def _compute_dicom(self):
        dicom = self.env['res.partner.dicom']
        for rec in self:
            partner_dicom = dicom.search([
                ('partner_id', '=', rec.id)], limit=1, order='date desc')
            rec.dicom_date = partner_dicom.date
            rec.dicom_score = partner_dicom.dicom_score

    def _inverse_dicom(self):
        for rec in self:
            if rec.dicom_score and rec.dicom_date:
                if not self._dicom_exist():
                    data = {
                        'dicom_score': rec.dicom_score,
                        'date': self.dicom_date,
                        'partner_id': rec.id}
                    self.env['res.partner.dicom'].create(data)

    def _dicom_exist(self):
        dicom_model = self.env['res.partner.dicom']
        for rec in self:
            return dicom_model.search([
                ('partner_id', '=', rec.id),
                ('date', '=', rec.dicom_date)])

    def _compute_dicom_count(self):
        dicom = self.env['res.partner.dicom']
        for rec in self:
            partner_dicom = dicom.search([('partner_id', '=', rec.id)])
            if partner_dicom:
                rec.dicom_count = dicom.search_count([
                    ('partner_id', '=', rec.id)])
                rec.dicom_ids = partner_dicom.ids
            else:
                rec.dicom_count = 0

    @api.multi
    def res_partner_dicom_action(self):
        dicom_ids = self.mapped('dicom_ids')
        action = \
            self.env.ref(
                'connector_dicom.res_partner_dicom_action').read()[0]
        if len(dicom_ids) > 0:
            action['domain'] = [('id', 'in', dicom_ids.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def onchange_documents(self):
        conf = self.env["ir.config_parameter"].sudo()
        username = conf.get_param("dicom.user")
        password = conf.get_param("dicom.password")
        url = conf.get_param("dicom.url")
        headers = {'content-type': 'text/xml'}
        vat = self.vat.replace('-', '').replace('CL', '')
        form = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:get="http://cl.equifax.com/schema/Platinum360/GetInformePlatinum360BReq">
    <soapenv:Header/>
    <soapenv:Body>
        <get:getInformePlatinum360Request>
        <get:Username>%s</get:Username>
        <get:Password>%s</get:Password>
        <get:RUT>%s</get:RUT>
        <get:SerialNumber></get:SerialNumber>
        <get:IdTransaction></get:IdTransaction>
        <get:Platform>6</get:Platform>
        <get:Channel>6</get:Channel>
        <get:AditionalInformation></get:AditionalInformation>
        <get:BoletinConcursal></get:BoletinConcursal>
        <get:EspecialInformation>
            <!--Zero or more repetitions:--> <get:EspecialInformationType>
            <get:Section></get:Section>
            </get:EspecialInformationType>
            </get:EspecialInformation>
        </get:getInformePlatinum360Request>
    </soapenv:Body>
</soapenv:Envelope>
""" % (username, password, vat)
        encoded_request = form.encode('utf-8')
        response = requests.post(url, headers=headers, data=encoded_request)
        if not response:
            raise UserError(_('Connection Error'))
        Count = 0
        tree = ET.fromstring(response.text)
        for item in tree.getiterator():
            if Count == 7:
                self.dicom_score = item.text
                self.dicom_date = fields.Date.context_today(self)
            Count += 1

    @api.one
    def update_dicom(self):
        self.onchange_documents()
