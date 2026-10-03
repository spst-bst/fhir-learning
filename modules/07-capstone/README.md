# Module 7 — Capstone: Lab Ingestion and a Versioned Risk-Signal Timeline

## Concepts

This module doesn't introduce new FHIR/HL7 mechanics — it wires together
what Modules 1-6 already taught, into one small service, and adds the one
genuinely new idea: **two different persistence policies for two
different kinds of data, in the same pipeline.**

- **Raw resources are idempotent** (Module 4/5's lesson): the same
  `Observation` landing twice — a retried request, a replayed export —
  must not duplicate. Upsert by id; the latest write wins.
- **Derived risk signals are append-only and versioned** — the opposite
  policy, on purpose. If an elevated A1c gets flagged today and a
  corrected (still-elevated) value arrives tomorrow, that's two real
  clinical facts, and an auditor (or a bug report, six months from now
  asking "why did the model flag this patient on March 3rd?") needs both
  to still exist. Overwriting the first flag with the second would erase
  history a compliance review might need.

The pipeline decides which policy applies by **comparing before
writing**: fetch the previously-stored resource (if any), compare it to
the incoming one, and only treat it as "new or changed" if the content
actually differs. An identical replay updates nothing and appends
nothing — pure no-op. A genuinely new value gets upserted into the raw
table *and*, if it crosses a risk threshold, appended as a new version in
the audit timeline. This compare-before-write step is the same shape as
a CDC (change-data-capture) pipeline deciding whether to fire a
downstream event, or an "outbox" pattern deciding whether a write is
worth publishing — don't re-trigger side effects on a no-op write.

**Structured logging**: instead of `print()` or a free-text log line,
each ingestion event is logged with machine-parseable fields (`event`,
`patient_id`, `risk_signal`, …) — the difference between a log a human
greps during an incident and a log a system can alert on, aggregate, or
query (Datadog, CloudWatch Insights, BigQuery over log sinks — whatever
your stack's equivalent is).

## Why it matters in practice

This *is* the risk-model ingestion pipeline, in miniature: lab results
come in (from a FHIR API or an HL7 feed), get normalized, get scored
against clinical thresholds, and anything the model should act on lands
in an **auditable history** — not just a mutable "current state" table.
When a regulator, an internal reviewer, or your own on-call engineer asks
"what did the system know, and when did it know it," the append-only
timeline is the answer. A `risk_score` column that just gets UPDATEd in
place can't answer that question at all.

## 3 Key Takeaways

1. **"Two persistence policies, one pipeline: idempotent upsert for raw
   data, append-only versioning for derived/audited data."** Knowing
   *which* policy a given table needs — and why conflating them is a
   bug, not a style choice — is the core judgment call of this module.
2. **"Compare-before-write to avoid re-firing side effects on a replay."**
   Same shape as change-data-capture or outbox patterns: a write that
   doesn't actually change anything shouldn't trigger downstream work
   twice.
3. **"Structured logs over free text — fields a system can query, not
   just a human can read."** `logger.info("...", extra={"patient_id":
   ..., "risk_signal": ...})` instead of an f-string: the difference
   between a log you can alert on and one you can only grep.

## What to do

No running FHIR server needed — this works against a local, in-memory
DuckDB connection and FastAPI's `TestClient`, both wired up for you in
the tests.

Two files:

- `exercises/capstone.py` — the pipeline logic: risk-threshold scoring,
  versioning, the append-only audit write, the compare-before-write
  ingestion orchestration, and structured JSON logging.
- `exercises/app.py` — two small FastAPI endpoints (`POST /ingest/fhir`,
  `GET /patients/{patient_id}/risk-timeline`) that wire `capstone.py`'s
  functions up to HTTP. If this is your first FastAPI route, it's meant
  to be — the mechanics are intentionally thin.

Fill in the TODOs in both files, then:

```bash
make test-07
```

Each function dumps its inputs/outputs as JSON when `DEBUG = True` (the
default) — pytest hides it unless you pass `-s`.

Hints before answers — ask if you get stuck for more than ~10 minutes on
any one function. Don't open `solutions/` until you've got a passing (or
honestly-stuck) attempt.

**Stretch (optional, not covered by the tests):** add a third ingestion
path, `POST /ingest/hl7`, accepting raw HL7 v2 ORU text and reusing
Module 4's parsing logic ahead of this module's same normalize → score →
audit pipeline. The point of leaving it out of the required exercise is
that it's mechanical once you've done the FHIR path — a good gut-check
for whether Module 4 actually stuck.

## Wrap-up: `ARCHITECTURE.md`

Once the code's green, write `ARCHITECTURE.md` (a template with guiding
questions is already in this directory) covering: idempotency, the audit
trail, PHI access controls, and model versioning. Writing it yourself
*is* the exercise — it's the same document you'd be asked to produce (or
defend in a design review) for this exact pipeline on the job, and
articulating the trade-offs from scratch teaches you far more than
reading a filled-in answer.
