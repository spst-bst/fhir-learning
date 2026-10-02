# Synthetic Patient Data

All data under `fhir/` is **synthetic**, generated with
[Synthea](https://github.com/synthetichealth/synthea) (MITRE). No real
patient data of any kind is used anywhere in this repository.

Generated with:

```
java -jar synthea-with-dependencies.jar \
  -p 15 -s 20261002 \
  --exporter.fhir.export true \
  --exporter.fhir.use_us_core_ig true \
  --exporter.years_of_history 10 \
  Massachusetts
```

Then curated down to 5 patients + a shared reference bundle (see files
below) to keep the repo small and focused on the resource types this course
covers. Curation:

- Kept only: `Patient`, `Encounter`, `Condition`, `Observation`,
  `DiagnosticReport`, `Procedure`, `MedicationRequest`, `Medication`,
  `Immunization`, `AllergyIntolerance`. Dropped Synthea's `Claim`,
  `ExplanationOfBenefit`, `DocumentReference`, `SupplyDelivery`, `Device`,
  `ImagingStudy`, `CareTeam`, `CarePlan`, `Provenance` — out of scope for
  this course.
- Added a couple of hand-authored `FamilyMemberHistory` resources (Synthea
  doesn't generate these in this seed), since Module 2 and the capstone use
  family history as a cancer-risk-relevant resource.
- Rewrote every `Bundle.entry.request` to `PUT /{ResourceType}/{id}`
  instead of Synthea's default `POST` — this makes `id`s stable (matches
  the source JSON, needed for reproducible exercises/tests) and makes
  reloading idempotent.

## Files

- `00-reference-organizations-practitioners.json` — shared `Organization`
  and `Practitioner` resources that patient records reference by
  identifier. Load this **first**.
- `patient-01-katlyn-infant.json` — healthy infant, minimal history.
- `patient-02-buster-toddler.json` — healthy toddler.
- `patient-03-lavern-prediabetes.json` — adult, prediabetes.
- `patient-04-ellsworth-diabetes-chf.json` — older adult, type 2 diabetes,
  CHF, hyperlipidemia — rich in labs, good for Module 3's normalization
  exercises. Has a hand-added maternal family history of type 2 diabetes.
- `patient-05-brandy-breast-cancer.json` — adult with a malignant breast
  neoplasm diagnosis. Has hand-added family history of breast cancer
  (mother) and ovarian cancer (maternal grandmother) — the richest case for
  the capstone's risk-signal timeline.

Load everything with `make load-data` (see `scripts/load_synthea_data.py`).
