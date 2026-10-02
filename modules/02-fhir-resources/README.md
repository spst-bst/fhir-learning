# Module 2 — FHIR Resources: Typed Models, References, Search, Bundles

## Concepts

Module 1 treated every response as a plain `dict`. That's fragile — nothing
stops you from typo'ing `"valueQuantitty"` and getting `None` back silently.
**`fhir.resources`** gives you Pydantic models for every FHIR resource type,
so malformed or unexpected data fails loudly, with a real error, at the
point you parse it — not three functions later when a risk score comes out
wrong.

Gotcha worth knowing cold: `fhir.resources` defaults to **FHIR R5**
(`from fhir.resources.patient import Patient`), but this HAPI server (like
almost every production EHR today) speaks **R4**. Use the R4B submodule
instead: `from fhir.resources.R4B.patient import Patient`. Mixing these up
gives you confusing validation errors on perfectly valid R4 data — a
version-mismatch class of bug you've definitely hit before in distributed
systems, just with a different vocabulary.

This module works with the six resource types named in the course goals —
`Patient`, `Observation`, `Condition`, `DiagnosticReport`,
`FamilyMemberHistory`, `MedicationRequest` — and three mechanics that matter
more than any single resource type:

- **Search parameters**: `?code=` (token search on a coded value, e.g. a
  LOINC code), `?patient=` (reference search — "everything about this
  patient"), combined in one query.
- **References**: FHIR references are loose/logical — just a string like
  `"Patient/123"` — not an enforced foreign key. They can dangle if the
  referenced resource is missing or you got the id wrong.
- **`_include`**: fetch a resource *and* everything it references in one
  round trip, instead of N+1 follow-up calls. `GET
  DiagnosticReport?...&_include=DiagnosticReport:result` returns the report
  plus every `Observation` it points to, tagged `search.mode: "include"` so
  you can tell matched-vs-pulled-in resources apart.

You'll also **construct** a resource for the first time (a new
`MedicationRequest`, in memory, not submitted) — the capstone needs you
comfortable building FHIR resources, not just reading them.

## Why it matters for a clinical-data startup

A risk model ingesting from multiple EHRs is going to see malformed,
incomplete, or just-plain-wrong FHIR from partners constantly. Typed
parsing turns "silently wrong data poisons a risk score" into "loud
validation error at ingestion time" — the difference between a data-quality
incident you catch in a pipeline and one a clinician notices. And knowing
`_include` exists is the difference between a per-patient chart pull making
1 request or 40.

## 3 Interview Talking Points

1. **"Typed parsing at the integration boundary turns silent data
   corruption into a loud, early failure."** Same principle as strict
   deserialization in any service boundary you've built — the earlier you
   reject bad data, the cheaper the incident.
2. **"`_include` avoids N+1 — the same lesson as eager-loading in any ORM
   or distributed system."** Across dozens of partner EHRs, this is the
   difference between a chart pull taking one request or forty, with all
   the latency and partial-failure risk that implies.
3. **"FHIR references are logical, not enforced — dangling references are
   a normal, expected failure mode, not a bug."** Talk about defensive
   handling of broken or missing references from partner data, the same
   posture you'd take with any eventually-consistent or loosely-coupled
   system.

## What to do

```bash
make up          # if not already running
make load-data    # if not already loaded
```

Open `exercises/fhir_resources.py`, fill in the TODOs, then:

```bash
make test-02
```
