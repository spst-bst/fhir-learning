"""Module 7 capstone: lab ingestion with a versioned, auditable risk-signal
timeline.

Ties together Module 4/5's idempotent-ingest lesson with its deliberate
opposite: a risk signal, once detected, is never overwritten — a
corrected value gets a new version, not a replaced one.

Run the tests with:
    make test-07
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import duckdb

# code -> (threshold, signal name). Value at or above the threshold fires
# the signal. A real version of this would be a proper clinical reference
# table; this is just enough to make the exercise concrete.
RISK_THRESHOLDS = {
    "4548-4": (6.5, "elevated_a1c"),  # Hemoglobin A1c, %
    "2345-7": (126, "elevated_glucose"),  # Glucose, mg/dL
    "8480-6": (140, "elevated_systolic_bp"),  # Systolic BP, mmHg
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
    """Renders each log record as one JSON object, including any `extra`
    fields the caller passed — the structured-logging counterpart to the
    free-text logs you'd otherwise grep."""

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
    """Return a "capstone" logger that emits JSON lines via JsonFormatter.

    Pass `stream` (e.g. an io.StringIO in tests) to capture output instead
    of writing to stderr. Clear any existing handlers first so repeated
    calls (e.g. once per test) don't stack duplicate handlers on the same
    named logger — logging.getLogger() returns the same object every time
    it's called with the same name.

    Hint: logging.StreamHandler(stream) if stream is not None else
    logging.StreamHandler(). Set the formatter, level=INFO, and
    propagate=False (so records don't also hit pytest's root logger
    config and print twice).

    TODO: implement.
    """
    logger = logging.getLogger("capstone")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream) if stream is not None else logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def compute_risk_signal(loinc_code: str, value: float, unit: str) -> str | None:
    """Check a lab value against RISK_THRESHOLDS.

    Return the signal name if loinc_code is in RISK_THRESHOLDS and value
    is at or above its threshold. Return None if the code isn't in the
    table, or the value is below threshold.

    TODO: implement.
    """
    threshold_and_signal = RISK_THRESHOLDS.get(loinc_code)
    if threshold_and_signal is None:
        return None
    threshold, signal = threshold_and_signal
    result = signal if value >= threshold else None
    _debug_print("compute_risk_signal", loinc_code=loinc_code, value=value, result=result)
    return result


def next_version_for(con: duckdb.DuckDBPyConnection, patient_id: str, signal: str) -> int:
    """Return the next version number for this (patient_id, signal) pair
    in the risk_signal_history table.

    1 if no rows exist yet for this pair, otherwise one more than the
    current max version. This is what makes the audit trail an ordered
    sequence rather than an unordered pile of rows.

    Hint: con.execute("SELECT MAX(version) FROM risk_signal_history WHERE
    patient_id = ? AND signal = ?", [...]).fetchone() returns a one-tuple;
    its value is None if there are no matching rows (not 0). This
    function gets called directly in tests before any row exists yet, so
    it needs its own CREATE TABLE IF NOT EXISTS guard too (same DDL as
    append_risk_signal below) — don't assume the table's already there.

    TODO: implement.
    """
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
    """Append one row to risk_signal_history. Never update or delete here
    — that's the whole point of an audit trail.

    Create the table if it doesn't exist:
        risk_signal_history(
            patient_id VARCHAR, signal VARCHAR, version INTEGER,
            loinc_code VARCHAR, value DOUBLE, unit VARCHAR,
            source_resource_id VARCHAR, detected_at VARCHAR
        )

    `record` has exactly those keys. Insert it as one row.

    TODO: implement.
    """
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
    """Return every version of every signal for one patient, oldest
    first within each signal — the full audit history, not just the
    latest state.

    Hint: con.execute(...).fetchall() gives tuples; con.execute(...)
    .description gives you the column names in order if you want to
    zip them into dicts. Order by signal, then version. Same
    CREATE TABLE IF NOT EXISTS guard as next_version_for — this can also
    get called before any row (or even the table) exists.

    TODO: implement.
    """
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
    """Ingest one FHIR Observation: idempotent upsert of the raw resource,
    plus an append-only audit row if it crosses a risk threshold — but
    only when the content is actually new or changed.

    Steps:
    1. Pull resource_id = raw_observation["id"], loinc_code from
       raw_observation["code"]["coding"][0]["code"], value and unit from
       raw_observation["valueQuantity"].
    2. Create table bulk_resources(resource_type VARCHAR, resource_id
       VARCHAR, data_json VARCHAR) if it doesn't exist.
    3. Look up any existing row for this resource_id. Serialize the
       incoming observation with json.dumps(raw_observation,
       sort_keys=True) and compare — `is_new_or_changed` is True if there
       was no existing row, or its data_json differs from the new one.
    4. Upsert (delete-then-insert, same as Module 5) into bulk_resources
       regardless of whether it changed — the raw table always reflects
       the latest write.
    5. Call compute_risk_signal(loinc_code, value, unit).
    6. If is_new_or_changed and a signal fired: get patient_id from
       raw_observation["subject"]["reference"].split("/")[-1], get
       next_version_for(...), build the record dict (see
       append_risk_signal's docstring for the shape;
       detected_at = datetime.now(timezone.utc).isoformat()), and
       append_risk_signal(...). Log with
       logger.info("risk_signal_detected", extra={"event":
       "risk_signal_detected", "patient_id": ..., "resource_id": ...,
       "risk_signal": signal, "version": version}).
    7. Otherwise (no signal, or a no-op replay) log with
       logger.info("observation_ingested", extra={"event":
       "observation_ingested", "resource_id": ..., "changed":
       is_new_or_changed}).
    8. Return {"resource_id": ..., "changed": is_new_or_changed,
       "risk_signal": signal, "version": version_or_None}.

    TODO: implement.
    """
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
