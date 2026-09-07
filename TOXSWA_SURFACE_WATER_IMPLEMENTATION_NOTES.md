# EnviroChem Studio v2.12 — TOXSWA surface-water implementation

## Purpose

v2.12 adds a surface-water and sediment workbench without conflating an EnviroChem calculation with the official FOCUS_TOXSWA executable.

Two modes are intentionally separate:

1. **FOCUS_TOXSWA official workflow** — an external, version-controlled regulatory workflow. EnviroChem prepares an auditable workflow record, checks missing inputs, records SWASH/SPIN/MACRO/PRZM dependencies, and imports official TOXSWA output.
2. **EnviroChem TOXSWA Process Screen** — a native transparent water/sediment calculation for adapted research and early-tier assessments. It uses TOXSWA-like process architecture but is not claimed to reproduce the FOCUS numerical kernel or standard scenarios.

The official version currently registered in this build is FOCUS_TOXSWA 5.5.3 / kernel 3.3.6. The regulatory source must be rechecked before a submission.

## Chemical-group routing

The workbench covers every contaminant group in the EnviroChem registry. The fate engine is shared, but the loading route is selected from the actual environmental release:

- pesticides: spray drift, drainage, runoff;
- human pharmaceuticals: usually WWTP point discharge;
- veterinary medicines: wastewater, aquaculture, pasture/manure runoff or drainage as appropriate;
- biocides and personal-care/detergent chemicals: use-specific wastewater/direct release;
- industrial organics: point, pulse or distributed industrial discharge;
- PFAS: adapted use with explicit warning that measured partitioning and persistence data are preferred;
- metals/inorganics: limited applicability because organic-carbon Koc and first-order degradation are not generally adequate;
- polymers/microplastics and nanomaterials: routing is available, but the current dissolved-chemical process core is explicitly not quantitative for particle transport;
- UVCBs and mixtures: component-based assessment is preferred.

Thus the platform can reuse the surface-water fate architecture across chemical groups while preserving the relevant sector-specific risk-assessment route.

## Native process screen

The alpha calculation uses a segmented waterbody and one active sediment cell below each water segment. It calculates:

- bulk advection through the waterbody;
- instantaneous linear partitioning to suspended solids;
- first-order transformation in water;
- first-order transformation in sediment;
- optional volatilisation from the dissolved water phase;
- diffusive exchange between the water layer and sediment;
- downstream dissolved and total water concentrations;
- total sediment concentration;
- global peak PECsw and PECsed;
- moving TWAEC windows of 1, 2, 3, 4, 7, 14, 21, 28, 42, 50 and 100 days;
- full water/sediment mass balance and numerical closure;
- applicability and official-input readiness warnings.

Loading modes are:

- spray drift;
- continuous point discharge;
- continuous distributed release;
- pulse/spill;
- lateral drainage;
- lateral runoff.

The spray-drift conversion is unit-tested: for application rate in kg/ha and drift in percent, deposited mass in mg/m² equals `application rate × drift percent`.

## Official FOCUS workflow

The managed TOXSWA adapter now expects and records:

- SPIN substance record;
- SWASH surface-water scenario;
- application pattern and drift deposition;
- MACRO `.m2t` drainage or PRZM `.p2t` runoff/erosion input where applicable;
- water and sediment DT50;
- Freundlich sorption parameters;
- molar mass, vapour pressure, solubility and aqueous diffusion coefficient;
- parent/metabolite scheme;
- exact model and executable versions.

The interface can prepare a workflow shell. Missing official inputs remain visibly missing rather than being invented.

## Official result import

The official output importer accepts `.sum`, `.txt` or `.out` text and conservatively extracts, when present:

- FOCUS_TOXSWA version;
- TOXSWA kernel version;
- global maximum PECsw;
- global maximum PECsed where identifiable;
- TWAECsw;
- TWAECsed;
- selected reported mass-balance terms.

The original output is represented by a SHA-256 hash and the import is stored as a separate immutable model run.

## Important current boundaries

- Native mode is not FOCUS regulatory equivalence.
- Standard FOCUS transient hydrology/scenario databases are not reconstructed natively.
- Native sediment is not yet the official depth-resolved sediment discretisation.
- A Freundlich exponent other than 1 is retained for official readiness but the alpha native screen currently uses a linear Kd approximation.
- For Koc > 30,000 L/kg, the native result is flagged and the official high-Koc sediment discretisation is required for the FOCUS run.
- Lateral drainage/runoff currently adds chemical mass but does not yet add the lateral water flux to native transient hydrology; use MACRO/PRZM → TOXSWA for official Step 3.
- Separate hydrolysis, photolysis and biotic rate constants are not yet split in the native screen. The interface currently offers lumped transformation or transformation restricted to dissolved-phase mass.
- No official TOXSWA output is generated unless the external authorised tool was actually run.

## Next implementation pass

Highest-value next work:

1. SWASH project/scenario writer and validator around the authorised installation;
2. MACRO `.m2t` / PRZM `.p2t` file metadata parser and linkage;
3. native depth-resolved sediment layering and iterative Freundlich partitioning for research comparison;
4. separate hydrolysis/photolysis/biotic transformation mode with meteorological radiation input;
5. parent/metabolite reaction matrices in the native research screen;
6. stronger official `.sum/.out` parser regression set using known FOCUS example outputs;
7. direct comparison report: native adapted screen versus imported official TOXSWA endpoints.
