# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "Xerox Electronic Document",
    "version": "12.0.1.0.2",
    "license": "AGPL-3",
    "category": "Localization",
    "summary": "Use Xerox electronic document communication.",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "development_status": "Beta",
    "maintainers": ["max3903"],
    "depends": [
        "connector_acp_ftp",
        "l10n_cl_etd_account",
        "l10n_cl_sii_activity",
        "l10n_cl_sii_folio",
        "l10n_cl_etd_stock",
    ],
    "data": [
        "data/backend.acp.csv",
        "data/etd_document_invoice.xml",
        "data/etd_document_stock.xml",
        "data/etd_xerox_cron.xml",
        "views/backend_acp.xml",
    ],
}
