{
    "name": "Chile - DTE Signing",
    "summary": "Signing service contracts for Chilean TED and DTE XML",
    "version": "18.0.1.2.0",
    "category": "Accounting/Localizations",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": ["l10n_cl_dte_core", "l10n_cl_dte_caf", "certificate"],
    "data": [
        "security/ir.model.access.csv",
        "views/signing_profile_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "maintainers": ["fsmw"],
}
