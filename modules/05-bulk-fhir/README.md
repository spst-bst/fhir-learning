# Module 5 — Bulk FHIR: $export and NDJSON Ingest

## Concepts

Modules 2-4 all pull data **one resource (or one message) at a time** — fine
for "show me this patient," wrong for "give me every patient your partner
has." Pulling a population of 50,000 patients via `GET /Observation?patient=X`
in a loop is thousands of round trips. The **Bulk Data Access IG** ("Flat
FHIR") defines a bulk alternative: `$export`.

The flow is **asynchronous** because a full-population export can take
minutes to hours server-side:

1. **Kick off**: `GET [base]/Patient/$export` (or `/Group/{id}/$export` for a
   cohort, or system-level `/$export` for everything) with header
   `Prefer: respond-async`. The server replies `202 Accepted` immediately —
   no body — with a `Content-Location` header pointing at a status/poll URL.
   It has not produced anything yet; it has only accepted the job.
2. **Poll**: `GET` that status URL repeatedly. While the job runs, the
   server replies `202 Accepted` again (sometimes with `X-Progress`). When
   done, it replies `200 OK` with a JSON **manifest**: a list of output
   files, each `{"type": "Observation", "url": "https://.../obs_1.ndjson"}`
   — one or more files *per resource type*, since a real export splits large
   types across multiple files.
3. **Download + parse**: each output file is **NDJSON** — newline-delimited
   JSON, one resource per line, not a JSON array. You stream it line by
   line rather than loading one giant array into memory, because these
   files can be gigabytes for a real population.
4. **Ingest**: load the parsed resources into local storage (DuckDB here)
   for downstream querying. Bulk resources already carry their own stable
   `id` from the source system, so unlike Module 4's HL7 feed, idempotency
   is simpler: re-ingesting the same file twice should still leave one row
   per `(resourceType, id)`, not two.

This module works directly on the request/response *shapes* (headers,
status codes, manifest JSON, NDJSON text) rather than standing up a real
async job — same posture as Module 3 (raw dicts) and Module 4 (raw HL7
text): the local HAPI server you've been running doesn't implement
`$export`, and a real one takes minutes to finish by design, which would
make for a bad exercise loop.

## Why it matters for a clinical-data startup

A risk model that scores an existing population needs a **nightly or
weekly bulk refresh**, not 50,000 individual polling loops — that's exactly
the `$export` → NDJSON → warehouse pattern. And because exports get
re-run (a job fails partway, a backfill gets re-triggered, someone re-runs
last night's job to be safe), the ingest step has to be **idempotent**: the
same resource landing twice must not double-count in a risk score, and a
resource that *changed* between runs (corrected lab value, updated
condition) must overwrite the old row, not create a duplicate alongside it.

## 3 Interview Talking Points

1. **"$export is async because bulk jobs are slow — kickoff returns a poll
   URL, not data."** Any time an API hands back `202` + a `Content-Location`
   (or `Location`) header instead of a body, that's the same async-job
   pattern: accept now, let the caller poll for completion.
2. **"NDJSON, not a JSON array, because files are streamed and can be
   huge."** One resource per line means you can process (or even start
   ingesting) a multi-gigabyte export without ever holding the whole file
   in memory — same reason log pipelines and ETL tools favor NDJSON/JSONL
   over a single top-level array.
3. **"Idempotent ingest by (resourceType, id), same principle as Module
   4's content-derived id — just easier here because bulk resources already
   have one."** A re-run of the same export, or a retried job, should
   leave the warehouse in the same state as running it once.

## What to do

No running FHIR server needed for this one — it works directly on raw
HTTP response shapes (headers, status codes, manifest JSON) and NDJSON
text, plus a local DuckDB connection for the ingest step. Open
`exercises/bulk_fhir.py`, fill in the TODOs, then:

```bash
make test-05
```

Each function dumps its inputs/outputs as JSON when `DEBUG = True` (the
default) in `bulk_fhir.py` — pytest hides it unless you pass `-s`:

```bash
uv run pytest modules/05-bulk-fhir/exercises -v -s
```

Hints before answers — ask if you get stuck for more than ~10 minutes on
any one function. Don't open `solutions/` until you've got a passing (or
honestly-stuck) attempt.
