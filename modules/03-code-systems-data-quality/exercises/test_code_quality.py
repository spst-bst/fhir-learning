"""Tests for code_quality.py.

No running FHIR server needed for this module — these exercises work
directly on raw (dict) partner data, the layer below typed parsing.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import code_quality  # noqa: E402


def test_normalize_loinc_code_strips_whitespace():
    assert code_quality.normalize_loinc_code("  4548-4  ") == "4548-4"


def test_normalize_loinc_code_strips_system_prefix():
    assert code_quality.normalize_loinc_code("LOINC:4548-4") == "4548-4"
    assert code_quality.normalize_loinc_code("loinc:4548-4") == "4548-4"


def test_find_coding_returns_matching_system():
    concept = {
        "coding": [
            {"system": code_quality.SNOMED_SYSTEM, "code": "254837009"},
            {"system": code_quality.ICD10_SYSTEM, "code": "C50.911"},
        ]
    }
    coding = code_quality.find_coding(concept, code_quality.ICD10_SYSTEM)
    assert coding is not None
    assert coding["code"] == "C50.911"


def test_find_coding_returns_none_when_system_absent():
    concept = {"coding": [{"system": code_quality.SNOMED_SYSTEM, "code": "254837009"}]}
    assert code_quality.find_coding(concept, code_quality.RXNORM_SYSTEM) is None


def test_infer_missing_unit_fills_in_known_loinc_code():
    observation = {
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": " LOINC:4548-4"}]},
        "valueQuantity": {"value": 5.43},
    }
    result = code_quality.infer_missing_unit(observation)
    assert result["valueQuantity"]["unit"] == "%"
    assert result["valueQuantity"]["value"] == 5.43


def test_infer_missing_unit_does_not_mutate_input():
    observation = {
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": "4548-4"}]},
        "valueQuantity": {"value": 5.43},
    }
    code_quality.infer_missing_unit(observation)
    assert "unit" not in observation["valueQuantity"]


def test_infer_missing_unit_leaves_existing_unit_alone():
    observation = {
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": "4548-4"}]},
        "valueQuantity": {"value": 5.43, "unit": "percent"},
    }
    result = code_quality.infer_missing_unit(observation)
    assert result["valueQuantity"]["unit"] == "percent"


def test_infer_missing_unit_raises_on_unknown_code():
    observation = {
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": "99999-9"}]},
        "valueQuantity": {"value": 1.0},
    }
    try:
        code_quality.infer_missing_unit(observation)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_deduplicate_observations_drops_repeats_from_second_feed():
    obs_a = {
        "id": "feed-a-1",
        "subject": {"reference": "Patient/123"},
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": "4548-4"}]},
        "effectiveDateTime": "2026-04-10T19:53:14+00:00",
    }
    obs_b_dup = {
        "id": "feed-b-99",
        "subject": {"reference": "Patient/123"},
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": "LOINC:4548-4"}]},
        "effectiveDateTime": "2026-04-10T19:53:14+00:00",
    }
    obs_c_distinct = {
        "id": "feed-a-2",
        "subject": {"reference": "Patient/123"},
        "code": {"coding": [{"system": code_quality.LOINC_SYSTEM, "code": "2345-7"}]},
        "effectiveDateTime": "2026-04-10T19:53:14+00:00",
    }
    deduped = code_quality.deduplicate_observations([obs_a, obs_b_dup, obs_c_distinct])
    assert [o["id"] for o in deduped] == ["feed-a-1", "feed-a-2"]


def test_describe_condition_codings_labels_multiple_systems():
    condition = {
        "code": {
            "coding": [
                {
                    "system": code_quality.SNOMED_SYSTEM,
                    "code": "254837009",
                    "display": "Malignant neoplasm of breast",
                },
                {
                    "system": code_quality.ICD10_SYSTEM,
                    "code": "C50.911",
                    "display": "Malignant neoplasm of breast, unspecified",
                },
            ]
        }
    }
    descriptions = code_quality.describe_condition_codings(condition)
    assert descriptions == [
        "SNOMED CT: 254837009 (Malignant neoplasm of breast)",
        "ICD-10-CM: C50.911 (Malignant neoplasm of breast, unspecified)",
    ]
