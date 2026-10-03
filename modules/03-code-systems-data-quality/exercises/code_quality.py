"""Module 3 exercise: code systems and data quality on raw partner JSON.

No running FHIR server needed here — these work directly on raw dicts, the
layer *below* typed parsing (Module 2 assumed clean, valid FHIR; partner
feeds often aren't).

Run the tests with:
    make test-03
"""

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

# A real version of this would be a proper LOINC reference table lookup;
# here it's just enough to make the exercise concrete.
LOINC_DEFAULT_UNITS = {
    "4548-4": "%",  # Hemoglobin A1c
    "2345-7": "mg/dL",  # Glucose
    "8480-6": "mmHg",  # Systolic blood pressure
    "8462-4": "mmHg",  # Diastolic blood pressure
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
    """Normalize a messy partner-supplied LOINC code to its canonical form.

    Partner feeds send codes inconsistently: surrounding whitespace, or a
    "LOINC:" (or "loinc:") prefix tacked on. Strip both.

    Examples: "  4548-4  " -> "4548-4", "LOINC:4548-4" -> "4548-4".

    Hint: str.strip() handles whitespace. For the prefix, split on ":" and
    check if the part before it, lowercased, is "loinc".

    TODO: implement.
    """
    code = raw_code.strip()
    if ":" in code:
        prefix, _, rest = code.partition(":")
        if prefix.strip().lower() == "loinc":
            code = rest
    code = code.strip()
    _debug_print("normalize_loinc_code", raw_code=raw_code, normalized=code)
    return code


def find_coding(codeable_concept: dict, system: str) -> dict | None:
    """Return the first coding dict in codeable_concept["coding"] whose
    "system" matches the given URI, or None if there isn't one.

    A CodeableConcept can carry multiple codings from different systems at
    once — e.g. a Condition with both a SNOMED CT code (clinical modeling)
    and an ICD-10-CM code (billing). This is how you pick out the one you
    want.

    Hint: codeable_concept.get("coding", []) is a list of dicts, each with
    a "system" key.

    TODO: implement.
    """
    for coding in codeable_concept.get("coding", []):
        if coding.get("system") == system:
            return coding
    return None


def infer_missing_unit(observation: dict) -> dict:
    """Fill in a missing valueQuantity.unit using the LOINC_DEFAULT_UNITS
    table, without mutating the input.

    Behavior:
    - If there's no valueQuantity, or it already has a "unit", return the
      observation unchanged (don't overwrite good data, don't invent units
      for non-numeric results).
    - Otherwise, find the LOINC coding (use find_coding), normalize its
      code (use normalize_loinc_code), and look it up in
      LOINC_DEFAULT_UNITS.
    - If there's no LOINC coding, or the code isn't in the table, raise
      ValueError — a loud failure beats silently guessing a unit on a lab
      value that could feed a risk score.

    Hint: build a new dict (e.g. `observation = dict(observation)` and a
    new valueQuantity dict) rather than mutating the one you were given —
    callers may still hold a reference to the original.

    TODO: implement.
    """
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
    """Drop duplicate Observations, keeping the first occurrence.

    Partner feeds sometimes send the same lab result twice — e.g. once from
    a direct HL7 feed and again from a batch FHIR export — with different
    resource ids but otherwise-identical clinical content. Treat two
    observations as duplicates when they share the same
    (subject reference, normalized LOINC code, effectiveDateTime).

    Hint: track a `set()` of keys you've already seen; build the key with
    find_coding + normalize_loinc_code same as infer_missing_unit does.
    Preserve input order, keeping the first observation for each key.

    TODO: implement.
    """
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
    """Format each coding on a Condition as "{system label}: {code} ({display})".

    A Condition from a partner feed might carry a SNOMED CT code, an
    ICD-10-CM code, or both, in condition["code"]["coding"]. Use
    CODE_SYSTEM_LABELS to turn the system URI into a human label (fall back
    to the raw URI if it's not in the table).

    TODO: implement. Return one string per coding, same order as input.
    """
    descriptions = []
    for coding in condition.get("code", {}).get("coding", []):
        system = coding.get("system")
        label = CODE_SYSTEM_LABELS.get(system, system)
        descriptions.append(f"{label}: {coding.get('code')} ({coding.get('display')})")
    return descriptions
