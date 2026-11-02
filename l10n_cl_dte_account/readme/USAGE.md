Set the company SII mode to Demo from Settings > Companies, then select
**Prepare Demo Configuration** beside the mode selector. The confirmation wizard
creates a synthetic Demo trust key, a signed type-33 CAF, and a disposable
company signing certificate/profile. The company must have a valid Chilean RUT.
The wizard never changes an existing CAF or signing profile, and all generated
records are marked synthetic and scoped to Demo.

After setup, post a customer invoice with document type 33 and choose **Issue
DTE 33**. The asynchronous Demo gateway simulates submission and status polling;
its TrackID and evidence are clearly marked `DEMO / SIMULADO`. They are not an
SII receipt. The queue-job runner must be active to process the submission.

The generated trust key, CAF private key, and signing certificate are synthetic
local test material. Never use them in Certification or Production. Those modes
remain unavailable until their real SII transport adapters are installed.
