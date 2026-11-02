Only a DTE manager may load CAF files and configure the scoped CAF trust keys.
Validation checks the CAF structure, issuer and folio metadata, the SII signature
over DA, and the embedded RSA key pair. It refuses CAF files whose saved bytes
no longer match their registered SHA-256 digest.

Validated CAF ranges may overlap. The folio ledger enforces uniqueness by
company, DTE type, and folio number, records the source CAF as DTE evidence, and
never recycles a reserved or voided folio. Reservation accepts an idempotency
key so a repeated request returns the same ledger entry.

Every CAF is assigned to Demo, Certification, or Production. Signature
verification selects trust keys from the `demo` scope only for Demo CAFs and
from the `official` scope for both SII environments. Folio reservation refuses
to proceed unless the CAF mode matches the immutable DTE mode.

Populate `official` keys from the SII trust material before validating
Certification or Production CAFs. No synthetic trust key is shipped in the OCA
source; a DTE manager may request runtime generation from the company's Demo
configuration. Local verification proves cryptographic separation; it does not
certify SII acceptance.
