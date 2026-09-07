# EnviroChem Studio v2.17 — external-model integration notes

## Scientific boundary

EnviroChem prepares, validates, hashes, imports and reviews external-model workflows. A prepared manifest is not a completed execution. A native EnviroChem screening result is never relabelled as SPIN, MACRO or GREAT-ER output.

## FOCUS SPIN 4.4

SPIN is the shared FOCUS repository for substance properties and transformation pathways. It facilitates PEARL and SWASH host workflows but does not simulate environmental fate.

The integration stores:

- chemical identity and record revision;
- reviewed fate-property snapshot;
- parent/metabolite pathway and formation fractions;
- SPIN/database version;
- selected host models;
- input hash, output snapshot hash and scientific review decision.

Operational constraints retained in every manifest:

- install SPIN locally before PEARL or SWASH;
- only one SPIN-connected host application should use the database at a time;
- do not uninstall SPIN 3.3 when its existing substance database must be retained;
- for the documented SPIN 4.4/PEARL combination, review TSCF in standalone SPIN and do not use 0.5 without a relevant substance-specific basis.

Official source: https://esdac.jrc.ec.europa.eu/projects/spin

## FOCUS MACRO 5.5.4a

MACRO is a physically based, one-dimensional dual-domain model for water flow and reactive solute transport in field soils. The FOCUS package uses MACRO model 5.2. The model supports the Chateaudun groundwater scenario and drainage loading for six FOCUS surface-water scenarios.

The integration distinguishes:

- `groundwater_leaching` runs, with groundwater/profile endpoints; and
- `surface_water_drainage` runs, which retain the SWASH linkage and `.m2t` lateral-entry file for TOXSWA.

The workflow records the FOCUS package, model and scenario-database versions; SPIN substance key; crop/application schedule; official soil, hydrology and weather inputs; degradation and Freundlich sorption; run settings; raw parameters/logs/binary files; parsed endpoints; and scientific review.

FOCUS_MACRO 5.5.4a is the Windows 11-compatible package containing the .NET Framework 4.7.2 prerequisite. The installed model is essentially the same 5.5.4/MACRO 5.2 implementation. The documented standalone M2T filename-case requirement is retained as a review warning.

Official source: https://esdac.jrc.ec.europa.eu/projects/macro

## GREAT-ER 4

GREAT-ER is a GIS-based river-basin exposure system for widely dispersed down-the-drain releases and defined WWTP or industrial point sources. It calculates spatial river PEC distributions and can support sediment and spatial-risk interpretation.

The integration requires:

- GREAT-ER deployment and PostgreSQL service;
- authorised basin database with identity, vintage and rights basis;
- georeferenced network dataset, CRS and reach identifier;
- reach hydrology and travel-time provenance;
- WWTP/industrial source inventory and coordinate system;
- emission/use linkage, WWTP removal and in-stream fate;
- deterministic or uncertainty settings;
- raw output capture, reach PEC mapping, catchment distribution and database-version record.

GREAT-ER 4 is described as open-source software, but a usable deployment and basin datasets remain separate prerequisites. EnviroChem’s native catchment network remains a transparent first-order comparison screen and is not an official GREAT-ER execution.

Technical positioning source: https://www.erasm.org/wp-content/uploads/2022/07/4.4.1.1GREAT-ER_TechnicalPositioning_DS.161116.pdf
