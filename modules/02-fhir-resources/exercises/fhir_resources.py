"""Module 2 exercise: typed FHIR resources, references, search, bundles.

Uses fhir.resources' R4B models (this HAPI server speaks FHIR R4; the
top-level fhir.resources import defaults to R5 — use R4B explicitly).

Run the tests with:
    make test-02
"""

from __future__ import annotations

import json

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

# Set to False to quiet the request/response dump below.
DEBUG = True


def _debug_print(resp: httpx.Response) -> None:
    if not DEBUG:
        return
    print(f"\n--- {resp.request.method} {resp.request.url} -> {resp.status_code} ---")
    print(json.dumps(resp.json(), indent=2))


def fetch_patient(patient_id: str, base_url: str = DEFAULT_BASE_URL) -> Patient:
    """Fetch a Patient by id and parse it into a typed Patient model.

    Hint: GET {base_url}/Patient/{patient_id}, then
    Patient.model_validate(response_json).

    TODO: implement.
    """
    resp = httpx.get(f"{base_url}/Patient/{patient_id}")
    resp.raise_for_status()
    _debug_print(resp)
    return Patient.model_validate(resp.json())


def patient_display_name(patient: Patient) -> str:
    """Return "Given Family" using the patient's official name.

    A Patient can have multiple HumanName entries (official, nickname,
    maiden name...). Prefer the one with use == "official"; fall back to
    the first name entry if none is marked official; return
    "(no name on file)" if there are no names at all.

    Hint: patient.name is a list[HumanName]. HumanName has .use, .given
    (a list of strings), and .family (a string).

    TODO: implement.
    """
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
    """Search for a patient's Observations, optionally filtered by LOINC code.

    Hint: GET {base_url}/Observation?patient={patient_id}, adding
    &code=http://loinc.org|{loinc_code} when loinc_code is given. Pass
    _count=100 so you don't silently miss results past the first page.
    Parse each bundle entry's resource into an Observation model.

    TODO: implement. Return an empty list if there are no matches.
    """
    params = {"patient": patient_id, "_count": 100}
    if loinc_code:
        params["code"] = f"http://loinc.org|{loinc_code}"
    resp = httpx.get(f"{base_url}/Observation", params=params)
    resp.raise_for_status()
    _debug_print(resp)
    bundle = resp.json()
    return [Observation.model_validate(e["resource"]) for e in bundle.get("entry", [])]


def latest_observation(observations: list[Observation]) -> Observation | None:
    """Return the Observation with the most recent effectiveDateTime.

    Hint: Observation.effectiveDateTime parses into a real datetime you can
    compare directly. Return None for an empty list, and skip any
    observations where effectiveDateTime is None (don't let them crash the
    comparison).

    TODO: implement.
    """
    dated = [o for o in observations if o.effectiveDateTime is not None]
    if not dated:
        return None
    return max(dated, key=lambda o: o.effectiveDateTime)


def fetch_conditions(patient_id: str, base_url: str = DEFAULT_BASE_URL) -> list[Condition]:
    """Search for all Conditions for a patient, parsed into typed models.

    TODO: implement, same pattern as fetch_observations but for Condition.
    """
    resp = httpx.get(f"{base_url}/Condition", params={"patient": patient_id, "_count": 100})
    resp.raise_for_status()
    _debug_print(resp)
    bundle = resp.json()
    return [Condition.model_validate(e["resource"]) for e in bundle.get("entry", [])]


def fetch_family_history(
    patient_id: str, base_url: str = DEFAULT_BASE_URL
) -> list[FamilyMemberHistory]:
    """Search for all FamilyMemberHistory records for a patient.

    TODO: implement, same pattern as fetch_conditions.
    """
    resp = httpx.get(
        f"{base_url}/FamilyMemberHistory", params={"patient": patient_id, "_count": 100}
    )
    resp.raise_for_status()
    _debug_print(resp)
    bundle = resp.json()
    return [FamilyMemberHistory.model_validate(e["resource"]) for e in bundle.get("entry", [])]


def summarize_family_history(records: list[FamilyMemberHistory]) -> list[str]:
    """Format each record as "{relationship display}: {condition text}".

    Hint: record.relationship.coding[0].display gives you e.g. "Mother".
    record.condition is a list; each item has .code.text, e.g.
    "Malignant neoplasm of breast (disorder)". This course's sample data
    always has exactly one condition per record, but don't assume that in
    general — loop over record.condition.

    TODO: implement. Return one string per (record, condition) pair.
    """
    summaries = []
    for record in records:
        relationship = record.relationship.coding[0].display
        for condition in record.condition:
            summaries.append(f"{relationship}: {condition.code.text}")
    return summaries


def fetch_diagnostic_reports_with_results(
    patient_id: str, loinc_code: str, base_url: str = DEFAULT_BASE_URL
) -> tuple[list[DiagnosticReport], list[Observation]]:
    """Fetch DiagnosticReports for a patient by LOINC code, plus every
    Observation they reference — in ONE request, using _include.

    Hint: GET {base_url}/DiagnosticReport with params:
      patient={patient_id}, code=http://loinc.org|{loinc_code},
      _include=DiagnosticReport:result, _count=100

    The response Bundle mixes DiagnosticReport and Observation entries.
    Each entry has an entry["resource"]["resourceType"] you can switch on
    to sort them into two typed lists.

    TODO: implement. Return (diagnostic_reports, observations).
    """
    params = {
        "patient": patient_id,
        "code": f"http://loinc.org|{loinc_code}",
        "_include": "DiagnosticReport:result",
        "_count": 100,
    }
    resp = httpx.get(f"{base_url}/DiagnosticReport", params=params)
    resp.raise_for_status()
    _debug_print(resp)
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
    """Construct a new MedicationRequest resource in memory (don't submit it).

    Required for a valid MedicationRequest: status="active", intent="order",
    a subject Reference to the patient, a medicationCodeableConcept with
    .text set to medication_text, and a dosageInstruction list containing
    one Dosage with .text set to dosage_text.

    This is the first resource you've built rather than read — the
    capstone (Module 7) does a lot more of this.

    TODO: implement and return the MedicationRequest.
    """
    return MedicationRequest(
        status="active",
        intent="order",
        subject=Reference(reference=f"Patient/{patient_id}"),
        medicationCodeableConcept=CodeableConcept(text=medication_text),
        dosageInstruction=[Dosage(text=dosage_text)],
    )
