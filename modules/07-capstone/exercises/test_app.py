"""Tests for app.py's FastAPI wiring, via TestClient.

app.state.db is one shared in-memory DuckDB connection for the whole
test session (same as a real app's one connection pool) — tests use
distinct patient ids so they don't interfere with each other.
"""

import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import app as capstone_app  # noqa: E402

client = TestClient(capstone_app.app)


def make_observation(resource_id: str, loinc_code: str, value: float, unit: str, patient_id: str) -> dict:
    return {
        "resourceType": "Observation",
        "id": resource_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": loinc_code}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": value, "unit": unit},
    }


def test_post_ingest_fhir_returns_risk_signal():
    obs = make_observation("app-obs1", "4548-4", 7.1, "%", patient_id="app-p1")
    response = client.post("/ingest/fhir", json=obs)

    assert response.status_code == 200
    body = response.json()
    assert body["risk_signal"] == "elevated_a1c"
    assert body["version"] == 1


def test_get_risk_timeline_returns_versions_in_order():
    patient_id = "app-p2"
    client.post("/ingest/fhir", json=make_observation("app-obs2", "4548-4", 7.1, "%", patient_id))
    client.post("/ingest/fhir", json=make_observation("app-obs2", "4548-4", 7.8, "%", patient_id))

    response = client.get(f"/patients/{patient_id}/risk-timeline")

    assert response.status_code == 200
    timeline = response.json()
    assert [row["version"] for row in timeline] == [1, 2]


def test_ingest_fhir_duplicate_does_not_duplicate_timeline():
    patient_id = "app-p3"
    obs = make_observation("app-obs3", "4548-4", 7.1, "%", patient_id)
    client.post("/ingest/fhir", json=obs)
    client.post("/ingest/fhir", json=dict(obs))

    response = client.get(f"/patients/{patient_id}/risk-timeline")

    assert len(response.json()) == 1
