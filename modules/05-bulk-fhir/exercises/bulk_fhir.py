"""Module 5 exercise: Bulk FHIR $export flow and idempotent NDJSON ingest.

Works directly on the request/response shapes (headers, status codes,
manifest JSON, NDJSON text) rather than a live async job — the local HAPI
server doesn't implement $export, and a real one takes minutes to finish
by design.

Run the tests with:
    make test-05
"""

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
    """Return the poll URL from a $export kickoff response's headers.

    The kickoff response (202 Accepted, empty body) carries the status URL
    in the "Content-Location" header. Raise KeyError if it's missing —
    a kickoff response without it means the server didn't actually accept
    an async job, which should fail loudly rather than return None.

    TODO: implement.
    """
    poll_url = headers["Content-Location"]
    _debug_print("parse_kickoff_response", headers=headers, poll_url=poll_url)
    return poll_url


def poll_export_status(status_code: int, body: dict | None) -> dict | None:
    """Interpret one poll response against the export status URL.

    - 202: job still running. Return None regardless of body.
    - 200: job complete. `body` is the completion manifest — return it
      as-is.
    - anything else: the job failed. Raise RuntimeError with a message
      that includes the status code.

    TODO: implement.
    """
    if status_code == 202:
        _debug_print("poll_export_status", status_code=status_code, result="still running")
        return None
    if status_code == 200:
        _debug_print("poll_export_status", status_code=status_code, result="complete", manifest=body)
        return body
    raise RuntimeError(f"export job failed with status {status_code}")


def extract_output_urls(manifest: dict, resource_type: str) -> list[str]:
    """Pull the download URLs for one resource type out of a manifest.

    The manifest's "output" key is a list of
    {"type": "Observation", "url": "..."} entries — a real export can
    split one resource type across multiple files, so there may be more
    than one entry per type. Return the urls for entries matching
    resource_type, in order. Empty list if none match.

    TODO: implement.
    """
    urls = [entry["url"] for entry in manifest.get("output", []) if entry["type"] == resource_type]
    _debug_print("extract_output_urls", resource_type=resource_type, urls=urls)
    return urls


def parse_ndjson(raw_text: str) -> list[dict]:
    """Parse NDJSON text (one JSON object per line) into a list of dicts.

    Skip blank lines (a trailing newline at end-of-file is common and
    shouldn't produce an empty entry).

    TODO: implement.
    """
    parsed = [json.loads(line) for line in raw_text.split("\n") if line.strip()]
    _debug_print("parse_ndjson", line_count=len(parsed))
    return parsed


def build_typed_resources(raw_resources: list[dict]) -> list[Patient | Observation | Condition]:
    """Parse a list of raw resource dicts into typed FHIR models.

    Each dict has a "resourceType" key ("Patient", "Observation", or
    "Condition" in this course's fixtures). Look the type up in
    RESOURCE_MODELS and call .model_validate(raw) on the matching class.
    Raise ValueError for a resourceType not in RESOURCE_MODELS.

    TODO: implement.
    """
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
    """Upsert typed resources into a local DuckDB table, keyed by
    (resource_type, resource_id).

    Create the table if it doesn't exist:
        bulk_resources(resource_type VARCHAR, resource_id VARCHAR,
                        data_json VARCHAR)

    For idempotency — re-ingesting the same export must not duplicate
    rows, and a changed resource must overwrite the old row — delete any
    existing row with the same (resource_type, resource_id) before
    inserting the new one. Use resource.get_resource_type() for the type
    and resource.id for the id; resource.model_dump_json() for the JSON
    to store.

    Return the number of resources ingested.

    Hint: con.execute(sql, params) runs one parameterized statement.
    You'll call it three times per resource (create-table-if-not-exists
    can run once up front, then delete + insert per resource).

    TODO: implement.
    """
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
