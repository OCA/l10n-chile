# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(
        "SELECT to_regclass('l10n_cl_dte_signing_profile'), to_regclass('res_company')"
    )
    profile_table, company_table = cr.fetchone()
    if not profile_table or not company_table:
        return
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'res_company' AND column_name = 'dte_certificate_id'"
    )
    if not cr.fetchone():
        return
    cr.execute(
        "INSERT INTO l10n_cl_dte_signing_profile "
        "(name, company_id, sii_environment, certificate_id, active, "
        "create_uid, create_date, write_uid, write_date) "
        "SELECT 'Migrated ' || company.name || ' DTE certificate', company.id, "
        "COALESCE(company.dte_sii_environment, 'certification'), "
        "company.dte_certificate_id, true, 1, NOW(), 1, NOW() "
        "FROM res_company AS company "
        "WHERE company.dte_certificate_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM l10n_cl_dte_signing_profile AS profile "
        "WHERE profile.company_id = company.id "
        "AND profile.sii_environment = COALESCE("
        "company.dte_sii_environment, 'certification'))"
    )
