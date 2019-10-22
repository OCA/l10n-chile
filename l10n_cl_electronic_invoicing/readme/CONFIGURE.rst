.. |step1| image:: ./static/images/01-res.company.png
    :alt: Company form view
    :width: 400px

.. |step2| image:: ./static/images/02-res.company.png
    :alt: Company form view
    :width: 400px

.. |step3| image:: ./static/images/03-res.company.png
    :alt: Company form view
    :width: 400px

.. |step4| image:: ./static/images/04-res.company.png
    :alt: Company form view
    :width: 400px

.. |step5| image:: ./static/images/05-account.journal.png
    :alt: Accounting Journal
    :width: 400px

.. |step6| image:: ./static/images/06-account.journal.png
    :alt: Accounting Journal
    :width: 400px

.. |step7| image:: ./static/images/07-account.journal.png
    :alt: Accounting Journal
    :width: 400px

.. |step8| image:: ./static/images/08-ir.sequence.png
    :alt: Sequence form view
    :width: 400px

.. |step9| image:: ./static/images/09-ir.sequence.png
    :alt: Sequence form view
    :width: 400px

.. |step10| image:: ./static/images/10-fetchmail.server.png
    :alt: Fetchmail Server
    :width: 400px

.. |step11| image:: ./static/images/11-res.config.settings.png
    :alt: Accounting Settings
    :width: 400px

.. |step12| image:: ./static/images/12-res.company.png
    :alt: Company form view
    :width: 400px

.. |step13| image:: ./static/images/13-www.sii.cl.png
    :alt: SII form
    :width: 400px

Please note that the configuration for the production environment is different
than for a test one. The difference resides in the following fields:

* Resolution Number
* Resolution Date
* DTE Service Provider
* Folios

Companies
---------

To configure this module, you need to:

* Go to Settings > Users & Companies > Companies
* Select or create a company
* Enter all the information of the company especially:

  * the logo
  * the resolution number
  * the resolution date

|step1|

* Go to the Signature File tab
* Upload your digital certificate

|step2|

* Edit to update the Subject Serial Number with your RUT

|step3|

* Select users allowed to send and receive invoices

|step4|

Journals
--------

* Go to Accounting > Configuration > Journals
* Select the Customer Invoices or Vendor Bills journal
* Enter the documents that can be generated

|step5|

|step6|

* Download the CAF and folios from SII
* Go to the sequence
* Import the CAF and folios in Odoo: https://www.youtube.com/watch?v=OXldIC9lMqU
* Select the folio (XML)

|step7|

* Make sure the sequence is configured without hole

|step8|

* Set the initial folio in the next number

|step9|

To backup and upload the XML history, go to
http://www.sii.cl/destacados/factura_electronica/guias_ayuda/como_generar_archivo_respaldo.pdf

Incoming Mail Servers
---------------------

* Go to Settings
* Activate the developer mode
* Go to Settings > Technical > Emails > Incoming Mail Servers
* Create a new incoming mail server with the mailbox created previsouly to receive vendo bills
* Set the action to create a new record "mail.message.dte"

|step10|

Accounting
----------

* Go to Accounting > Configuration > Settings
* Set the rounding method to "Round globally"

|step11|

Go Live
-------

To go live and use the production environment

* Go to Settings > User & Companies > Companies
* Edit the company
* Set the "DTE Service Provider" to "www.sii.cl"

|step12|

* Go to https://maullin.sii.cl/cvc/dte/pe_condiciones.html
* Update your data to set the email address configured to receive vendor bills

|step13|
