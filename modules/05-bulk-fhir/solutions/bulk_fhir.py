"""Reference solution for Module 5. Don't peek until you've had a real go."""

from __future__ import annotations

import json

import duckdb
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient

RESOURCE_MODELS = {
    "Patient": Patient,
    "Observation": Observation,
    "Condition": Condition,
}

# Set to False to quiet the debug dump below.
DEBUG = True


def _debug_print(label: str, **values) -> None:
    if not DEBUG:
        return
    print(f"\n--- {label} ---")
    for name, value in values.items():
        print(f"{name}: {json.dumps(value, default=str)}")


def parse_kickoff_response(headers: dict) -> str:
    poll_url = headers["Content-Location"]
    _debug_print("parse_kickoff_response", headers=headers, poll_url=poll_url)
    return poll_url


def poll_export_status(status_code: int, body: dict | None) -> dict | None:
    if status_code == 202:
        _debug_print("poll_export_status", status_code=status_code, result="still running")
        return None
    if status_code == 200:
        _debug_print("poll_export_status", status_code=status_code, result="complete", manifest=body)
        return body
    raise RuntimeError(f"export job failed with status {status_code}")


def extract_output_urls(manifest: dict, resource_type: str) -> list[str]:
    urls = [entry["url"] for entry in manifest.get("output", []) if entry["type"] == resource_type]
    _debug_print("extract_output_urls", resource_type=resource_type, urls=urls)
    return urls


def parse_ndjson(raw_text: str) -> list[dict]:
    parsed = [json.loads(line) for line in raw_text.split("\n") if line.strip()]
    _debug_print("parse_ndjson", line_count=len(parsed))
    return parsed


def build_typed_resources(raw_resources: list[dict]) -> list[Patient | Observation | Condition]:
    resources = []
    for raw in raw_resources:
        resource_type = raw["resourceType"]
        model = RESOURCE_MODELS.get(resource_type)
        if model is None:
            raise ValueError(f"unsupported resourceType: {resource_type!r}")
        resources.append(model.model_validate(raw))
    _debug_print(
        "build_typed_resources",
        resource_types=[r.get_resource_type() for r in resources],
        resource_ids=[r.id for r in resources],
    )
    return resources


def ingest_resources(con: duckdb.DuckDBPyConnection, resources: list) -> int:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS bulk_resources (
            resource_type VARCHAR,
            resource_id VARCHAR,
            data_json VARCHAR
        )
        """
    )
    for resource in resources:
        resource_type = resource.get_resource_type()
        con.execute(
            "DELETE FROM bulk_resources WHERE resource_type = ? AND resource_id = ?",
            [resource_type, resource.id],
        )
        con.execute(
            "INSERT INTO bulk_resources VALUES (?, ?, ?)",
            [resource_type, resource.id, resource.model_dump_json()],
        )
    _debug_print(
        "ingest_resources",
        ingested=[(r.get_resource_type(), r.id) for r in resources],
        count=len(resources),
    )
    return len(resources)
