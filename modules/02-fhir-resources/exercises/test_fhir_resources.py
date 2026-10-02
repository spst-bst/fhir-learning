"""Tests for fhir_resources.py.

These hit a real, running HAPI FHIR server loaded with the course's Synthea
sample data. Before running:
    make up
    make load-data
"""

import pathlib
import sys
from datetime import datetime, timezone

import httpx
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fhir_resources  # noqa: E402

BASE_URL = fhir_resources.DEFAULT_BASE_URL

# Known values baked into the committed Synthea sample data
# (data/synthea/fhir/*.json) — fixed because the data is fixed.
KATLYN_ID = "2b25e76e-99af-e31a-55ec-62f57d9ddc2f"
ELLSWORTH_ID = "660a3a4d-356e-be2b-64cd-33cee49924de"  # diabetes, CHF
BRANDY_ID = "00f9f584-3d61-c739-d204-0af484e86d5a"  # breast cancer + family history

HBA1C_LOINC = "4548-4"
BASIC_METABOLIC_PANEL_LOINC = "51990-0"


@pytest.fixture(scope="module", autouse=True)
def _require_server():
    try:
        httpx.get(f"{BASE_URL}/metadata", timeout=5.0).raise_for_status()
    except httpx.HTTPError:
        pytest.skip(
            f"HAPI FHIR not reachable at {BASE_URL}. Run 'make up && make load-data' first."
        )


def test_fetch_patient_returns_typed_patient():
    patient = fhir_resources.fetch_patient(KATLYN_ID)
    assert patient.id == KATLYN_ID
    assert isinstance(patient, fhir_resources.Patient)


def test_patient_display_name_uses_official_name():
    patient = fhir_resources.fetch_patient(KATLYN_ID)
    name = fhir_resources.patient_display_name(patient)
    assert name == "Katlyn29 Torie475 Weissnat378"


def test_fetch_observations_filters_by_loinc_code():
    observations = fhir_resources.fetch_observations(ELLSWORTH_ID, loinc_code=HBA1C_LOINC)
    assert len(observations) == 12
    for obs in observations:
        codes = {c.code for c in obs.code.coding}
        assert HBA1C_LOINC in codes


def test_fetch_observations_without_code_returns_more_than_filtered():
    all_obs = fhir_resources.fetch_observations(ELLSWORTH_ID)
    hba1c_obs = fhir_resources.fetch_observations(ELLSWORTH_ID, loinc_code=HBA1C_LOINC)
    assert len(all_obs) > len(hba1c_obs)


def test_latest_observation_picks_most_recent():
    observations = fhir_resources.fetch_observations(ELLSWORTH_ID, loinc_code=HBA1C_LOINC)
    latest = fhir_resources.latest_observation(observations)
    assert latest is not None
    assert latest.effectiveDateTime == datetime(2026, 4, 10, 19, 53, 14, tzinfo=timezone.utc)
    assert float(latest.valueQuantity.value) == pytest.approx(5.43)
    assert latest.valueQuantity.unit == "%"


def test_latest_observation_of_empty_list_is_none():
    assert fhir_resources.latest_observation([]) is None


def test_fetch_conditions_includes_known_condition():
    conditions = fhir_resources.fetch_conditions(BRANDY_ID)
    texts = {c.code.text for c in conditions if c.code and c.code.text}
    assert any("breast" in t.lower() for t in texts)


def test_fetch_and_summarize_family_history():
    records = fhir_resources.fetch_family_history(BRANDY_ID)
    assert len(records) == 2
    summaries = fhir_resources.summarize_family_history(records)
    assert "Mother: Malignant neoplasm of breast (disorder)" in summaries
    assert "Maternal Grandmother: Malignant tumor of ovary (disorder)" in summaries


def test_fetch_diagnostic_reports_with_results_uses_include():
    reports, observations = fhir_resources.fetch_diagnostic_reports_with_results(
        ELLSWORTH_ID, BASIC_METABOLIC_PANEL_LOINC
    )
    assert len(reports) == 12
    assert len(observations) > 0
    # every report should reference at least one of the included observations
    observation_ids = {o.id for o in observations}
    referenced_ids = {
        ref.reference.split("/")[-1]
        for report in reports
        for ref in (report.result or [])
    }
    assert referenced_ids & observation_ids


def test_build_medication_request_has_required_fields():
    mr = fhir_resources.build_medication_request(
        KATLYN_ID, "Amoxicillin 250mg", "Take 1 capsule 3 times daily for 10 days"
    )
    assert mr.status == "active"
    assert mr.intent == "order"
    assert mr.subject.reference == f"Patient/{KATLYN_ID}"
    assert mr.medicationCodeableConcept.text == "Amoxicillin 250mg"
    assert mr.dosageInstruction[0].text == "Take 1 capsule 3 times daily for 10 days"
