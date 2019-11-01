# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "References from SII",
    "summary": "Store document references using SII nomenclature",
    "version": "12.0.1.0.0",
    "category": "Localization/Chile",
    "author": "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "l10n_cl_sii",
    ],
    "data": [
        "data/sii.responsibility.csv",
        "data/sii.document.type.csv",
        "data/sii.document.letter.csv",
        "data/sii.document.class.csv",
        "data/sii.concept.type.csv",
        "security/ir.model.access.csv",
        "views/sii_document_class.xml",
        "views/sii_document_letter.xml",
        "views/sii_document_type.xml",
        "views/sii_concept_type.xml",
        "views/sii_responsibility.xml",
        "views/sii_optional_type.xml",
        "views/sii_reference.xml",
        "views/menuitem.xml",
    ],
    "application": False,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
