"""Tests for hl7_mapping.py.

No running FHIR server needed — these work directly on raw HL7 v2 message
text, fed in with \\n for readability (real messages use \\r; parse_message
has to normalize that).
"""

import pathlib
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import hl7_mapping  # noqa: E402

PATIENT_ID = "2b25e76e-99af-e31a-55ec-62f57d9ddc2f"

ORU_MESSAGE = (
    "MSH|^~\\&|LAB|HOSP|EHR|HOSP|20260410195314||ORU^R01|MSG00001|P|2.3\n"
    f"PID|1||{PATIENT_ID}^^^HOSP^MR||Doe^Jane||19800101|F\n"
    "OBR|1|||4548-4^Hemoglobin A1c^LN\n"
    "OBX|1|NM|4548-4^Hemoglobin A1c^LN||5.43|%|||||F|||20260410195314\n"
)

ADT_MESSAGE = (
    "MSH|^~\\&|REG|HOSP|EHR|HOSP|20260410080000||ADT^A01|MSG00002|P|2.3\n"
    "EVN|A01|20260410080000\n"
    f"PID|1||{PATIENT_ID}^^^HOSP^MR||Doe^Jane||19800101|F\n"
    "PV1|1|I|ICU^101^1\n"
)


def test_parse_message_normalizes_newlines():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    assert str(message.segment("MSH")[9]) == "ORU^R01"


def test_message_type_reads_msh_9():
    oru = hl7_mapping.parse_message(ORU_MESSAGE)
    adt = hl7_mapping.parse_message(ADT_MESSAGE)
    assert hl7_mapping.message_type(oru) == "ORU^R01"
    assert hl7_mapping.message_type(adt) == "ADT^A01"


def test_patient_id_reads_pid_3():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    assert hl7_mapping.patient_id(message) == PATIENT_ID


def test_patient_display_name_reads_pid_5():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    assert hl7_mapping.patient_display_name(message) == "Jane Doe"


def test_extract_observations_reads_obx_segments():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    observations = hl7_mapping.extract_observations(message)
    assert len(observations) == 1
    obs = observations[0]
    assert obs["loinc_code"] == "4548-4"
    assert obs["display"] == "Hemoglobin A1c"
    assert obs["value"] == "5.43"
    assert obs["unit"] == "%"
    assert obs["status"] == "F"
    assert obs["observed_at"] == datetime(2026, 4, 10, 19, 53, 14, tzinfo=timezone.utc)


def test_extract_observations_returns_empty_list_for_adt():
    message = hl7_mapping.parse_message(ADT_MESSAGE)
    assert hl7_mapping.extract_observations(message) == []


def test_observation_id_for_is_deterministic():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    pid = hl7_mapping.patient_id(message)
    obs = hl7_mapping.extract_observations(message)[0]
    # Simulate the same result being redelivered in a second, separate message.
    first_id = hl7_mapping.observation_id_for(pid, obs)
    second_id = hl7_mapping.observation_id_for(pid, dict(obs))
    assert first_id == second_id


def test_build_fhir_observation_maps_fields():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    pid = hl7_mapping.patient_id(message)
    obs = hl7_mapping.extract_observations(message)[0]
    fhir_obs = hl7_mapping.build_fhir_observation(pid, obs)
    assert fhir_obs.id == hl7_mapping.observation_id_for(pid, obs)
    assert fhir_obs.status == "final"
    assert fhir_obs.subject.reference == f"Patient/{pid}"
    assert fhir_obs.code.coding[0].system == hl7_mapping.LOINC_SYSTEM
    assert fhir_obs.code.coding[0].code == "4548-4"
    assert float(fhir_obs.valueQuantity.value) == pytest.approx(5.43)
    assert fhir_obs.valueQuantity.unit == "%"
    assert fhir_obs.effectiveDateTime == datetime(2026, 4, 10, 19, 53, 14, tzinfo=timezone.utc)


def test_build_fhir_observation_raises_on_unmapped_status():
    message = hl7_mapping.parse_message(ORU_MESSAGE)
    pid = hl7_mapping.patient_id(message)
    obs = hl7_mapping.extract_observations(message)[0]
    obs["status"] = "X"  # "results cannot be obtained" — not in our mapping
    with pytest.raises(ValueError):
        hl7_mapping.build_fhir_observation(pid, obs)
