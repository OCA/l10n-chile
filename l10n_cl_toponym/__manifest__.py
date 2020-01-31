# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Toponyms of Chile",
    "summary": "Cities, States and Regions of Chile",
    "version": "12.0.1.3.0",
    "category": "Localization/Toponyms",
    "author": "Konos, "
              "Blanco Martín & Asociados, "
              "CubicERP, "
              "Open source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "base_address_city",
    ],
    "data": [
        "data/res_country_state_region.xml",
        "data/res_country_state.xml",
        "data/res_country.xml",
        "data/res_city.xml",
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "views/res_company.xml",
        "views/res_partner.xml",
        "views/res_country.xml",
        "views/res_country_state.xml",
        "views/res_country_state_region.xml",
        "views/res_city.xml",
    ],
    "installable": True,
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
