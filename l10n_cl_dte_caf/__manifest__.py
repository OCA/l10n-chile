# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Chile - DTE CAF",
    "summary": "Register Chilean CAF authorizations and protect their evidence",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["l10n_cl_dte_base"],
    "data": [
        "security/caf_security.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "maintainers": ["fsmw"],
}
