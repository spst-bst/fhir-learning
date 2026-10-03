"""Reference solution for Module 7. Don't peek until you've had a real go."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import duckdb

RISK_THRESHOLDS = {
    "4548-4": (6.5, "elevated_a1c"),
    "2345-7": (126, "elevated_glucose"),
    "8480-6": (140, "elevated_systolic_bp"),
}

# Set to False to quiet the debug dump below.
DEBUG = True


def _debug_print(label: str, **values) -> None:
    if not DEBUG:
        return
    print(f"\n--- {label} ---")
    for name, value in values.items():
        print(f"{name}: {json.dumps(value, default=str)}")


class JsonFormatter(logging.Formatter):
    EXTRA_FIELDS = ("event", "patient_id", "resource_id", "risk_signal", "version", "changed")

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for field in self.EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload)


def configure_logging(stream=None) -> logging.Logger:
    logger = logging.getLogger("capstone")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream) if stream is not None else logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def compute_risk_signal(loinc_code: str, value: float, unit: str) -> str | None:
    threshold_and_signal = RISK_THRESHOLDS.get(loinc_code)
    if threshold_and_signal is None:
        return None
    threshold, signal = threshold_and_signal
    result = signal if value >= threshold else None
    _debug_print("compute_risk_signal", loinc_code=loinc_code, value=value, result=result)
    return result


def next_version_for(con: duckdb.DuckDBPyConnection, patient_id: str, signal: str) -> int:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_signal_history (
            patient_id VARCHAR, signal VARCHAR, version INTEGER,
            loinc_code VARCHAR, value DOUBLE, unit VARCHAR,
            source_resource_id VARCHAR, detected_at VARCHAR
        )
        """
    )
    row = con.execute(
        "SELECT MAX(version) FROM risk_signal_history WHERE patient_id = ? AND signal = ?",
        [patient_id, signal],
    ).fetchone()
    current_max = row[0]
    next_version = 1 if current_max is None else current_max + 1
    _debug_print("next_version_for", patient_id=patient_id, signal=signal, next_version=next_version)
    return next_version


def append_risk_signal(con: duckdb.DuckDBPyConnection, record: dict) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_signal_history (
            patient_id VARCHAR, signal VARCHAR, version INTEGER,
            loinc_code VARCHAR, value DOUBLE, unit VARCHAR,
            source_resource_id VARCHAR, detected_at VARCHAR
        )
        """
    )
    con.execute(
        """
        INSERT INTO risk_signal_history
        (patient_id, signal, version, loinc_code, value, unit, source_resource_id, detected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["patient_id"],
            record["signal"],
            record["version"],
            record["loinc_code"],
            record["value"],
            record["unit"],
            record["source_resource_id"],
            record["detected_at"],
        ],
    )
    _debug_print("append_risk_signal", record=record)


def get_risk_timeline(con: duckdb.DuckDBPyConnection, patient_id: str) -> list[dict]:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_signal_history (
            patient_id VARCHAR, signal VARCHAR, version INTEGER,
            loinc_code VARCHAR, value DOUBLE, unit VARCHAR,
            source_resource_id VARCHAR, detected_at VARCHAR
        )
        """
    )
    result = con.execute(
        """
        SELECT patient_id, signal, version, loinc_code, value, unit, source_resource_id, detected_at
        FROM risk_signal_history
        WHERE patient_id = ?
        ORDER BY signal, version
        """,
        [patient_id],
    )
    columns = [col[0] for col in result.description]
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    _debug_print("get_risk_timeline", patient_id=patient_id, row_count=len(rows))
    return rows


def ingest_fhir_observation(
    con: duckdb.DuckDBPyConnection, raw_observation: dict, logger: logging.Logger
) -> dict:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS bulk_resources (
            resource_type VARCHAR, resource_id VARCHAR, data_json VARCHAR
        )
        """
    )

    resource_id = raw_observation["id"]
    loinc_code = raw_observation["code"]["coding"][0]["code"]
    value_quantity = raw_observation["valueQuantity"]
    value = value_quantity["value"]
    unit = value_quantity.get("unit")

    previous = con.execute(
        "SELECT data_json FROM bulk_resources WHERE resource_type = 'Observation' AND resource_id = ?",
        [resource_id],
    ).fetchone()
    new_data_json = json.dumps(raw_observation, sort_keys=True)
    is_new_or_changed = previous is None or previous[0] != new_data_json

    con.execute(
        "DELETE FROM bulk_resources WHERE resource_type = 'Observation' AND resource_id = ?",
        [resource_id],
    )
    con.execute(
        "INSERT INTO bulk_resources VALUES ('Observation', ?, ?)",
        [resource_id, new_data_json],
    )

    signal = compute_risk_signal(loinc_code, value, unit)
    version = None

    if is_new_or_changed and signal is not None:
        patient_id = raw_observation["subject"]["reference"].split("/")[-1]
        version = next_version_for(con, patient_id, signal)
        append_risk_signal(
            con,
            {
                "patient_id": patient_id,
                "signal": signal,
                "version": version,
                "loinc_code": loinc_code,
                "value": value,
                "unit": unit,
                "source_resource_id": resource_id,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info(
            "risk_signal_detected",
            extra={
                "event": "risk_signal_detected",
                "patient_id": patient_id,
                "resource_id": resource_id,
                "risk_signal": signal,
                "version": version,
            },
        )
    else:
        logger.info(
            "observation_ingested",
            extra={
                "event": "observation_ingested",
                "resource_id": resource_id,
                "changed": is_new_or_changed,
            },
        )

    result = {
        "resource_id": resource_id,
        "changed": is_new_or_changed,
        "risk_signal": signal,
        "version": version,
    }
    _debug_print("ingest_fhir_observation", result=result)
    return result
