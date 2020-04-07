# Copyright (C) 2020 Konos
# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import fields, models


_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    dicom_score = fields.Char(compute="_compute_dicom",
                              inverse="_inverse_dicom", string="Dicom Score")
    dicom_date = fields.Date(compute="_compute_dicom",
                             inverse="_inverse_dicom", string="Dicom Date")

    def _compute_dicom(self):
        dicom = self.env['res.partner.dicom']
        for rec in self:
            partner_dicom = dicom.search([
                ('partner_id', '=', rec.partner_id.id)],
                limit=1, order='date desc')
            rec.dicom_date = partner_dicom.date
            rec.dicom_score = partner_dicom.dicom_score

    def _inverse_dicom(self):
        for rec in self:
            if rec.dicom_score and rec.dicom_date:
                if not self._dicom_exist():
                    data = {
                        'dicom_score': rec.dicom_score,
                        'date': rec.dicom_date,
                        'partner_id': rec.partner_id.id}
                    self.env['res.partner.dicom'].create(data)

    def _dicom_exist(self):
        dicom_model = self.env['res.partner.dicom']
        for rec in self:
            return dicom_model.search([
                ('partner_id', '=', rec.partner_id.id),
                ('date', '=', rec.dicom_date)])

    def update_dicom(self):
        self.partner_id.onchange_documents()
