# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Electronic Shipping for Chile",
    "summary": "Sign your delivery orders and send them to SII.",
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
        "l10n_cl_etd",
        "delivery",
        "stock",
        "l10n_cl_invoicing_policy",
    ],
    "data": [
        "data/etd_document.xml",
        "data/etd_document_file.xml",
        "views/stock_picking.xml",
        "views/delivery_carrier.xml",
    ],
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
