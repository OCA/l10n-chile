# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "References from SII",
    "summary": "Store document references using SII nomenclature",
    "version": "12.0.1.1.0",
    "category": "Localization/Chile",
    "author": "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "account",
        "l10n_cl_sii_reference",
    ],
    "data": [
        "views/account_invoice.xml",
        "views/sii_reference.xml",
    ],
    "application": False,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
