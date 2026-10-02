"""Reference solution for Module 1. Don't peek until you've had a real go."""

from __future__ import annotations

import httpx

DEFAULT_BASE_URL = "http://localhost:8080/fhir"


def get_capability_statement(base_url: str = DEFAULT_BASE_URL) -> dict:
    resp = httpx.get(f"{base_url}/metadata")
    resp.raise_for_status()
    return resp.json()


def count_resources(resource_type: str, base_url: str = DEFAULT_BASE_URL) -> int:
    resp = httpx.get(f"{base_url}/{resource_type}", params={"_summary": "count"})
    resp.raise_for_status()
    return resp.json()["total"]


def get_patient_by_id(patient_id: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    resp = httpx.get(f"{base_url}/Patient/{patient_id}")
    resp.raise_for_status()
    return resp.json()


def search_patients_by_family_name(
    family_name: str, base_url: str = DEFAULT_BASE_URL
) -> list[dict]:
    resp = httpx.get(f"{base_url}/Patient", params={"family": family_name})
    resp.raise_for_status()
    bundle = resp.json()
    return [entry["resource"] for entry in bundle.get("entry", [])]


def get_conditions_for_patient(
    patient_id: str, base_url: str = DEFAULT_BASE_URL
) -> list[dict]:
    resp = httpx.get(f"{base_url}/Condition", params={"patient": patient_id})
    resp.raise_for_status()
    bundle = resp.json()
    return [entry["resource"] for entry in bundle.get("entry", [])]
