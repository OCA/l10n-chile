# Copyright (c) 2018 Konos
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Chile Localization Chart Account SII",
    "version": "12.0.1.0.0",
    "author": "Konos, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "category": "Localization/Chile",
    "license": "AGPL-3",
    "depends": ["account"],
    "data": [
        "data/l10n_cl_chart_of_account_data.xml",
        "data/account_tax_data.xml",
        "data/account_chart_template_data.xml",
        "data/account_journal.xml",
        "views/account_tax.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
