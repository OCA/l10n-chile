{
    'name': 'Chilean Financial Indicators',
    'version': '12.0.1.0.0',
    'category': 'Tools',
    'license': 'LGPL-3',
    'author': u'Blanco Martin & Asociados',
    'website': 'http://blancomartin.cl',
    'depends': [
        'base'
    ],
    'data': [
        'data/decimal.precision.xml',
        'data/ir_cron.xml',
        'data/ir.config_parameter.xml',
        'views/update_button.xml',
        'data/res.currency.csv',
    ],
    'init_xml': [
        'query0.sql',
        'query1.sql',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
