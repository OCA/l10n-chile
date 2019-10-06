# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": """Chile Localization Regions, Cities and Comunas\
    """,
    'version': '12.0.0.1',
    'category': 'Localization/Toponyms',
    'sequence': 12,
    'author': 'Konos, '
              'Blanco Martín & Asociados, '
              'CubicERP, '
              'Odoo Community Association (OCA)',
    'website': 'https://konos.cl',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Chile Localization Regions, Cities and Comunas.
""",
    'depends': [
            'base',
            'base_address_city',
        ],

    'data': [
            'views/res_company.xml',
            'views/res_partner.xml',
            'views/res_state_view.xml',
            'views/res_city.xml',
            'data/counties_data.xml',
            'security/state_manager.xml',
            'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
