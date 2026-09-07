# FOCUS installation and EnviroChem adapter guide

## What is installed

The official European Commission JRC packages are external Windows applications. EnviroChem does not redistribute them inside its own archive. `INSTALL_FOCUS_MODELS.bat` downloads the packages from the official ESDAC addresses into `focus_downloads`.

Install in this order:

1. **FOCUS SPIN 4.4** — substance property and transformation-pathway database.
2. **FOCUS PEARL 5.5.5** — groundwater leaching and Tier-3A soil outputs.
3. **FOCUS SWASH 5.3** — Step 3 surface-water orchestration shell.
4. **FOCUS MACRO 5.5.4a** — preferential-flow groundwater model and surface-water drainage loader (MACRO model 5.2).
5. **FOCUS TOXSWA 5.5.3** — water and sediment fate solver.

SWASH is not itself the fate model. It prepares and links drift, MACRO drainage or PRZM runoff/erosion loadings to TOXSWA.

## Current official compatibility points

- SPIN must be installed before PEARL or SWASH and must be on a local drive.
- PEARL 5.5.5 is the preferred released PEARL version for new submissions.
- FOCUS_MACRO 5.5.4a is the current Windows 11-compatible installer; the model is essentially the 5.5.4/MACRO 5.2 implementation.
- MACRO is used for the Chateaudun groundwater scenario and drainage inputs for six FOCUS surface-water scenarios. Retain generated `.m2t` files for TOXSWA.
- TOXSWA must be installed below the SWASH directory, normally `C:\SWASH\TOXSWA`.
- With SPIN 4.4 opened through PEARL, the TSCF field may be disabled. Open SPIN standalone to enter a relevant substance-specific value. Do not use 0.5 as an unexplained default.
- In SWASH 5.3, after viewing/editing Applications, save and export the project before TOXSWA. The official warning states that otherwise drift can be reset to 100%.

## Scientific boundary

FOCUS PEARL, MACRO, SWASH and TOXSWA are pesticide exposure tools. EnviroChem may use them for comparative or research assessments of pharmaceuticals, wastewater irrigation or biosolids only when this non-standard use is explicitly labelled and scientifically justified. A prepared FOCUS workflow is not represented as an accepted pharmaceutical regulatory assessment.

## EnviroChem integration status

- Installation manifest and path detection: working.
- Versioned SPIN/PEARL/MACRO/SWASH/TOXSWA workflow contracts: working.
- Input readiness and missing-data validation: working.
- Raw result import, hashing and scientific review: working.
- Fully automated manipulation of the legacy Windows GUIs/databases: not yet complete.
