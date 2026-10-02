"""Reference solution for Module 2. Don't peek until you've had a real go."""

from __future__ import annotations

import httpx
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.diagnosticreport import DiagnosticReport
from fhir.resources.R4B.dosage import Dosage
from fhir.resources.R4B.familymemberhistory import FamilyMemberHistory
from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.reference import Reference

DEFAULT_BASE_URL = "http://localhost:8080/fhir"


def fetch_patient(patient_id: str, base_url: str = DEFAULT_BASE_URL) -> Patient:
    resp = httpx.get(f"{base_url}/Patient/{patient_id}")
    resp.raise_for_status()
    return Patient.model_validate(resp.json())


def patient_display_name(patient: Patient) -> str:
    names = patient.name or []
    if not names:
        return "(no name on file)"
    name = next((n for n in names if n.use == "official"), names[0])
    given = " ".join(name.given or [])
    family = name.family or ""
    return f"{given} {family}".strip()


def fetch_observations(
    patient_id: str, loinc_code: str | None = None, base_url: str = DEFAULT_BASE_URL
) -> list[Observation]:
    params = {"patient": patient_id, "_count": 100}
    if loinc_code:
        params["code"] = f"http://loinc.org|{loinc_code}"
    resp = httpx.get(f"{base_url}/Observation", params=params)
    resp.raise_for_status()
    bundle = resp.json()
    return [Observation.model_validate(e["resource"]) for e in bundle.get("entry", [])]


def latest_observation(observations: list[Observation]) -> Observation | None:
    dated = [o for o in observations if o.effectiveDateTime is not None]
    if not dated:
        return None
    return max(dated, key=lambda o: o.effectiveDateTime)


def fetch_conditions(patient_id: str, base_url: str = DEFAULT_BASE_URL) -> list[Condition]:
    resp = httpx.get(f"{base_url}/Condition", params={"patient": patient_id, "_count": 100})
    resp.raise_for_status()
    bundle = resp.json()
    return [Condition.model_validate(e["resource"]) for e in bundle.get("entry", [])]


def fetch_family_history(
    patient_id: str, base_url: str = DEFAULT_BASE_URL
) -> list[FamilyMemberHistory]:
    resp = httpx.get(
        f"{base_url}/FamilyMemberHistory", params={"patient": patient_id, "_count": 100}
    )
    resp.raise_for_status()
    bundle = resp.json()
    return [
        FamilyMemberHistory.model_validate(e["resource"]) for e in bundle.get("entry", [])
    ]


def summarize_family_history(records: list[FamilyMemberHistory]) -> list[str]:
    summaries = []
    for record in records:
        relationship = record.relationship.coding[0].display
        for condition in record.condition:
            summaries.append(f"{relationship}: {condition.code.text}")
    return summaries


def fetch_diagnostic_reports_with_results(
    patient_id: str, loinc_code: str, base_url: str = DEFAULT_BASE_URL
) -> tuple[list[DiagnosticReport], list[Observation]]:
    params = {
        "patient": patient_id,
        "code": f"http://loinc.org|{loinc_code}",
        "_include": "DiagnosticReport:result",
        "_count": 100,
    }
    resp = httpx.get(f"{base_url}/DiagnosticReport", params=params)
    resp.raise_for_status()
    bundle = resp.json()

    reports: list[DiagnosticReport] = []
    observations: list[Observation] = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        if resource["resourceType"] == "DiagnosticReport":
            reports.append(DiagnosticReport.model_validate(resource))
        elif resource["resourceType"] == "Observation":
            observations.append(Observation.model_validate(resource))
    return reports, observations


def build_medication_request(
    patient_id: str, medication_text: str, dosage_text: str
) -> MedicationRequest:
    return MedicationRequest(
        status="active",
        intent="order",
        subject=Reference(reference=f"Patient/{patient_id}"),
        medicationCodeableConcept=CodeableConcept(text=medication_text),
        dosageInstruction=[Dosage(text=dosage_text)],
    )
