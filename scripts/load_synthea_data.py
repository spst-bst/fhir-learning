"""Loads the committed Synthea sample data into the local HAPI FHIR server.

Idempotent: safe to run more than once. Reference data (Organizations and
Practitioners) uses conditional-update bundles, so re-posting is a no-op.
Patient bundles are skipped if that patient id already exists on the server.

Usage:
    uv run python scripts/load_synthea_data.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

BASE_URL = "http://localhost:8080/fhir"
DATA_DIR = pathlib.Path(__file__).parent.parent / "data" / "synthea" / "fhir"
REFERENCE_FILE = "00-reference-organizations-practitioners.json"


def post_bundle(client: httpx.Client, bundle: dict, label: str) -> None:
    resp = client.post("", json=bundle)
    if resp.status_code >= 400:
        print(f"  FAILED ({resp.status_code}): {label}")
        print(resp.text[:1000])
        resp.raise_for_status()
    print(f"  loaded: {label} ({len(bundle.get('entry', []))} resources)")


def patient_id_in_bundle(bundle: dict) -> str | None:
    for entry in bundle.get("entry", []):
        if entry["resource"]["resourceType"] == "Patient":
            return entry["resource"]["id"]
    return None


def main() -> int:
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        try:
            client.get("/metadata").raise_for_status()
        except httpx.HTTPError as exc:
            print(f"Cannot reach HAPI FHIR at {BASE_URL}: {exc}")
            print("Run 'make up' (or scripts/start_stack.sh) first.")
            return 1

        print("Loading reference data (Organizations, Practitioners)...")
        ref_bundle = json.loads((DATA_DIR / REFERENCE_FILE).read_text())
        post_bundle(client, ref_bundle, REFERENCE_FILE)

        print("Loading Synthea patients...")
        patient_files = sorted(DATA_DIR.glob("patient-*.json"))
        for path in patient_files:
            bundle = json.loads(path.read_text())
            patient_id = patient_id_in_bundle(bundle)
            existing = client.get(f"/Patient/{patient_id}")
            if existing.status_code == 200:
                print(f"  skipped (already loaded): {path.name}")
                continue
            post_bundle(client, bundle, path.name)

        total = client.get("/Patient?_summary=count").json().get("total")
        print(f"\nDone. HAPI FHIR now has {total} Patient resource(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
