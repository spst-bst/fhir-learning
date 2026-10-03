# Architecture: Lab Ingestion and Risk-Signal Timeline

Fill this in yourself once `make test-07` passes — writing it is the
exercise, not reading a filled-in version. Each section below is a
prompt, not a fill-in-the-blank; answer it the way you would in an actual
design review, in your own words, referencing what you actually built.

## 1. Idempotency

What happens if the same `Observation` is ingested twice — a client
retry, a replayed export, a duplicate webhook delivery? Where in this
pipeline is that handled, and what would break if it weren't? How does
this compare to Module 4's HL7 idempotency problem (no natural id, so one
was derived from content) versus Module 5/7's (the id already exists,
upsert on it directly)?

## 2. Audit trail

Why does `risk_signal_history` never get updated or deleted, only
appended to? Walk through a concrete scenario: a patient's A1c is flagged
elevated on day 1, a corrected (still-elevated) value arrives on day 3.
What does the timeline look like after both events, and what question
could someone answer from it six months later that they couldn't if the
row had just been updated in place?

## 3. PHI access controls

This module's `/ingest/fhir` and `/patients/{id}/risk-timeline` endpoints
have no auth at all — deliberately out of scope for the exercise. If this
were going to production tomorrow: who should be allowed to call each
endpoint, what would you use to enforce it (think back to Module 6 —
would this be a user-facing scope or a `system/` one?), and what would
you log about *access* to PHI, not just the ingestion events this module
already logs?

## 4. Model versioning

The risk thresholds in `RISK_THRESHOLDS` are hardcoded. If those
thresholds — or the underlying logic deciding what counts as "elevated"
— change next quarter, what happens to the *existing* rows in
`risk_signal_history` that were computed under the old rule? Should old
and new coexist, and if so, what would you add to the schema to tell them
apart? (This is the same "never silently overwrite history" principle as
section 2, applied one layer up — to the rule itself, not just the data
it produced.)

## 5. What would have to change for real HL7 ingestion

Module 4 built HL7 v2 ORU parsing; this module's ingestion path only
takes FHIR `Observation` JSON. Sketch (a paragraph is enough) what an
`/ingest/hl7` endpoint would need to do differently before it could reuse
`ingest_fhir_observation`'s compare-before-write / risk-scoring /
audit-append logic unchanged.
