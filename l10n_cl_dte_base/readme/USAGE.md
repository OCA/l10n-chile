Assign **DTE User** to users who need to read documents and evidence metadata
for their allowed companies. Assign **DTE Manager** to users who need to create
documents, read evidence content, or check its integrity. Choose the DTE role
separately from the Accounting role in the user access settings.

This technical addon provides records and permissions for other DTE addons.
A document captures the company's SII environment when it is created.

A DTE manager can use the signing workflow to revise the current signature
before the document is queued. Each revision preserves the previous signature
as immutable evidence. The transport workflow must acquire the same document
lock before selecting the current signature and persisting the request.
