# EnviroChem Studio v2.7 — Science QA corrections

## Veterinary ERA

- VICH GL38 section 2.7 refers to persistence and accumulation in **soil**.
- Manure-storage DT50 remains a separate parameter used only for loss during storage.
- Soil DT50/DT90 now controls the repeated annual soil-application series.
- A soil DT90 above one year triggers an explicit persistence warning and multi-year output.
- Intensive-animal initial and refined PEC calculations now use a consistent annual administered mass, retaining animal turnover and treatment events.
- The Outlier BIOWIN equation remains a labelled manure-screening compatibility mode and is not used as a soil persistence surrogate.

## Droge–Goss

- The application equations already used per-compound named descriptor fields and were not vulnerable to spreadsheet relative-row shifts.
- Manual atom counts are now checked against the molecular formula and conflicting inputs are rejected.
- A reviewed McGowan volume or explicit total bond count is preferred.
- Formula/ring-derived bond estimation remains available only as a visibly warned screening descriptor.
- Large workbook tabular outputs are not used as model calibration values. Validation remains anchored to reviewed worked examples and explicit descriptor payloads.

## Confidentiality

No source workbook, corrected workbook, comparison table, Outlier material or private row-level audit is included in the distributable application archive.
