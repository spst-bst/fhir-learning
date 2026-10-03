"""Reference solution for Module 3. Don't peek until you've had a real go."""

from __future__ import annotations

import json

LOINC_SYSTEM = "http://loinc.org"
SNOMED_SYSTEM = "http://snomed.info/sct"
ICD10_SYSTEM = "http://hl7.org/fhir/sid/icd-10-cm"
RXNORM_SYSTEM = "http://www.nlm.nih.gov/research/umls/rxnorm"

CODE_SYSTEM_LABELS = {
    LOINC_SYSTEM: "LOINC",
    SNOMED_SYSTEM: "SNOMED CT",
    ICD10_SYSTEM: "ICD-10-CM",
    RXNORM_SYSTEM: "RxNorm",
}

LOINC_DEFAULT_UNITS = {
    "4548-4": "%",
    "2345-7": "mg/dL",
    "8480-6": "mmHg",
    "8462-4": "mmHg",
}

# Set to False to quiet the debug dump below.
DEBUG = True


def _debug_print(label: str, **values) -> None:
    if not DEBUG:
        return
    print(f"\n--- {label} ---")
    for name, value in values.items():
        print(f"{name}: {json.dumps(value, default=str)}")


def normalize_loinc_code(raw_code: str) -> str:
    code = raw_code.strip()
    if ":" in code:
        prefix, _, rest = code.partition(":")
        if prefix.strip().lower() == "loinc":
            code = rest
    code = code.strip()
    _debug_print("normalize_loinc_code", raw_code=raw_code, normalized=code)
    return code


def find_coding(codeable_concept: dict, system: str) -> dict | None:
    for coding in codeable_concept.get("coding", []):
        if coding.get("system") == system:
            return coding
    return None


def infer_missing_unit(observation: dict) -> dict:
    observation = dict(observation)
    value_quantity = observation.get("valueQuantity")
    if value_quantity is None or "unit" in value_quantity:
        return observation

    loinc_coding = find_coding(observation.get("code", {}), LOINC_SYSTEM)
    if loinc_coding is None:
        raise ValueError("observation has no LOINC code to infer a unit from")

    code = normalize_loinc_code(loinc_coding.get("code", ""))
    if code not in LOINC_DEFAULT_UNITS:
        raise ValueError(f"no default unit known for LOINC code {code!r}")

    observation["valueQuantity"] = {**value_quantity, "unit": LOINC_DEFAULT_UNITS[code]}
    _debug_print(
        "infer_missing_unit",
        before=value_quantity,
        after=observation["valueQuantity"],
    )
    return observation


def deduplicate_observations(observations: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for obs in observations:
        loinc_coding = find_coding(obs.get("code", {}), LOINC_SYSTEM)
        code = normalize_loinc_code(loinc_coding["code"]) if loinc_coding else None
        key = (
            obs.get("subject", {}).get("reference"),
            code,
            obs.get("effectiveDateTime"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(obs)
    _debug_print(
        "deduplicate_observations",
        input_ids=[o.get("id") for o in observations],
        kept_ids=[o.get("id") for o in deduped],
    )
    return deduped


def describe_condition_codings(condition: dict) -> list[str]:
    descriptions = []
    for coding in condition.get("code", {}).get("coding", []):
        system = coding.get("system")
        label = CODE_SYSTEM_LABELS.get(system, system)
        descriptions.append(f"{label}: {coding.get('code')} ({coding.get('display')})")
    return descriptions
