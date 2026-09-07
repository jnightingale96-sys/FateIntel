# EnviroChem v2.6 implementation notes

## Native biosolids screen

The module accepts either chemical mass transferred to WWTP sludge or a measured biosolids concentration. It applies explicit storage degradation, land-applied fraction, area, soil depth, bulk density, annual pulses and soil degradation. It reports both a single-application increment and a repeated-application series.

No universal legal biosolids application rate is hidden in the calculation. The EU/UK/Swiss regulatory pack and US Part 503 context are attached separately.

## Native plant uptake screen

The first working plant module supports:

- a neutral-organic Briggs TSCF water-flux screen;
- user-supplied TSCF;
- user-supplied empirical root/shoot/edible BCFs.

It does not yet claim to reproduce the full ionisation-aware Trapp PPCP model. The next scientific step is a validated implementation of acids, bases, ion trapping, protein sorption, xylem/phloem transfer and crop-specific parameter sets.

## FOCUS PEARL / SWASH / TOXSWA

The application now contains an official-source installation manifest, Windows download assistant, installation-path checks, adapter contracts and audit-ready workflow records.

- PEARL is the groundwater/soil-plant model and includes passive plant uptake as a model parameter/flux.
- SWASH is the Step 3 orchestration shell.
- TOXSWA is the water/sediment fate solver.
- SWASH requires upstream MACRO drainage or PRZM runoff/erosion for those entry routes.

FOCUS models are designed for pesticides. Adapted use for pharmaceuticals, wastewater irrigation or biosolids is labelled research/comparative unless accepted by the receiving authority.
