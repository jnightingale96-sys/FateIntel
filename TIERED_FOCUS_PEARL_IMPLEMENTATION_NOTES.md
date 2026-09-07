# EnviroChem Studio v2.10 — tiered FOCUS PEARL implementation

## Assessment order

The groundwater module now follows the intended tiered sequence:

1. application pattern and crop interception;
2. effective soil application rate;
3. PECsoil initial and repeated-application maximum;
4. FOCUS groundwater scenario and crop selection;
5. layer-resolved sorption, transformation and transport;
6. solute flux at the selected assessment plane, default 1 m;
7. PECgw comparison with the selected groundwater threshold.

Groundwater is the final risk compartment in the interface and calculation chain.

## Application rate and PECsoil

For each application:

`effective rate [kg/ha] = nominal rate × (1 − crop interception fraction)`

`PECsoil increment [µg/kg] = effective rate [kg/ha] × 10^9 / soil mass [kg/ha]`

The soil mass is calculated from the actual profile bulk density over the selected PECsoil mixing depth. Repeated applications are accumulated with first-order dissipation between application dates. The same effective rate is converted to kg/m² and scheduled into the transport model.

## Okehampton

Okehampton is implemented as a depth-resolved native scenario option with:

- 1.5 m model profile;
- A, Bw1, BC, C and C-deep horizons;
- horizon-specific organic carbon, bulk density, water content and transformation-depth factors;
- 2.5 cm cells in the upper profile, 5 cm cells below 0.5 m to 1 m, and 10 cm cells below 1 m;
- default 1 m solute-flux assessment plane;
- free-drain lower boundary context;
- scenario crop list and crop root-depth metadata.

The scenario selector also lists Châteaudun, Hamburg, Jokioinen, Kremsmünster, Piacenza, Porto, Sevilla and Thiva. Their official scenario metadata is registered, but their full depth profiles are not yet represented by the native engine. Official execution must use the locked FOCUS scenario database.

## Groundwater endpoint

The native quick screen reports a flux-weighted concentration at the selected target interface. The FOCUS-style horizon runs six warm-up years followed by 20 one-, two- or three-year assessment cycles, depending on application frequency. The indicative endpoint is the average of the 16th and 17th ranked cycle-average concentrations.

This percentile calculation is not labelled as a regulatory FOCUS result unless the official daily SWAP hydrology and official FOCUS PEARL executable are used.

## Scientific boundary

The native PEARLpy kernel includes equilibrium Freundlich sorption, first-order transformation, aqueous advection/dispersion/diffusion, root uptake, target-depth flux and bottom-boundary leaching. It does not yet include kinetic sorption, metabolites, preferential flow, volatilisation, lateral drainage, runoff or canopy processes.

Official FOCUS PEARL remains a separately installed and managed workflow. EnviroChem prepares, detects, orchestrates and audits it; it does not claim that native PEARLpy is the official model.
