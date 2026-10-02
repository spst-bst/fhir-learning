"""Module 1 exercise: your first FHIR REST client calls, using httpx.

Fill in each TODO. Every function talks to a running HAPI FHIR server over
plain HTTP — no FHIR-specific library needed yet, just GET/POST and JSON.

Run the tests with:
    make test-01
"""

from __future__ import annotations

import httpx

DEFAULT_BASE_URL = "http://localhost:8080/fhir"


def get_capability_statement(base_url: str = DEFAULT_BASE_URL) -> dict:
    """Fetch the server's CapabilityStatement (what the server supports).

    FHIR servers publish this at GET {base_url}/metadata. It tells you the
    FHIR version, which resource types are supported, and which search
    parameters work on each — the first thing you check against any new
    FHIR server (your own, or a partner's).

    TODO: GET {base_url}/metadata and return the parsed JSON body.
    """
    resp = httpx.get(f"{base_url}/metadata")
    resp.raise_for_status()
    return resp.json()


def count_resources(resource_type: str, base_url: str = DEFAULT_BASE_URL) -> int:
    """Return how many resources of this type exist on the server.

    Hint: the search endpoint GET {base_url}/{resource_type}?_summary=count
    returns a Bundle whose "total" field is the count, without fetching
    every matching resource.

    TODO: implement and return the integer total.
    """
    resp = httpx.get(f"{base_url}/{resource_type}", params={"_summary": "count"})
    resp.raise_for_status()
    return resp.json()["total"]


def get_patient_by_id(patient_id: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    """Fetch a single Patient resource by its id.

    Hint: GET {base_url}/Patient/{patient_id}.

    TODO: implement and return the parsed Patient resource (a dict).
    """
    resp = httpx.get(f"{base_url}/Patient/{patient_id}")
    resp.raise_for_status()
    return resp.json()


def search_patients_by_family_name(
    family_name: str, base_url: str = DEFAULT_BASE_URL
) -> list[dict]:
    """Search for Patients by family (last) name.

    Hint: GET {base_url}/Patient?family={family_name} returns a Bundle. The
    matching resources live at bundle["entry"][i]["resource"]. A Bundle with
    no matches may have no "entry" key at all — don't assume it's there.

    TODO: implement and return a list of Patient resources (dicts). Return
    an empty list if there are no matches.
    """
    resp = httpx.get(f"{base_url}/Patient", params={"family": family_name})
    resp.raise_for_status()
    bundle = resp.json()
    return [entry["resource"] for entry in bundle.get("entry", [])]


def get_conditions_for_patient(
    patient_id: str, base_url: str = DEFAULT_BASE_URL
) -> list[dict]:
    """Search for all Condition resources referencing this patient.

    Hint: GET {base_url}/Condition?patient={patient_id}. This is a reference
    search parameter — most clinical resources support `?patient=` or
    `?subject=` to scope results to one patient, which is how you'd pull a
    patient's full chart in a real integration.

    TODO: implement and return a list of Condition resources (dicts).
    """
    resp = httpx.get(f"{base_url}/Condition", params={"patient": patient_id})
    resp.raise_for_status()
    bundle = resp.json()
    return [entry["resource"] for entry in bundle.get("entry", [])]
