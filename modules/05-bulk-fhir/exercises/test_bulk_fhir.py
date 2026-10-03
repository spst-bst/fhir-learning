"""Tests for bulk_fhir.py.

No running FHIR server needed for this module — these exercises work
directly on raw HTTP response shapes and NDJSON text, plus a local,
in-memory DuckDB connection for the ingest step.
"""

import pathlib
import sys

import duckdb
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bulk_fhir  # noqa: E402


def test_parse_kickoff_response_reads_content_location():
    headers = {"Content-Location": "https://example.org/fhir/bulk/status/abc123"}
    assert bulk_fhir.parse_kickoff_response(headers) == "https://example.org/fhir/bulk/status/abc123"


def test_parse_kickoff_response_raises_without_content_location():
    with pytest.raises(KeyError):
        bulk_fhir.parse_kickoff_response({})


def test_poll_export_status_returns_none_while_running():
    assert bulk_fhir.poll_export_status(202, None) is None


def test_poll_export_status_returns_manifest_when_complete():
    manifest = {"transactionTime": "2026-01-01T00:00:00Z", "output": []}
    assert bulk_fhir.poll_export_status(200, manifest) == manifest


def test_poll_export_status_raises_on_failure():
    with pytest.raises(RuntimeError):
        bulk_fhir.poll_export_status(500, None)


def test_extract_output_urls_filters_by_type():
    manifest = {
        "output": [
            {"type": "Patient", "url": "https://example.org/patient_1.ndjson"},
            {"type": "Observation", "url": "https://example.org/obs_1.ndjson"},
            {"type": "Observation", "url": "https://example.org/obs_2.ndjson"},
        ]
    }
    assert bulk_fhir.extract_output_urls(manifest, "Observation") == [
        "https://example.org/obs_1.ndjson",
        "https://example.org/obs_2.ndjson",
    ]


def test_extract_output_urls_returns_empty_list_when_no_match():
    manifest = {"output": [{"type": "Patient", "url": "https://example.org/patient_1.ndjson"}]}
    assert bulk_fhir.extract_output_urls(manifest, "Condition") == []


def test_parse_ndjson_skips_blank_lines():
    raw = (
        '{"resourceType": "Patient", "id": "p1"}\n'
        '{"resourceType": "Patient", "id": "p2"}\n'
        "\n"
    )
    parsed = bulk_fhir.parse_ndjson(raw)
    assert parsed == [
        {"resourceType": "Patient", "id": "p1"},
        {"resourceType": "Patient", "id": "p2"},
    ]


def test_build_typed_resources_maps_known_types():
    raw = [
        {"resourceType": "Patient", "id": "p1", "name": [{"family": "Doe", "given": ["Jane"]}]},
        {
            "resourceType": "Observation",
            "id": "o1",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4"}]},
        },
    ]
    resources = bulk_fhir.build_typed_resources(raw)
    assert [r.get_resource_type() for r in resources] == ["Patient", "Observation"]
    assert resources[0].id == "p1"
    assert resources[1].id == "o1"


def test_build_typed_resources_raises_on_unknown_type():
    with pytest.raises(ValueError):
        bulk_fhir.build_typed_resources([{"resourceType": "Medication", "id": "m1"}])


def test_ingest_resources_is_idempotent_on_replay():
    con = duckdb.connect(":memory:")
    raw = [{"resourceType": "Patient", "id": "p1", "name": [{"family": "Doe", "given": ["Jane"]}]}]
    resources = bulk_fhir.build_typed_resources(raw)

    first_count = bulk_fhir.ingest_resources(con, resources)
    second_count = bulk_fhir.ingest_resources(con, resources)

    assert first_count == 1
    assert second_count == 1
    rows = con.execute("SELECT resource_type, resource_id FROM bulk_resources").fetchall()
    assert rows == [("Patient", "p1")]


def test_ingest_resources_overwrites_changed_resource():
    con = duckdb.connect(":memory:")
    v1 = bulk_fhir.build_typed_resources(
        [{"resourceType": "Patient", "id": "p1", "name": [{"family": "Doe", "given": ["Jane"]}]}]
    )
    v2 = bulk_fhir.build_typed_resources(
        [{"resourceType": "Patient", "id": "p1", "name": [{"family": "Doe", "given": ["Janet"]}]}]
    )

    bulk_fhir.ingest_resources(con, v1)
    bulk_fhir.ingest_resources(con, v2)

    rows = con.execute("SELECT data_json FROM bulk_resources").fetchall()
    assert len(rows) == 1
    assert "Janet" in rows[0][0]
