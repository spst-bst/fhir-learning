# Module 3 — Code Systems & Data Quality: LOINC, SNOMED CT, ICD-10, RxNorm

## Concepts

Module 2 assumed clean, valid FHIR and let typed parsing catch structural
problems. Real partner feeds also have problems typed parsing *can't*
catch on its own — a structurally valid `Observation` can still have a
sloppily-formatted code, a missing unit, or be a flat-out duplicate of one
you already ingested. This module works one layer below typed parsing,
scrubbing raw JSON before it gets there.

Four code systems come up constantly in US clinical data, each owned by a
different standards body and used for a different purpose:

- **LOINC** (labs, measurements) — e.g. `4548-4` = Hemoglobin A1c.
- **SNOMED CT** (clinical findings/conditions, general-purpose) — e.g.
  `254837009` = malignant neoplasm of breast.
- **ICD-10-CM** (conditions, but for billing/diagnosis coding — what
  claims systems actually use).
- **RxNorm** (medications) — normalizes drug names/strengths/forms across
  vendors.

A single `Condition` resource often carries *both* a SNOMED CT coding and
an ICD-10-CM coding in the same `CodeableConcept` — clinical modeling and
billing, side by side. Knowing which system you're looking at, and that a
`CodeableConcept` can hold more than one, matters for every mapping
decision downstream.

## Why it matters for a clinical-data startup

A risk model ingesting from multiple EHRs sees the same lab sent with
inconsistent code formatting, values missing their unit, and the same
result duplicated across two partner feeds — constantly, not as edge
cases. Silently mis-normalizing a code, guessing a unit, or double-counting
a duplicated lab result doesn't crash anything; it just quietly corrupts a
risk score. The fix is the same instinct as Module 2's typed parsing,
applied earlier: normalize deliberately, fail loudly when you can't, and
never guess when you'd rather raise.

## 3 Interview Talking Points

1. **"The same clinical fact gets coded differently by system and by
   purpose — SNOMED CT for clinical modeling, ICD-10-CM for billing, same
   diagnosis."** This is a crosswalk problem, same shape as reconciling
   SKUs or account ids across two systems of record in any data platform
   you've built.
2. **"Missing or inconsistent units on a lab value are a silent
   correctness bug, not a missing-data bug."** `5.43` with no unit isn't
   usably "missing" — it's actively wrong if the pipeline assumes the
   wrong one. Treat inferring it as a deliberate, auditable decision
   (explicit lookup table), not a guess, and fail loudly when you can't
   infer it confidently.
3. **"Partner feeds duplicate data across channels — dedup logic belongs
   at the ingestion boundary, not scattered downstream."** Same posture as
   idempotent message consumers in any event-driven system: define the
   identity key once (patient + code + timestamp here), dedupe on it in
   one place.

## What to do

No running FHIR server needed for this one — it works directly on raw
dicts. Open `exercises/code_quality.py`, fill in the TODOs, then:

```bash
make test-03
```

Hints before answers — ask if you get stuck for more than ~10 minutes on
any one function. Don't open `solutions/` until you've got a passing (or
honestly-stuck) attempt.
