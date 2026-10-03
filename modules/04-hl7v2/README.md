# Module 4 — HL7 v2: ADT and ORU Messages

## Concepts

**HL7 v2** predates FHIR by decades (1987) and is still how most hospitals
move data internally today — ADT (admit/discharge/transfer) and ORU
(observation result, i.e. lab results) messages flying over MLLP/TCP
between the EHR, the lab system, and everything else on a hospital
network. FHIR didn't replace it; it sits on top for external/API access
while HL7 v2 keeps moving data inside the four walls. A clinical-data
startup ingesting straight from a hospital, rather than through an EHR's
FHIR API, is an HL7 v2 feed.

The format itself: pipe-delimited segments, each a 3-letter code (`MSH`
header, `PID` patient, `OBR` order, `OBX` one result per segment), fields
within a segment separated by `|`, components within a field by `^`.
`PID-3` (`id^^^authority^type`) is patient identifiers; `OBX-3`
(`code^display^system`) is one result's coded identifier — same `^`
pattern you'll use repeatedly.

Gotcha worth knowing cold: the real segment separator is `\r`, not `\n`.
Message text you paste into a file or test fixture almost always has `\n`
line endings — parse that literally and the library reads everything
after line one as data glued onto the first segment, not as separate
segments. Normalize before parsing, every time.

This module parses both ADT and ORU messages, then maps ORU lab results
into typed FHIR `Observation` resources — the same Pydantic models from
Module 2, now built from HL7 instead of read from a FHIR server.

## Why it matters for a clinical-data startup

The same lab result can arrive twice: a network blip triggers a resend, a
message gets redelivered out of order from a queue, two feeds send the
same result through different paths. Each arrives as its own HL7 message
with its own message-control id, so "has this message id been seen
before" doesn't catch the duplicate. The fix is **idempotent mapping**:
derive the FHIR resource's id from the clinical content itself (patient +
code + timestamp) rather than from the message. Reprocessing the same
result then produces the *same* id — an upsert overwrites instead of
creating a duplicate Observation that would double-count in a risk score.

## 3 Interview Talking Points

1. **"HL7 v2 didn't go away — FHIR is the external API, v2 still moves
   data inside the hospital."** Any integration that talks to a hospital
   system directly (not through an EHR's FHIR endpoint) is probably
   consuming HL7 v2 off an interface engine (Mirth, Rhapsody, Cloverleaf).
2. **"ADT tracks where a patient is; ORU delivers what was measured."**
   Different message types, different urgency and failure modes — a
   missed ADT means your care-location data is stale, a missed ORU means
   a lab result silently never reaches the model.
3. **"Idempotent mapping — derive the id from content, not the
   transport."** Same principle as idempotency keys in payments or
   exactly-once delivery in any message queue you've built: never trust
   "I haven't seen this message id before" as your only duplicate check
   when the content itself can tell you more directly.

## What to do

No running FHIR server needed for this one — it works directly on raw HL7
v2 message text. Open `exercises/hl7_mapping.py`, fill in the TODOs, then:

```bash
make test-04
```

Hints before answers — ask if you get stuck for more than ~10 minutes on
any one function. Don't open `solutions/` until you've got a passing (or
honestly-stuck) attempt.
