[![Runbot Status](https://runbot.odoo-community.org/runbot/badge/flat/236/12.0.svg)](https://runbot.odoo-community.org/runbot/repo/github-com-oca-l10n-chile-236)
[![Build Status](https://travis-ci.org/OCA/l10n-chile.svg?branch=12.0)](https://travis-ci.org/OCA/l10n-chile)
[![Coverage Status](https://coveralls.io/repos/OCA/l10n-chile/badge.png?branch=12.0)](https://coveralls.io/r/OCA/l10n-chile?branch=12.0)
[![codecov](https://codecov.io/gh/OCA/l10n-chile/branch/12.0/graph/badge.svg)](https://codecov.io/gh/OCA/l10n-chile)

# Localization for Chile

* Factura Electrónica (FAC 33, FNA 34): Ok envío, Ok muestra impresa, Ok Certificación
* Nota de Crédito Electrónica: Ok envío, Ok muestra impresa, Ok Certificación
* Nota de Débito Electrónica: Ok envío, Ok muestra impresa, Ok Certificación
* Recepción XML Intercambio: Ok recepción, Ok respuesta mercaderías, Ok respuesta Validación Comercial, Ok Envío Recepción al SII, Ok Certificación
* Libro de Compra Venta: Ok envío al SII, Ok Certificación (Básico y Exentos)
* Consumo de Folios: Validación OK, Envío OK, Certificación OK
* Boleta Electrónica por BO (39, 41): Validación Ok, Muestra impresa No probado aún, Información Pública no adaptada aún
* Libro Boletas Electrónica: Validación Ok, Creación XML OK
* Boleta Electrónica por POS (39, 41): Validación Ok, Muestras Impresas Ticket OK, Generación XML Ok, Visaulización Pública Ok, Certificación OK vía https://gitlab.com/dansanti/l10n_cl_dte_point_of_sale
* Nota de Crédito Electrónica para Boletas (Solo por BO POS): Validación Ok, Generación XML Ok, Muestras Impresas Ticket OK, Certificación OK vía https://gitlab.com/dansanti/l10n_cl_dte_point_of_sale
* Guía de Despacho Electrónica: Ok envío, Ok muestra impresa, Ok Certificación, vía https://gitlab.com/dansanti/l10n_cl_stock_picking
* Libro Guía Despacho: Ok envío, Ok Muestras impresas, Ok Certificación, vía https://gitlab.com/dansanti/l10n_cl_stock_picking
* Factoring (Cesión de Créditos): Ok Envío, Ok Certificación, vía https://gitlab.com/dansanti/l10n_cl_dte_factoring
* Factura de Exportación Electrónica (110 con sus NC 111 y ND 112): No Portado, No Probado vía https://gitlab.com/dansanti/l10n_cl_dte_exportacion
* Liquidación de Facturas: No desarrollada
* Factura de Compra Electrónica (46): No desarrollada


[//]: # (addons)

Available addons
----------------
addon | version | summary
--- | --- | ---
[connector_acp](connector_acp/) | 12.0.1.0.0 | Get your documents signed by an Authorized Certification Provider
[connector_acp_xerox](connector_acp_xerox/) | 12.0.1.0.0 | Get Xerox to sign your documents and send them to SII
[l10n_cl_chart_of_account](l10n_cl_chart_of_account/) | 12.0.1.0.0 | Chile Localization Chart Account SII
[l10n_cl_currency_rate_sbif](l10n_cl_currency_rate_sbif/) | 12.0.2.0.0 | Update UF, UTM and US Dollar exchange rates using SBIF
[l10n_cl_etd](l10n_cl_etd/) | 12.0.1.0.0 | Sign and send documents to SII.
[l10n_cl_etd_account](l10n_cl_etd_account/) | 12.0.1.0.0 | Sign your invoices and send them to SII.
[l10n_cl_etd_stock](l10n_cl_etd_stock/) | 12.0.1.0.0 | Sign your delivery orders and send them to SII.
[l10n_cl_invoicing_policy](l10n_cl_invoicing_policy/) | 12.0.1.0.0 | Ticket, Invoice or Electronic Guide
[l10n_cl_sii](l10n_cl_sii/) | 12.0.1.0.0 | Provides the Settings > SII menuitem
[l10n_cl_sii_activity](l10n_cl_sii_activity/) | 12.0.1.0.0 | Set the SII Activity on Partners
[l10n_cl_sii_folio](l10n_cl_sii_folio/) | 12.0.1.0.0 | Sign your documents and send them to SII.
[l10n_cl_sii_reference](l10n_cl_sii_reference/) | 12.0.1.0.0 | Store document references using SII nomenclature
[l10n_cl_sii_reference_account](l10n_cl_sii_reference_account/) | 12.0.1.0.0 | Store document references using SII nomenclature
[l10n_cl_toponym](l10n_cl_toponym/) | 12.0.1.1.0 | Cities, States and Regions of Chile
[res_partner_email_etd](res_partner_email_etd/) | 12.0.1.0.0 | To receive Electronic Tax Documents

[//]: # (end addons)

## Translation Status

[![Translation status](https://translation.odoo-community.org/widgets/l10n-chile-12-0/-/multi-auto.svg)](https://translation.odoo-community.org/engage/l10n-chile-12-0/?utm_source=widget)

----

OCA, or the Odoo Community Association, is a nonprofit organization whose 
mission is to support the collaborative development of Odoo features and 
promote its widespread use.

http://odoo-community.org/

