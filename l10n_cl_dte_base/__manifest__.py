# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Chile - DTE Base",
    "summary": "Company-scoped records and immutable evidence for Chilean DTEs",
    "version": "18.0.1.1.0",
    "category": "Accounting/Localizations",
    "author": "FSMW, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": ["l10n_cl"],
    "data": [
        "security/dte_security.xml",
        "security/ir.model.access.csv",
    ],
    "maintainers": ["fsmw"],
}
