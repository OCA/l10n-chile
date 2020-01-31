# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Partner Activity from SII",
    "summary": "Set the SII Activity on Partners",
    "version": "12.0.1.2.0",
    "category": "Localization/Chile",
    "author": "Daniel Blanco, "
              "Blanco Martín & Asociados, "
              "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sii.activity.csv",
        "views/sii_activity.xml",
        "views/res_partner.xml",
    ],
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
