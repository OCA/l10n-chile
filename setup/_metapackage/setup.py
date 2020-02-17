import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-l10n-chile",
    description="Meta package for oca-l10n-chile Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-connector_acp',
        'odoo12-addon-connector_acp_ftp',
        'odoo12-addon-l10n_cl_chart_of_account',
        'odoo12-addon-l10n_cl_currency_rate_sbif',
        'odoo12-addon-l10n_cl_etd',
        'odoo12-addon-l10n_cl_etd_account',
        'odoo12-addon-l10n_cl_etd_stock',
        'odoo12-addon-l10n_cl_invoicing_policy',
        'odoo12-addon-l10n_cl_sii',
        'odoo12-addon-l10n_cl_sii_activity',
        'odoo12-addon-l10n_cl_sii_folio',
        'odoo12-addon-l10n_cl_sii_reference',
        'odoo12-addon-l10n_cl_sii_reference_account',
        'odoo12-addon-l10n_cl_toponym',
        'odoo12-addon-res_partner_email_etd',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
