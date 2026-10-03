"""Reference solution for Module 4. Don't peek until you've had a real go."""

from __future__ import annotations

from datetime import datetime, timezone

import hl7
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.reference import Reference

LOINC_SYSTEM = "http://loinc.org"

HL7_TO_FHIR_STATUS = {
    "F": "final",
    "P": "preliminary",
    "C": "corrected",
}


def parse_message(raw: str) -> hl7.Message:
    normalized = raw.replace("\r\n", "\r").replace("\n", "\r")
    return hl7.parse(normalized)


def message_type(message: hl7.Message) -> str:
    msh = message.segment("MSH")
    return str(msh[9])


def patient_id(message: hl7.Message) -> str:
    pid = message.segment("PID")
    return str(pid[3][0][0])


def patient_display_name(message: hl7.Message) -> str:
    pid = message.segment("PID")
    name = pid[5][0]
    family = str(name[0])
    given = str(name[1]) if len(name) > 1 else ""
    return f"{given} {family}".strip()


def parse_hl7_datetime(raw: str) -> datetime:
    year, month, day = int(raw[0:4]), int(raw[4:6]), int(raw[6:8])
    hour = int(raw[8:10]) if len(raw) >= 10 else 0
    minute = int(raw[10:12]) if len(raw) >= 12 else 0
    second = int(raw[12:14]) if len(raw) >= 14 else 0
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def extract_observations(message: hl7.Message) -> list[dict]:
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
    timestamp = (
        obx["observed_at"].strftime("%Y%m%dT%H%M%SZ") if obx["observed_at"] else "unknown"
    )
    return f"{patient_id}-{obx['loinc_code']}-{timestamp}"


def build_fhir_observation(patient_id: str, obx: dict) -> Observation:
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
