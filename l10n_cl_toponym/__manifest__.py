# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Toponyms from Chile",
    "summary": "Cities, States and Regions from Chile",
    "version": "12.0.1.0.0",
    "category": "Localization/Toponyms",
    "author": "Konos, "
              "Blanco Martín & Asociados, "
              "CubicERP, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "base_address_city",
    ],
    "data": [
        "data/res.country.state.region.xml",
        "data/res.country.state.xml",
        "data/res.city.xml",
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "views/res_company.xml",
        "views/res_partner.xml",
        "views/res_state_view.xml",
        "views/res_city.xml",
    ],
    "installable": True,
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
