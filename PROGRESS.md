# Progress Checklist

Tick these off as you go. Each module is "done" when `make test-0N` passes
and you can explain the 3 interview talking points in that module's README
without looking at them.

## Module 1 — Setup
- [ ] `make up` runs HAPI FHIR locally
- [ ] `make load-data` loads the Synthea sample patients
- [ ] `exercises/fhir_client.py` TODOs filled in
- [ ] `make test-01` passes
- [ ] Can explain: why FHIR servers exist (ONC Cures Act / API mandate), what Synthea is for

## Module 2 — FHIR Resources
- [x] `exercises/` TODOs filled in (Patient, Observation, Condition, DiagnosticReport, FamilyMemberHistory, MedicationRequest)
- [x] `make test-02` passes
- [ ] Can explain: resources, references, search parameters, bundles

## Module 3 — Code Systems & Data Quality
- [x] `exercises/` TODOs filled in (LOINC normalization, missing units, duplicates)
- [x] `make test-03` passes
- [ ] Can explain: LOINC vs SNOMED CT vs ICD-10 vs RxNorm, why normalization matters for a risk model

## Module 4 — HL7 v2
- [x] `exercises/` TODOs filled in (ADT/ORU parsing, idempotent mapping to FHIR Observations)
- [x] `make test-04` passes
- [ ] Can explain: why HL7 v2 still exists, ADT vs ORU, idempotency with out-of-order messages

## Module 5 — Bulk FHIR
- [x] `exercises/` TODOs filled in ($export flow, NDJSON ingest into SQLite/DuckDB)
- [x] `make test-05` passes
- [ ] Can explain: Bulk Data IG, async export + polling, NDJSON vs per-resource REST

## Module 6 — SMART on FHIR
- [ ] Walked through standalone patient launch against the public SMART Health IT sandbox
- [ ] `exercises/` TODOs filled in (backend-services JWT auth)
- [ ] `make test-06` passes
- [ ] Can explain: standalone launch vs EHR launch vs backend services, scopes, signed JWT client auth

## Module 7 — Capstone
- [ ] FastAPI service ingests lab results (FHIR or HL7), validates, normalizes
- [ ] Versioned, auditable per-patient risk-signal timeline implemented
- [ ] Tests passing, structured logging in place
- [ ] `ARCHITECTURE.md` written (idempotency, audit trail, PHI access controls, model versioning)
- [ ] `make test-07` passes
- [ ] Can demo the capstone end-to-end and talk through trade-offs

## Wrap-up
- [ ] `INTERVIEW_NOTES.md` filled in
