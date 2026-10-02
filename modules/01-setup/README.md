# Module 1 — Setup: Run a FHIR Server and Query It

## Concepts

A FHIR server exposes clinical data as resources (`Patient`, `Condition`,
`Observation`, ...) over a plain REST API: `GET /Patient/123`, `GET
/Observation?patient=123&code=http://loinc.org|4548-4`, `POST /` with a
transaction `Bundle` to create many resources atomically. Every major EHR
(Epic, Cerner/Oracle Health, athenahealth) now exposes this same API shape
because the US ONC Cures Act requires it. That's the whole point of FHIR:
one API shape, instead of N custom integrations per vendor.

**HAPI FHIR** is the reference open-source Java implementation of a FHIR
server — widely used in health-tech for local dev, testing, and even
production. You're running it in Docker so you get a real, spec-compliant
server with zero cloud dependency.

**Synthea** is a synthetic patient generator built by MITRE. It produces
clinically plausible, statistically realistic patient records (conditions,
labs, meds, encounters) with zero real PHI — the standard way health-tech
teams develop and demo against realistic data. The patients loaded in this
course were generated with Synthea and conform to **US Core** profiles (the
"must-support" baseline every US FHIR API has to meet).

In this module you'll start the server, load the synthetic patients, and
write your first FHIR client calls with `httpx` — a capability statement
check, a resource count, a fetch-by-id, and two searches.

## Why it matters for a clinical-data startup

A cancer-risk model is only as good as the data pipeline feeding it. Before
any modeling happens, someone has to reliably pull `Observation`,
`Condition`, `FamilyMemberHistory`, and `DiagnosticReport` resources out of
partner EHRs over exactly this kind of REST API — often across dozens of
source systems with inconsistent data quality. Knowing the base mechanics
(resources, bundles, search parameters, pagination) is the foundation for
every later conversation about ingestion reliability, data contracts, and
scale.

## 3 Interview Talking Points

1. **"FHIR's REST + resource model is a contract, same as an internal
   microservice API."** Your GCP/distributed-systems background maps
   directly: `Patient` and `Observation` are just resources with a schema
   and a stable id, same as any service's domain entities. The hard parts
   (pagination, idempotent retries, versioning) are the same hard parts you
   already know from pharmacy data integrations.
2. **"Synthetic data generation (Synthea) is how HIPAA-constrained teams
   move fast."** You can't develop against real PHI casually. Talk about
   how your pharmacy integration work handled this tension, and that
   Synthea is the health-tech-standard answer to "how do we get realistic
   test data without touching real patient records."
3. **"A local HAPI server mirrors what you'll debug against a partner's
   sandbox."** Every EHR integration starts with pointing your client at
   someone else's FHIR server and working out capability statements,
   supported search parameters, and rate limits — exactly what this module
   does, just against a server you control first.

## What to do

```bash
make up          # start HAPI FHIR in Docker
make load-data   # load the Synthea sample patients
```

Then open `exercises/fhir_client.py`, fill in the `TODO`s, and run:

```bash
make test-01
```

Hints before answers — ask if you get stuck for more than ~10 minutes on any
one function. Don't open `solutions/` until you've got a passing (or
honestly-stuck) attempt.
