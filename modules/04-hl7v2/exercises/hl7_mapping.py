"""Module 4 exercise: HL7 v2 (ADT/ORU) parsing and idempotent mapping to FHIR.

Uses the `hl7` package to parse raw HL7 v2 messages, then maps lab results
(ORU messages) into typed FHIR R4B Observation resources.

Run the tests with:
    make test-04
"""

from __future__ import annotations

from datetime import datetime, timezone

import hl7
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.reference import Reference

LOINC_SYSTEM = "http://loinc.org"

# HL7 OBX-11 result status -> FHIR Observation.status. Only the three most
# common codes are mapped; anything else should fail loudly rather than
# guess (same posture as Module 3's LOINC unit lookup).
HL7_TO_FHIR_STATUS = {
    "F": "final",
    "P": "preliminary",
    "C": "corrected",
}


def parse_message(raw: str) -> hl7.Message:
    """Parse raw HL7 v2 text into an hl7.Message.

    Gotcha: HL7 v2's real segment separator is \\r, but message text you
    paste into a test file or editor almost always has \\n (or \\r\\n)
    line endings instead. hl7.parse() takes that literally — feed it \\n
    and it treats everything after the first line as more data *inside*
    the first segment, not as separate segments. Normalize to \\r before
    parsing.

    Hint: str.replace() twice (first \\r\\n, then \\n) handles both cases.

    TODO: implement.
    """
    normalized = raw.replace("\r\n", "\r").replace("\n", "\r")
    return hl7.parse(normalized)


def message_type(message: hl7.Message) -> str:
    """Return the message type from MSH-9, e.g. "ORU^R01" or "ADT^A01".

    Hint: message.segment("MSH")[9] gives you the field directly (its
    str() is already "ORU^R01" — HL7 fields print their own ^ separators).

    TODO: implement.
    """
    msh = message.segment("MSH")
    return str(msh[9])


def patient_id(message: hl7.Message) -> str:
    """Return the patient id from PID-3's first component.

    PID-3 looks like "2b25e76e-...^^^HOSP^MR" (id^checkDigit^checkDigitScheme^
    assigningAuthority^idTypeCode). You want just the first component.

    Hint: message.segment("PID")[3][0][0] — [3] is the field, [0] is the
    first repetition, [0] is the first component of that repetition.

    TODO: implement.
    """
    pid = message.segment("PID")
    return str(pid[3][0][0])


def patient_display_name(message: hl7.Message) -> str:
    """Return "Given Family" from PID-5.

    PID-5 looks like "Doe^Jane" (family^given). Note the order is reversed
    from how you'll display it.

    Hint: same indexing pattern as patient_id: field[0] gives the first
    repetition, then index into that for family (component 0) and given
    (component 1).

    TODO: implement.
    """
    pid = message.segment("PID")
    name = pid[5][0]
    family = str(name[0])
    given = str(name[1]) if len(name) > 1 else ""
    return f"{given} {family}".strip()


def parse_hl7_datetime(raw: str) -> datetime:
    """Parse an HL7 timestamp ("YYYYMMDDHHMMSS", UTC) into a datetime.

    This course's data always supplies the full 14-digit form, so you can
    assume year/month/day/hour/minute/second are all present.

    Hint: slice raw into fixed-width chunks — raw[0:4] is the year, raw[4:6]
    the month, etc. — int() each slice. Build the datetime with
    tzinfo=timezone.utc.

    TODO: implement.
    """
    year, month, day = int(raw[0:4]), int(raw[4:6]), int(raw[6:8])
    hour = int(raw[8:10]) if len(raw) >= 10 else 0
    minute = int(raw[10:12]) if len(raw) >= 12 else 0
    second = int(raw[12:14]) if len(raw) >= 14 else 0
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def extract_observations(message: hl7.Message) -> list[dict]:
    """Extract every OBX segment into a plain dict:
        {"loinc_code", "display", "value", "unit", "status", "observed_at"}

    OBX-3 is "code^display^system" (use the same component-indexing
    pattern as patient_id). OBX-5 is the value, OBX-6 the unit, OBX-11 the
    result status code, OBX-14 the observation date/time (parse it with
    parse_hl7_datetime).

    An ADT message has no OBX segments at all —
    message.segments("OBX") raises KeyError in that case. Catch it and
    return an empty list.

    TODO: implement.
    """
    try:
        obx_segments = message.segments("OBX")
    except KeyError:
        return []

    observations = []
    for obx in obx_segments:
        code_field = obx[3][0]
        loinc_code = str(code_field[0])
        display = str(code_field[1]) if len(code_field) > 1 else ""
        unit = str(obx[6]) or None
        observed_at_raw = str(obx[14])
        observations.append(
            {
                "loinc_code": loinc_code,
                "display": display,
                "value": str(obx[5]),
                "unit": unit,
                "status": str(obx[11]),
                "observed_at": parse_hl7_datetime(observed_at_raw) if observed_at_raw else None,
            }
        )
    return observations


def observation_id_for(patient_id: str, obx: dict) -> str:
    """Build a deterministic Observation id from (patient_id, loinc_code,
    observed_at).

    This is the idempotency mechanism: the same lab result can arrive
    twice — redelivered after a network blip, or re-sent out of order from
    a queue — as two separate HL7 messages with different message control
    ids. Deriving the FHIR Observation's id from the clinical content
    instead of a per-message id means reprocessing the duplicate produces
    the *same* id, so an upsert overwrites instead of duplicating.

    Hint: f-string the three pieces together. Format obx["observed_at"]
    with .strftime("%Y%m%dT%H%M%SZ") so it's a clean id-safe string.

    TODO: implement.
    """
    timestamp = (
        obx["observed_at"].strftime("%Y%m%dT%H%M%SZ") if obx["observed_at"] else "unknown"
    )
    return f"{patient_id}-{obx['loinc_code']}-{timestamp}"


def build_fhir_observation(patient_id: str, obx: dict) -> Observation:
    """Build a typed FHIR Observation from one extract_observations() dict.

    Required: id (use observation_id_for), status (map obx["status"]
    through HL7_TO_FHIR_STATUS — raise ValueError if it's not in there),
    code (a CodeableConcept with one LOINC Coding), subject (a Reference
    to the patient), valueQuantity (value + unit), and effectiveDateTime
    (obx["observed_at"]).

    TODO: implement.
    """
    status = HL7_TO_FHIR_STATUS.get(obx["status"])
    if status is None:
        raise ValueError(f"unmapped HL7 result status: {obx['status']!r}")

    return Observation(
        id=observation_id_for(patient_id, obx),
        status=status,
        code=CodeableConcept(
            coding=[
                Coding(system=LOINC_SYSTEM, code=obx["loinc_code"], display=obx["display"])
            ]
        ),
        subject=Reference(reference=f"Patient/{patient_id}"),
        valueQuantity=Quantity(value=float(obx["value"]), unit=obx["unit"]),
        effectiveDateTime=obx["observed_at"],
    )
