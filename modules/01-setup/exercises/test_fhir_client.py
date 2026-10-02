"""Tests for fhir_client.py.

These hit a real, running HAPI FHIR server. Before running:
    make up
    make load-data

If the server isn't reachable, every test here is skipped with a clear
message rather than failing with a confusing connection error.
"""

import pathlib
import sys

import httpx
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fhir_client  # noqa: E402

BASE_URL = fhir_client.DEFAULT_BASE_URL

# Known values baked into the committed Synthea sample data
# (data/synthea/fhir/*.json) — fixed because the data is fixed.
KATLYN_ID = "2b25e76e-99af-e31a-55ec-62f57d9ddc2f"
KATLYN_FAMILY_NAME = "Weissnat378"
EXPECTED_PATIENT_COUNT = 5


@pytest.fixture(scope="module", autouse=True)
def _require_server():
    try:
        httpx.get(f"{BASE_URL}/metadata", timeout=5.0).raise_for_status()
    except httpx.HTTPError:
        pytest.skip(
            f"HAPI FHIR not reachable at {BASE_URL}. Run 'make up && make load-data' first."
        )


def test_capability_statement_reports_fhir_r4():
    capability = fhir_client.get_capability_statement()
    assert capability["resourceType"] == "CapabilityStatement"
    assert capability["fhirVersion"] == "4.0.1"


def test_count_resources_counts_loaded_patients():
    assert fhir_client.count_resources("Patient") == EXPECTED_PATIENT_COUNT


def test_get_patient_by_id_returns_matching_patient():
    patient = fhir_client.get_patient_by_id(KATLYN_ID)
    assert patient["resourceType"] == "Patient"
    assert patient["id"] == KATLYN_ID


def test_search_patients_by_family_name_finds_known_patient():
    results = fhir_client.search_patients_by_family_name(KATLYN_FAMILY_NAME)
    assert len(results) == 1
    assert results[0]["id"] == KATLYN_ID


def test_search_patients_by_family_name_no_match_returns_empty_list():
    results = fhir_client.search_patients_by_family_name("NoSuchFamilyNameXYZ")
    assert results == []


def test_get_conditions_for_patient_includes_known_condition():
    conditions = fhir_client.get_conditions_for_patient(KATLYN_ID)
    assert len(conditions) > 0
    assert all(c["resourceType"] == "Condition" for c in conditions)
    texts = {c["code"]["text"] for c in conditions if "text" in c.get("code", {})}
    assert any("sinusitis" in t.lower() for t in texts)


def test_get_conditions_for_unknown_patient_returns_empty_list():
    conditions = fhir_client.get_conditions_for_patient("not-a-real-id")
    assert conditions == []
