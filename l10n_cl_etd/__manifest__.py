# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Base for Electronic Tax Document for Chile",
    "summary": "Sign and send documents to SII.",
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
        "connector_acp",
        "document",
        "res_partner_email_etd",
        "l10n_cl_toponym",
        "l10n_cl_sii_activity",
        "l10n_cl_sii_folio",
        "l10n_cl_sii_reference",
    ],
    "data": [
        "data/backend.acp.csv",
        "data/res.country.csv",
    ],
    "application": False,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
