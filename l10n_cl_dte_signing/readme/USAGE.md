Create one signing profile for each company and SII environment. Select a
company-owned certificate with a private key; a certificate may belong to only
one profile. DTE signing resolves the profile from the DTE's immutable mode and
fails closed when no matching profile is active. A DTE manager may create a
synthetic Demo profile and disposable certificate from the company's Demo
configuration; the generated record is visibly marked synthetic and cannot be
used by Certification or Production.
