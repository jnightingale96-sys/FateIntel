> Superseded by `TIERED_FOCUS_PEARL_IMPLEMENTATION_NOTES.md` in v2.10.

# EnviroChem Studio v2.9 — PEARL groundwater implementation

## What is native

The `ENVIROCHEM_PEARLPY_GROUNDWATER` service runs a transparent one-dimensional matrix-flow screening model from an initial layer-resolved soil concentration. It includes:

- equilibrium Freundlich sorption;
- temperature, moisture and optional depth corrections to first-order transformation;
- dissolved-phase advection, dispersion and diffusion;
- optional root-water uptake;
- lower-boundary leaching;
- layer/time outputs and strict mass-balance accounting.

The default hydrology is an explicitly labelled constant-flow screen. A SWAP user-defined CSV can replace it using `WC[n]`, `Q[n]`, `RWU[n]`, `T[n]` and `BOT`.

## What is not claimed

This native service is not official FOCUS PEARL and is not regulatory-equivalent. Official PEARL remains a managed external workflow. The screen does not currently implement non-equilibrium sorption, metabolites, volatilisation, macropores, lateral drainage, runoff, canopy or paddy processes.

## Input conversions

- `Kd [L/kg] / 1000 -> Kf [m3/kg]`
- `Kd = Koc × fOC` when Koc is supplied
- `Koc = Kd / fOC` as an effective compatibility value when Kd is supplied
- `layer mass [kg/m2] = Csoil [µg/kg] × bulk density [kg/m3] × layer thickness [m] × 1e-9`
- bottom-boundary flux-weighted concentration is calculated from leached mass divided by drainage water depth

## Comparison loop

The package also contains the uploaded SWAP importer and normalized-reference comparison harness. Official output can be converted to:

`time_d, layer, depth_m, mass_kg_m2, liquid_concentration_kg_m3`

and compared using bias, MAE, RMSE, maximum error, MdAPE and Pearson correlation.
