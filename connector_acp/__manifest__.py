# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "ACP Connector",
    "summary": "Get your documents signed by an Authorized Certification "
               "Provider",
    "version": "12.0.1.0.0",
    "category": "Localization",
    "author": "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "connector",
    ],
    "external_dependencies": {
        "python": [
        ]
    },
    "data": [
        "security/ir.model.access.csv",
        "views/backend_acp.xml",
        "views/ssl_certificate.xml",
        "views/res_company.xml",
    ],
    "application": False,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
