# Interview Notes — Healthcare Interoperability

One page. What I built, the trade-offs I made, and how it maps to my
pharmacy integration background. Fill in each section as you finish the
corresponding module — don't try to write this in one sitting.

## What I built

A local FHIR/HL7 learning stack: HAPI FHIR (Docker) loaded with synthetic
Synthea patients (US Core profiles), a Python client layer over `httpx` and
`fhir.resources`, an HL7 v2 ADT/ORU parser, a Bulk FHIR `$export` + NDJSON
ingest pipeline, a SMART on FHIR auth walkthrough, and a capstone FastAPI
service that ingests lab results and maintains a versioned, auditable
per-patient risk-signal timeline.

_(Expand this paragraph as you build modules 2–7.)_

## Module 1 — Setup

- Ran a real HAPI FHIR server locally and loaded synthetic patients instead
  of working from static fixtures — closer to what a partner-EHR
  integration actually looks like (discover capabilities, then query).
- Talking point: FHIR's REST + resource model is a contract, structurally
  the same as any internal microservice API I've built on GCP — the hard
  parts (pagination, idempotent retries, versioning) transfer directly.

## Module 2 — FHIR Resources
_(fill in after building this module)_

## Module 3 — Code Systems & Data Quality
_(fill in after building this module)_

## Module 4 — HL7 v2
_(fill in after building this module)_

## Module 5 — Bulk FHIR
_(fill in after building this module)_

## Module 6 — SMART on FHIR
_(fill in after building this module)_

## Module 7 — Capstone
_(fill in after building this module — this is the centerpiece of the demo)_

## Trade-offs I'd call out unprompted

- _(e.g., rule-based risk score vs. ML model — the point of the capstone is
  the data pipeline, not model sophistication)_
- _(e.g., SQLite/DuckDB for local dev vs. a real OLTP/warehouse split in
  production)_

## How this maps to my pharmacy integration experience

- **Data contracts**: FHIR resources + US Core profiles are a more formal
  version of the data contracts I negotiated with pharmacy partners —
  schema, required fields, code systems, all spelled out instead of
  implied by a shared CSV format.
- **PHI handling**: the HIPAA discipline (access controls, audit trails,
  minimum necessary) carries over directly; FHIR just gives you
  `Provenance`/`AuditEvent` resources and SMART scopes as the standard
  vocabulary for it.
- **Partner security reviews**: SMART on FHIR's backend-services auth
  (signed JWT, no shared secrets) is the same shape as the auth reviews I've
  gone through with pharmacy and PBM partners.
- **Reliable ingestion**: idempotent HL7 v2 message handling (duplicates,
  out-of-order ORU results) is the same class of problem as reliable
  pharmacy claims/fill-event ingestion — dedupe keys, replay safety, and
  knowing what "already processed" means.
