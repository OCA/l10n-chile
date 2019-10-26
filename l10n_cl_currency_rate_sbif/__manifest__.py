# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 Konos
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Update Exchange Rates from SBIF",
    "summary": "Update UF, UTM and US Dollar exchange rates using SBIF",
    "version": "12.0.2.0.0",
    "category": "Tools",
    "license": "AGPL-3",
    "author": "Blanco Martin & Asociados, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "depends": [
        "decimal_precision",
    ],
    "data": [
        "data/decimal_precision.xml",
        "data/ir_config_parameter.xml",
        "data/ir_cron.xml",
        "views/update_button.xml",
        "data/res.currency.csv",
    ],
    "application": True,
    "development_status": "Beta",
    "maintainers": ["danisan"],
}
