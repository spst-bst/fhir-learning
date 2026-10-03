"""Module 7 capstone: FastAPI wiring for capstone.py's pipeline.

Intentionally thin — the pipeline logic lives in capstone.py; this file
just exposes it over HTTP. If this is your first FastAPI route, that's
by design: two small endpoints, no auth, no middleware.

Run the tests with:
    make test-07
"""

from __future__ import annotations

import pathlib
import sys

import duckdb
from fastapi import FastAPI

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import capstone  # noqa: E402

app = FastAPI()
app.state.db = duckdb.connect(":memory:")
app.state.logger = capstone.configure_logging()


@app.post("/ingest/fhir")
def ingest_fhir(observation: dict) -> dict:
    """Ingest one FHIR Observation (the request body, as a plain dict).

    Hint: call capstone.ingest_fhir_observation(app.state.db, observation,
    app.state.logger) and return its result directly — FastAPI will
    serialize the dict to JSON for you.

    TODO: implement.
    """
    raise NotImplementedError


@app.get("/patients/{patient_id}/risk-timeline")
def risk_timeline(patient_id: str) -> list[dict]:
    """Return the full versioned risk-signal audit history for one patient.

    Hint: call capstone.get_risk_timeline(app.state.db, patient_id) and
    return it directly.

    TODO: implement.
    """
    raise NotImplementedError
