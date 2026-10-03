"""Tests for capstone.py.

No running FHIR server needed — these work against a local, in-memory
DuckDB connection.
"""

import io
import json
import logging
import pathlib
import sys

import duckdb
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import capstone  # noqa: E402


def make_observation(resource_id: str, loinc_code: str, value: float, unit: str, patient_id: str = "p1") -> dict:
    return {
        "resourceType": "Observation",
        "id": resource_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": loinc_code}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "valueQuantity": {"value": value, "unit": unit},
    }


@pytest.fixture
def con():
    return duckdb.connect(":memory:")


@pytest.fixture
def logger():
    return capstone.configure_logging(stream=io.StringIO())


def test_configure_logging_emits_json_with_extra_fields():
    stream = io.StringIO()
    logger = capstone.configure_logging(stream=stream)

    logger.info(
        "risk_signal_detected",
        extra={"event": "risk_signal_detected", "patient_id": "p1", "risk_signal": "elevated_a1c"},
    )

    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "risk_signal_detected"
    assert payload["patient_id"] == "p1"
    assert payload["risk_signal"] == "elevated_a1c"
    assert payload["level"] == "INFO"


def test_compute_risk_signal_flags_elevated_a1c():
    assert capstone.compute_risk_signal("4548-4", 7.1, "%") == "elevated_a1c"


def test_compute_risk_signal_returns_none_under_threshold():
    assert capstone.compute_risk_signal("4548-4", 5.2, "%") is None


def test_compute_risk_signal_returns_none_for_unknown_code():
    assert capstone.compute_risk_signal("9999-9", 999, "unit") is None


def test_next_version_for_starts_at_one(con):
    assert capstone.next_version_for(con, "p1", "elevated_a1c") == 1


def test_next_version_for_increments_after_append(con):
    capstone.append_risk_signal(
        con,
        {
            "patient_id": "p1",
            "signal": "elevated_a1c",
            "version": 1,
            "loinc_code": "4548-4",
            "value": 7.1,
            "unit": "%",
            "source_resource_id": "obs1",
            "detected_at": "2026-01-01T00:00:00Z",
        },
    )
    assert capstone.next_version_for(con, "p1", "elevated_a1c") == 2


def test_get_risk_timeline_orders_by_version(con):
    for version, value, resource_id in [(1, 7.1, "obs1"), (2, 7.8, "obs2")]:
        capstone.append_risk_signal(
            con,
            {
                "patient_id": "p1",
                "signal": "elevated_a1c",
                "version": version,
                "loinc_code": "4548-4",
                "value": value,
                "unit": "%",
                "source_resource_id": resource_id,
                "detected_at": "2026-01-01T00:00:00Z",
            },
        )
    timeline = capstone.get_risk_timeline(con, "p1")
    assert [row["version"] for row in timeline] == [1, 2]
    assert [row["source_resource_id"] for row in timeline] == ["obs1", "obs2"]


def test_ingest_fhir_observation_appends_audit_row_on_new_signal(con, logger):
    obs = make_observation("obs1", "4548-4", 7.1, "%")
    result = capstone.ingest_fhir_observation(con, obs, logger)

    assert result == {"resource_id": "obs1", "changed": True, "risk_signal": "elevated_a1c", "version": 1}
    timeline = capstone.get_risk_timeline(con, "p1")
    assert len(timeline) == 1
    assert timeline[0]["version"] == 1


def test_ingest_fhir_observation_returns_none_signal_under_threshold(con, logger):
    obs = make_observation("obs1", "4548-4", 5.0, "%")
    result = capstone.ingest_fhir_observation(con, obs, logger)

    assert result == {"resource_id": "obs1", "changed": True, "risk_signal": None, "version": None}
    assert capstone.get_risk_timeline(con, "p1") == []


def test_ingest_fhir_observation_is_idempotent_on_identical_replay(con, logger):
    obs = make_observation("obs1", "4548-4", 7.1, "%")
    capstone.ingest_fhir_observation(con, obs, logger)
    result = capstone.ingest_fhir_observation(con, dict(obs), logger)

    assert result["changed"] is False
    assert len(capstone.get_risk_timeline(con, "p1")) == 1


def test_ingest_fhir_observation_appends_new_version_on_corrected_value(con, logger):
    capstone.ingest_fhir_observation(con, make_observation("obs1", "4548-4", 7.1, "%"), logger)
    result = capstone.ingest_fhir_observation(con, make_observation("obs1", "4548-4", 7.8, "%"), logger)

    assert result["changed"] is True
    assert result["version"] == 2
    timeline = capstone.get_risk_timeline(con, "p1")
    assert [row["version"] for row in timeline] == [1, 2]
