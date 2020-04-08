# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Konos
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "CRM - Dicom",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["connector_dicom", 
                "crm",
     ],
    "summary": "Get and store financial score from Dicom to CRM",
    "author": "Open Source Integrators, "
              "Konos, "
              "Odoo Community Association (OCA)",
    "maintainer": "Open Source Integrators",
    "website": "https://github.com/OCA/l10n-chile",
    "data": [
        "views/crm_lead_views.xml",
    ],
    "application": False,
    "sequence": 0,
}
