# EnviroChem Studio v2.15 — model expansion implementation notes

## Release purpose

v2.15 adds actual native modelling capability and managed official-model contracts. It does not count a registry card as a completed implementation and does not relabel a simplified native calculation as an official external model.

## 1. Native multimedia fate screen

For each environmental compartment `i`, the steady-state balance is:

```text
0 = Ei + Σj(kji × Mj) − Mi × (kdeg,i + kadv,i + Σj kij)
```

where:

- `Ei` is the emission to compartment `i` in kg/day;
- `Mi` is the steady-state chemical mass in kg;
- `kji` and `kij` are directed intermedia transfer rates per day;
- `kdeg,i = ln(2) / DT50i`;
- `kadv,i` is terminal advective removal per day.

EnviroChem assembles the coupled linear system and solves all compartment masses simultaneously. Intermedia flux is internal to the system and cancels from the global balance. The required global closure is:

```text
total emissions = total degradation + total advective loss
```

Reported units are `µg/m³` for air, `µg/L` for freshwater and `µg/kg` for soil/sediment. Solid density is therefore mandatory for soil and sediment.

### Boundary versus SimpleBox

RIVM describes SimpleBox as a Mackay-type multimedia mass-balance model operating across air, water, sediment and soil at regional, continental and global scales. The native EnviroChem screen uses user-supplied effective first-order transfers and does not reproduce the complete SimpleBox fugacity, landscape or nested-scale parameterisation.

The separate `SIMPLEBOX` contract preserves this distinction and manages an external SimpleBox run.

## 2. Native catchment river-network screen

For a WWTP or industrial effluent:

```text
local load (kg/day) = effluent concentration (µg/L)
                    × effluent flow (m³/day)
                    × 10^-6
```

For each river reach:

```text
kin = ln(2) / DT50water + kother

outlet load = inlet load × exp(−kin × travel time)

mean load = inlet load × [1 − exp(−kin × travel time)] / (kin × travel time)

PEC (µg/L) = load (kg/day) × 10^6 / river flow (m³/day)
```

Segments are evaluated in topological order. Loads from multiple upstream reaches can join at a confluence. A segment cannot feed two downstream segments until explicit flow-split support is added, because silently duplicating mass would be incorrect.

The global network balance is:

```text
all local point-source inputs
= all reach transformation/sink losses
+ all terminal-reach outputs
```

### Boundary versus GREAT-ER and ePiE

GREAT-ER is a georeferenced river-basin exposure tool for point-source chemicals. ePiE is a published high-resolution European surface-water model developed specifically for pharmaceuticals. The native EnviroChem model currently implements transparent steady-state load routing only. It does not claim their GIS, hydrology, uncertainty or data architecture.

Separate `GREATER` and `EPIE` contracts preserve method/data access, external execution and imported results.

## 3. EPI Suite evidence contract

EPA EPI Suite 4.11 is registered as an external estimation suite, including physical/chemical property, biodegradation, hydrolysis/atmospheric fate, BCF/BAF and Level III fugacity outputs. Every estimate is stored as:

```text
modelled evidence candidate
→ module and version retained
→ measured overrides retained separately
→ applicability reviewed
→ explicit scientist selection if used
```

No EPI Suite estimate automatically supersedes measured evidence.

## 4. PWC3 update

EPA's current pesticide model page identifies PWC Version 3 as the latest Pesticide in Water Calculator. EnviroChem retains the stable internal key `PWC` so historical workflows remain readable, but the displayed model and new adapter contract are now `EPA Pesticide in Water Calculator 3 (PWC3)`.

PWC3 is treated as the current integrated US pesticide-water workflow. Standalone PRZM and EXAMS remain available only for explicit specialist or legacy reproducibility use.

## 5. Routing rules

- Down-the-drain and point-source releases: SimpleTreat/Activity SimpleTreat where applicable → EnviroChem catchment river screen → GREAT-ER/ePiE at higher tier.
- Industrial/direct multi-compartment emission: native multimedia screen → SimpleBox refinement.
- EU pesticide agricultural surface water: SWASH → MACRO/PRZM → FOCUS_TOXSWA.
- US pesticide water: PWC3.
- Wastewater irrigation and biosolids: exposure loading/soil calculation first, then relevant leaching, runoff, surface-water and plant pathways.

## 6. Primary model sources

- RIVM, SimpleBox: https://www.rivm.nl/en/soil-and-water/simplebox
- CEFIC LRI, GREAT-ER: https://cefic-lri.org/toolbox/great-er/
- Oldenkamp et al. (2018), ePiE: https://doi.org/10.1021/acs.est.8b03862
- US EPA, EPI Suite: https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface
- US EPA, pesticide risk-assessment models/PWC3: https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment
