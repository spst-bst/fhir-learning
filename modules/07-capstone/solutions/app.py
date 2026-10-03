"""Reference solution for Module 7's FastAPI wiring. Don't peek until
you've had a real go."""

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
    return capstone.ingest_fhir_observation(app.state.db, observation, app.state.logger)


@app.get("/patients/{patient_id}/risk-timeline")
def risk_timeline(patient_id: str) -> list[dict]:
    return capstone.get_risk_timeline(app.state.db, patient_id)
