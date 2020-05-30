# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Konos
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Connector - Dicom",
    "version": "12.0.1.0.1",
    "license": "AGPL-3",
    "depends": ["contacts"],
    "summary": "Get and store financial score from Dicom",
    "author": "Open Source Integrators, "
              "Konos, "
              "Odoo Community Association (OCA)",
    "maintainer": "Open Source Integrators",
    "website": "https://github.com/OCA/l10n-chile",
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner.xml",
        "views/res_partner_dicom.xml",
        "data/ir_config_parameter.xml",
    ],
    "application": False,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"]
}
