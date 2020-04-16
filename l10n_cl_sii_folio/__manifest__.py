# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Electronic Invoicing for Chile",
    "summary": "Sign your documents and send them to SII.",
    "version": "12.0.1.1.2",
    "category": "Localization/Chile",
    "author": "Daniel Blanco, "
              "Blanco Martín & Asociados, "
              "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    'external_dependencies': {
        'python': [
            'xmltodict',
        ],
    },
    "depends": [
        "l10n_cl_sii_reference_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_sequence.xml",
        "views/ir_sequence_folio.xml",
    ],
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
