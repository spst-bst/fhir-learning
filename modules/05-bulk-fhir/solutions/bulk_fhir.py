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


def parse_kickoff_response(headers: dict) -> str:
    return headers["Content-Location"]


def poll_export_status(status_code: int, body: dict | None) -> dict | None:
    if status_code == 202:
        return None
    if status_code == 200:
        return body
    raise RuntimeError(f"export job failed with status {status_code}")


def extract_output_urls(manifest: dict, resource_type: str) -> list[str]:
    return [entry["url"] for entry in manifest.get("output", []) if entry["type"] == resource_type]


def parse_ndjson(raw_text: str) -> list[dict]:
    return [json.loads(line) for line in raw_text.split("\n") if line.strip()]


def build_typed_resources(raw_resources: list[dict]) -> list[Patient | Observation | Condition]:
    resources = []
    for raw in raw_resources:
        resource_type = raw["resourceType"]
        model = RESOURCE_MODELS.get(resource_type)
        if model is None:
            raise ValueError(f"unsupported resourceType: {resource_type!r}")
        resources.append(model.model_validate(raw))
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
    return len(resources)
