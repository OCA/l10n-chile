# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.constrains('backend_acp_id')
    def _check_backend_acp_id(self):
        """
        Check the company backend to make sure it is not set to SII
        """
        sii = self.env.ref('l10n_cl_etd.backend_acp_sii')
        for record in self:
            if record.backend_acp_id.id == sii.id:
                raise ValidationError(_(
                    "%s does not sign documents. Please select another "
                    "provider." % sii.name))
