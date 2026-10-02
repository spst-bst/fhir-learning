# FHIR / Healthcare Interoperability Course

A hands-on, ~10–12 hour course to get from "no FHIR/HL7 experience" to
"confident in a healthtech interview and comfortable with real code." Built
for a senior engineering leader with a Java/GCP/distributed-systems/pharmacy
integrations/HIPAA background, prepping for a Director/EM interview at a
cancer-risk-modeling startup.

All data is synthetic (generated with [Synthea](https://github.com/synthetichealth/synthea)).
**No real PHI anywhere in this repo.**

## Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/), pytest
- [HAPI FHIR](https://hapifhir.io/) server, local, in Docker
- `fhir.resources` (Pydantic FHIR models), `httpx`, `hl7` (HL7 v2)
- FastAPI for the capstone

## Quick start

```bash
make install     # uv sync — installs the venv
make up           # start HAPI FHIR in Docker (http://localhost:8080/fhir)
make load-data    # load the synthetic Synthea patients
make test-01      # run Module 1's tests
```

See [PROGRESS.md](PROGRESS.md) for the full checklist.

## How this course works

```
modules/
  01-setup/
    README.md       <- concepts (1 page), why it matters, interview talking points
    exercises/       <- starter code with TODOs + failing pytest tests
    solutions/       <- reference solutions (don't peek until you've tried)
  02-fhir-resources/
  03-code-systems-data-quality/
  04-hl7v2/
  05-bulk-fhir/
  06-smart-on-fhir/
  07-capstone/
```

Work through modules in order. Each module's README tells you what to do.
Run `make test-0N` to check your work for module N — tests fail until the
TODOs are filled in correctly.

Modules 2–7 unlock (get fully built out) as you complete the ones before
them — ask for the next module when you're ready.

## Stopping / resetting

```bash
make down          # stop the stack (keeps data)
make reset-data     # wipe and reload the synthetic patients from scratch
```

## Other docs

- [PROGRESS.md](PROGRESS.md) — your checklist
- [INTERVIEW_NOTES.md](INTERVIEW_NOTES.md) — one-page summary for the interview itself
