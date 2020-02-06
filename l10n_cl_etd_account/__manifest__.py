# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Electronic Invoicing for Chile",
    "summary": "Sign your invoices and send them to SII.",
    "version": "12.0.2.0.0",
    "category": "Localization/Chile",
    "author": "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "l10n_cl_etd",
        "l10n_cl_chart_of_account",
        "l10n_cl_invoicing_policy",
        "l10n_cl_sii_reference_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/etd_document.xml",
        "data/etd_document_file.xml",
        "views/account_invoice.xml",
    ],
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
