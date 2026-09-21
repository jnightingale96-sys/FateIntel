from __future__ import annotations

"""Surface-water/sediment modelling support for EnviroChem.

This module deliberately separates two things:

1. ``FOCUS_TOXSWA``: the official external regulatory tool. EnviroChem prepares,
   checks and imports that workflow but does not pretend to be the official kernel.
2. ``ENVIROCHEM_TOXSWA_PROCESS_SCREEN``: a transparent native, finite-volume
   water/sediment screen based on the same high-level process architecture
   (advection, first-order transformation, sorption, volatilisation and diffusive
   water-sediment exchange). It is useful for non-pesticide research and early
   tier assessments, but is explicitly not regulatory-equivalent to FOCUS_TOXSWA.

All rates, dimensions and partitioning inputs remain visible. No hidden official
FOCUS scenario defaults are embedded in the native screen.
"""

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
import math
import re
from typing import Any


MODEL_VERSION = "0.1.0-alpha"
OFFICIAL_FOCUS_VERSION = "5.5.3"
TWA_WINDOWS_DAYS = [1, 2, 3, 4, 7, 14, 21, 28, 42, 50, 100]


ROUTE_MATRIX: dict[str, dict[str, Any]] = {
    "pesticide": {
        "default_loading_mode": "spray_drift",
        "recommended_routes": ["spray_drift", "lateral_drainage", "lateral_runoff"],
        "regulatory_note": "For EU plant-protection products use the official SWASH → MACRO/PRZM → TOXSWA Step 3 workflow when a FOCUS assessment is required.",
        "applicability": "direct",
    },
    "biocide": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "lateral_runoff"],
        "regulatory_note": "Select the product-type/use-specific release scenario first; use of the native screen is an exposure refinement, not an automatic BPR regulatory scenario.",
        "applicability": "adapted",
    },
    "human_pharmaceutical": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "continuous_distributed"],
        "regulatory_note": "Typical loading is WWTP effluent concentration × discharge flow. FOCUS_TOXSWA use is adapted/research unless explicitly accepted by the receiving authority.",
        "applicability": "adapted",
    },
    "veterinary_pharmaceutical": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "lateral_drainage", "lateral_runoff"],
        "regulatory_note": "Route depends on aquaculture, pasture, manure/soil or wastewater release. VICH/EMA exposure logic remains the controlling regulatory pathway.",
        "applicability": "adapted",
    },
    "personal_care_cosmetic": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge"],
        "regulatory_note": "Usually linked to treated municipal effluent or a documented direct discharge.",
        "applicability": "adapted",
    },
    "detergent_cleaner": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge"],
        "regulatory_note": "Usually linked to WWTP effluent or use-specific direct release.",
        "applicability": "adapted",
    },
    "industrial_organic": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "continuous_distributed"],
        "regulatory_note": "Use site-specific discharge concentration/flow or a documented emission scenario.",
        "applicability": "adapted",
    },
    "pfas_persistent_mobile": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "lateral_drainage"],
        "regulatory_note": "Persistence and ionisation make generic Koc/first-order assumptions especially uncertain; measured partitioning and transformation data should be preferred.",
        "applicability": "conditional",
    },
    "hydrocarbon_solvent": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass"],
        "regulatory_note": "Volatilisation can dominate; provide a defensible volatilisation parameter or use the official/external model inputs.",
        "applicability": "conditional",
    },
    "metal_inorganic": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "continuous_distributed"],
        "regulatory_note": "Organic-carbon Koc and first-order degradation are generally not appropriate for metals. Use only with substance-specific partitioning/speciation assumptions and label the result adapted.",
        "applicability": "limited",
    },
    "polymer_microplastic": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass"],
        "regulatory_note": "The dissolved-chemical process core is not validated for particle settling, aggregation or size-dependent transport.",
        "applicability": "not_quantitative",
    },
    "nanomaterial": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass"],
        "regulatory_note": "The current process core does not represent aggregation, dissolution or particle-specific sedimentation.",
        "applicability": "not_quantitative",
    },
    "uvcb_complex_substance": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass"],
        "regulatory_note": "Prefer component/block assessment. A single Koc/DT50 is rarely representative of a UVCB.",
        "applicability": "limited",
    },
    "mixture_formulation": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "spray_drift", "pulse_mass"],
        "regulatory_note": "Run individual active/relevant components unless a defensible whole-mixture fate basis exists.",
        "applicability": "component_based",
    },
    "emerging_contaminant": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "continuous_distributed", "lateral_drainage", "lateral_runoff"],
        "regulatory_note": "Select the release route from actual use/emission evidence; the native process screen is scenario-based rather than product-class prescriptive.",
        "applicability": "adapted",
    },
    "pah": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "lateral_runoff"],
        "regulatory_note": "Koc-based partitioning is chemically valid for PAHs but strongly sediment-associated; prefer measured sediment partitioning and treat the result as a screening estimate. Bioaccumulation and sediment-benthic endpoints are not covered.",
        "applicability": "conditional",
    },
    "legacy_pop_organic": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass", "lateral_runoff"],
        "regulatory_note": "Persistent, hydrophobic and bioaccumulative: the water-column process screen omits sediment burial, resuspension and food-web transfer. Screening/comparative use only; POPs regulatory status is not assessed here.",
        "applicability": "conditional",
    },
    "organotin": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": ["continuous_point_discharge", "pulse_mass"],
        "regulatory_note": "Organotins partition to sediment and speciate; generic Koc/first-order assumptions are uncertain. Prefer measured partitioning and transformation data.",
        "applicability": "conditional",
    },
    "radionuclide": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": [],
        "regulatory_note": "Not a chemical-fate problem: radiological assessment is dose-based and outside this process screen. EXTERNAL MODEL REQUIRED.",
        "applicability": "not_quantitative",
    },
    "contaminated_mixture": {
        "default_loading_mode": "continuous_point_discharge",
        "recommended_routes": [],
        "regulatory_note": "Run each contaminant separately under its own group; concentrations are not summed and additivity is not assumed.",
        "applicability": "component_based",
    },
}


@dataclass(frozen=True)
class Capacities:
    water_l: float
    sediment_l: float
    water_dissolved_fraction: float
    sediment_kd_l_kg: float
    suspended_kd_l_kg: float


def _route_info(group: str) -> dict[str, Any]:
    return ROUTE_MATRIX.get(group, ROUTE_MATRIX["emerging_contaminant"])


def manifest() -> dict[str, Any]:
    return {
        "module": "EnviroChem TOXSWA surface-water workbench",
        "native_model_key": "ENVIROCHEM_TOXSWA_PROCESS_SCREEN",
        "native_model_version": MODEL_VERSION,
        "official_model": "FOCUS_TOXSWA",
        "official_stable_version_registered": OFFICIAL_FOCUS_VERSION,
        "separation_of_modes": {
            "official_focus": "Managed external workflow. SWASH prepares standard Step 3 runs; MACRO or PRZM supplies lateral entries; TOXSWA supplies surface-water/sediment fate.",
            "adapted_process_screen": "Native transparent research/screening calculation with user-visible geometry, flow and loading. It is not the FOCUS_TOXSWA executable, is not regulatory-equivalent, and must not be reported as an official FOCUS run.",
        },
        "processes": [
            "advection through segmented water body",
            "instantaneous linear water suspended-solids partitioning",
            "first-order water transformation",
            "first-order sediment transformation",
            "optional first-order volatilisation from dissolved water phase",
            "diffusive water-sediment exchange",
        ],
        "loading_modes": {
            "spray_drift": "Distributed pulse over the selected water-surface stretch.",
            "continuous_point_discharge": "Continuous point source, e.g. WWTP or industrial effluent.",
            "continuous_distributed": "Continuous loading distributed over a selected watercourse stretch.",
            "pulse_mass": "One-off point or distributed pulse/spill.",
            "lateral_drainage": "Continuous distributed drainage concentration × lateral water flux.",
            "lateral_runoff": "Continuous distributed runoff concentration × lateral water flux.",
        },
        "official_inputs": [
            "SWASH project / standard scenario and waterbody combination",
            "SPIN substance record including parent/metabolite scheme",
            "application scheme and drift deposition",
            "MACRO .m2t drainage OR PRZM .p2t runoff/erosion input when required",
            "water and sediment transformation half-lives and reference temperatures",
            "Freundlich sorption parameters for suspended solids and sediment",
            "molar mass, vapour pressure, solubility and aqueous diffusion coefficient",
            "exact TOXSWA/SWASH/SPIN/model versions",
        ],
        "official_outputs": [
            "global maximum PECsw",
            "global maximum PECsed",
            "PEC values after the global maximum",
            "TWAECsw and TWAECsed",
            "water and sediment mass balances",
            "time series and spatial/depth profiles when requested",
        ],
        "twa_windows_days": TWA_WINDOWS_DAYS,
        "routing": ROUTE_MATRIX,
        "numerical_boundary": "The native screen uses a finite-volume/upwind water transport core and one active sediment layer per water segment. It is a transparent approximation and does not reproduce the official TOXSWA numerical kernel, transient FOCUS hydrology or scenario databases.",
    }


def route_recommendation(contaminant_group: str) -> dict[str, Any]:
    row = dict(_route_info(contaminant_group))
    row["contaminant_group"] = contaminant_group
    return row


def _selected_segments(payload: dict[str, Any], dx: float) -> list[int]:
    n = int(payload["n_segments"])
    start = max(0.0, float(payload.get("loaded_start_m", 0.0)))
    end = min(float(payload["waterbody_length_m"]), float(payload.get("loaded_end_m") or payload["waterbody_length_m"]))
    if end <= start:
        raise ValueError("loaded_end_m must be greater than loaded_start_m")
    chosen = []
    for i in range(n):
        centre = (i + 0.5) * dx
        if start <= centre <= end:
            chosen.append(i)
    if not chosen:
        chosen = [min(n - 1, max(0, int(start / dx)))]
    return chosen


def _capacities(payload: dict[str, Any], segment_volume_m3: float, sediment_volume_m3: float) -> Capacities:
    koc = float(payload["koc_l_kg"])
    sed_kd = payload.get("sediment_kd_l_kg")
    ss_kd = payload.get("suspended_solids_kd_l_kg")
    if sed_kd is None:
        sed_kd = koc * float(payload["sediment_organic_carbon_fraction"])
    if ss_kd is None:
        ss_kd = koc * float(payload["suspended_solids_organic_carbon_fraction"])
    ss_kg_l = float(payload["suspended_solids_mg_l"]) * 1e-6
    water_partition_factor = 1.0 + float(ss_kd) * ss_kg_l
    water_capacity_l = segment_volume_m3 * 1000.0 * water_partition_factor
    sed_mass_kg = float(payload["sediment_bulk_density_kg_m3"]) * sediment_volume_m3
    sed_pore_l = float(payload["sediment_porosity"]) * sediment_volume_m3 * 1000.0
    sediment_capacity_l = sed_pore_l + float(sed_kd) * sed_mass_kg
    return Capacities(
        water_l=water_capacity_l,
        sediment_l=max(sediment_capacity_l, 1e-12),
        water_dissolved_fraction=1.0 / water_partition_factor,
        sediment_kd_l_kg=float(sed_kd),
        suspended_kd_l_kg=float(ss_kd),
    )


def _temperature_corrected_dt50(dt50_days: float, source_c: float, target_c: float, ea_kj_mol: float) -> float:
    if abs(source_c - target_c) < 1e-12:
        return dt50_days
    r = 8.31446261815324
    ts = source_c + 273.15
    tt = target_c + 273.15
    return dt50_days * math.exp((ea_kj_mol * 1000.0 / r) * (1.0 / tt - 1.0 / ts))


def _moving_twa(samples: list[tuple[float, float]], windows: list[int]) -> dict[str, float | None]:
    """Maximum moving TWA from a regular/near-regular time series using trapezoid integration.

    The series is small enough that a straightforward sliding calculation keeps the
    implementation transparent. Values are concentrations and time is in days.
    """
    if len(samples) < 2:
        return {str(w): (samples[0][1] if samples and w <= 1 else None) for w in windows}
    out: dict[str, float | None] = {}
    times = [x[0] for x in samples]
    vals = [x[1] for x in samples]
    for w in windows:
        best: float | None = None
        left = 0
        # cumulative trapezoid integral at sample points
        cumulative = [0.0]
        for i in range(1, len(samples)):
            cumulative.append(cumulative[-1] + 0.5 * (vals[i - 1] + vals[i]) * (times[i] - times[i - 1]))
        for right in range(1, len(samples)):
            target = times[right] - w
            while left + 1 < right and times[left + 1] <= target:
                left += 1
            if target < times[0] - 1e-9:
                continue
            # interpolate value and cumulative integral at exact left boundary
            if times[left] == target or left == right:
                int_left = cumulative[left]
            else:
                j = min(left + 1, right)
                t0, t1 = times[left], times[j]
                if t1 <= t0:
                    int_left = cumulative[left]
                else:
                    frac = (target - t0) / (t1 - t0)
                    v_target = vals[left] + frac * (vals[j] - vals[left])
                    int_left = cumulative[left] + 0.5 * (vals[left] + v_target) * (target - t0)
            integral = cumulative[right] - int_left
            avg = integral / w
            if best is None or avg > best:
                best = avg
        out[str(w)] = best
    return out


def _loading_rate_mg_day(payload: dict[str, Any]) -> float:
    mode = payload["loading_mode"]
    if mode == "continuous_point_discharge":
        # 1 µg/L × 1 m³ = 1 mg
        return float(payload["discharge_concentration_ug_l"]) * float(payload["discharge_flow_m3_day"])
    if mode in {"lateral_drainage", "lateral_runoff"}:
        return float(payload["lateral_concentration_ug_l"]) * float(payload["lateral_water_flux_m3_day"])
    if mode == "continuous_distributed":
        return float(payload["continuous_mass_mg_day"])
    return 0.0


def _official_readiness(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        ("Substance properties", True, "Koc, water/sediment DT50 and key physical properties are stored for this screen; official SPIN records still need verification."),
        ("Application / loading", True, f"Native loading route: {payload['loading_mode'].replace('_', ' ')}."),
        ("FOCUS standard scenario", False, "Select the crop/scenario/waterbody combination in SWASH for an official Step 3 run."),
        ("SWASH project", False, "Official FOCUS Step 3 project must be created/exported in SWASH."),
        ("MACRO or PRZM lateral file", payload["loading_mode"] not in {"lateral_drainage", "lateral_runoff"}, "Required for official drainage/runoff routes; .m2t and .p2t files are not fabricated by the native screen."),
        ("Official executable output", False, "Run the authorised local FOCUS_TOXSWA installation and import the .sum/.out artefact."),
    ]
    return [{"label": label, "status": "ready" if ok else "required", "note": note} for label, ok, note in rows]


def run_process_screen(payload: dict[str, Any]) -> dict[str, Any]:
    n = int(payload["n_segments"])
    length = float(payload["waterbody_length_m"])
    width = float(payload["waterbody_width_m"])
    depth = float(payload["water_depth_m"])
    flow = float(payload["receiving_flow_m3_day"])
    dx = length / n
    if min(length, width, depth, dx) <= 0:
        raise ValueError("Waterbody dimensions must be positive")

    segment_volume_m3 = dx * width * depth
    segment_volume_l = segment_volume_m3 * 1000.0
    sediment_depth = float(payload["sediment_active_depth_m"])
    sediment_volume_m3 = dx * width * sediment_depth
    sediment_mass_kg = sediment_volume_m3 * float(payload["sediment_bulk_density_kg_m3"])
    capacities = _capacities(payload, segment_volume_m3, sediment_volume_m3)

    water_dt50 = _temperature_corrected_dt50(
        float(payload["water_dt50_days"]), float(payload["transformation_reference_temperature_c"]),
        float(payload["water_temperature_c"]), float(payload["activation_energy_kj_mol"]),
    )
    sed_dt50 = _temperature_corrected_dt50(
        float(payload["sediment_dt50_days"]), float(payload["transformation_reference_temperature_c"]),
        float(payload["water_temperature_c"]), float(payload["activation_energy_kj_mol"]),
    )
    kw = math.log(2.0) / water_dt50
    ks = math.log(2.0) / sed_dt50
    kvol = 0.0
    if payload.get("volatilisation_half_life_days"):
        kvol = math.log(2.0) / float(payload["volatilisation_half_life_days"])

    d_eff = float(payload["aqueous_diffusion_coefficient_m2_day"]) * float(payload["relative_sediment_diffusion"])
    path = float(payload["interface_diffusion_path_m"])
    area_interface = width * dx
    conductance_l_day = d_eff * area_interface / path * 1000.0 if d_eff > 0 else 0.0

    advective_dt = float("inf") if flow <= 0 else 0.45 * segment_volume_m3 / flow
    exchange_rate = conductance_l_day * (1.0 / capacities.water_l + 1.0 / capacities.sediment_l) if conductance_l_day > 0 else 0.0
    exchange_dt = float("inf") if exchange_rate <= 0 else 0.25 / exchange_rate
    dt = min(float(payload["max_transport_substep_days"]), advective_dt, exchange_dt)
    if not math.isfinite(dt):
        dt = float(payload["max_transport_substep_days"])
    if dt <= 0:
        raise ValueError("Resolved numerical time step is not positive")
    # Avoid an accidental pathological run while retaining a strict stability signal.
    if dt < 1e-5:
        raise ValueError("Numerical time step below 1e-5 d. Reduce flow/diffusion stiffness or refine the scenario deliberately.")

    selected = _selected_segments(payload, dx)
    water = [0.0] * n
    sediment = [0.0] * n
    initial_water_ug_l = float(payload.get("initial_water_concentration_ug_l", 0.0))
    initial_sed_ug_kg = float(payload.get("initial_sediment_concentration_ug_kg", 0.0))
    for i in range(n):
        water[i] = initial_water_ug_l / 1000.0 * segment_volume_l
        sediment[i] = initial_sed_ug_kg * sediment_mass_kg / 1000.0
    initial_mass = sum(water) + sum(sediment)

    mode = payload["loading_mode"]
    continuous_rate = _loading_rate_mg_day(payload)
    # For continuous point release, the mass is introduced at the first loaded segment.
    point_segment = selected[0]
    app_days: list[float] = []
    pulse_masses: list[float] = []
    if mode == "spray_drift":
        start = float(payload["first_application_day"])
        count = int(payload["number_applications"])
        interval = float(payload["application_interval_days"])
        app_days = [start + j * interval for j in range(count)]
        # With rate in kg/ha: deposition mg/m² = kg/ha × drift%.
        deposition_mg_m2 = float(payload["application_rate_kg_ha"]) * float(payload["drift_percent"])
        loaded_area_m2 = width * len(selected) * dx
        pulse_masses = [deposition_mg_m2 * loaded_area_m2 for _ in app_days]
    elif mode == "pulse_mass":
        app_days = [float(payload["pulse_day"])]
        pulse_masses = [float(payload["pulse_mass_mg"])]

    event_done = [False] * len(app_days)
    duration = float(payload["simulation_days"])
    output_interval = float(payload["output_interval_days"])
    next_output = 0.0

    cumulative_input = 0.0
    cumulative_outflow = 0.0
    cumulative_water_transform = 0.0
    cumulative_sed_transform = 0.0
    cumulative_volatilised = 0.0
    cumulative_exchange_to_sed = 0.0
    cumulative_exchange_to_water = 0.0

    max_water_total = (-1.0, 0.0)
    max_water_dissolved = (-1.0, 0.0)
    max_sed = (-1.0, 0.0)
    samples_total: list[tuple[float, float]] = []
    samples_diss: list[tuple[float, float]] = []
    samples_sed: list[tuple[float, float]] = []
    series: list[dict[str, float]] = []

    def record(t: float) -> None:
        nonlocal max_water_total, max_water_dissolved, max_sed
        i = n - 1
        total_ug_l = (water[i] / segment_volume_l) * 1000.0
        diss_mg_l = water[i] / capacities.water_l
        diss_ug_l = diss_mg_l * 1000.0
        sed_ug_kg = (sediment[i] / sediment_mass_kg) * 1000.0
        samples_total.append((t, total_ug_l))
        samples_diss.append((t, diss_ug_l))
        samples_sed.append((t, sed_ug_kg))
        if total_ug_l > max_water_total[0]: max_water_total = (total_ug_l, t)
        if diss_ug_l > max_water_dissolved[0]: max_water_dissolved = (diss_ug_l, t)
        if sed_ug_kg > max_sed[0]: max_sed = (sed_ug_kg, t)
        series.append({"time_d": t, "water_total_ug_l": total_ug_l, "water_dissolved_ug_l": diss_ug_l, "sediment_ug_kg": sed_ug_kg})

    t = 0.0
    record(0.0)
    steps = 0
    while t < duration - 1e-12:
        h = min(dt, duration - t)
        t_next = t + h

        # Pulse events falling within this sub-step are applied at its beginning. The
        # resolved h is normally short compared with regulatory application spacing.
        for j, day in enumerate(app_days):
            if not event_done[j] and t - 1e-12 <= day < t_next + 1e-12:
                mass = pulse_masses[j]
                if mode == "spray_drift":
                    per = mass / len(selected)
                    for i in selected: water[i] += per
                else:
                    if payload.get("pulse_distributed", False):
                        per = mass / len(selected)
                        for i in selected: water[i] += per
                    else:
                        water[point_segment] += mass
                cumulative_input += mass
                event_done[j] = True

        # Continuous load.
        if continuous_rate > 0:
            mass = continuous_rate * h
            if mode in {"continuous_distributed", "lateral_drainage", "lateral_runoff"}:
                per = mass / len(selected)
                for i in selected: water[i] += per
            else:
                water[point_segment] += mass
            cumulative_input += mass

        # First-order water transformation and volatilisation. Separate-process
        # mode acts on the dissolved fraction only, while lumped mode acts on the
        # total water-layer mass.
        phase_factor = 1.0 if payload["water_transformation_mode"] == "lumped" else capacities.water_dissolved_fraction
        for i in range(n):
            if water[i] <= 0: continue
            k_total = kw * phase_factor + kvol * capacities.water_dissolved_fraction
            if k_total > 0:
                fraction_lost = 1.0 - math.exp(-k_total * h)
                lost = water[i] * fraction_lost
                if lost > 0:
                    # allocate competing first-order sinks by rate contribution
                    denom = k_total
                    tr = lost * (kw * phase_factor / denom) if denom else 0.0
                    vol = lost - tr
                    water[i] -= lost
                    cumulative_water_transform += tr
                    cumulative_volatilised += vol

        # Sediment transformation.
        if ks > 0:
            frac = 1.0 - math.exp(-ks * h)
            for i in range(n):
                lost = sediment[i] * frac
                sediment[i] -= lost
                cumulative_sed_transform += lost

        # Diffusive water-sediment exchange, one active sediment cell beneath each
        # water segment. Concentration is the dissolved phase concentration.
        if conductance_l_day > 0:
            for i in range(n):
                cw = water[i] / capacities.water_l  # mg/L
                cs = sediment[i] / capacities.sediment_l  # mg/L porewater equilibrium
                transfer = conductance_l_day * (cw - cs) * h
                if transfer >= 0:
                    transfer = min(transfer, water[i])
                    water[i] -= transfer
                    sediment[i] += transfer
                    cumulative_exchange_to_sed += transfer
                else:
                    back = min(-transfer, sediment[i])
                    sediment[i] -= back
                    water[i] += back
                    cumulative_exchange_to_water += back

        # Conservative upwind advection. This transports the total water-layer
        # mass (dissolved + suspended-solid associated mass) with bulk flow.
        if flow > 0:
            frac_out = min(1.0, flow * h / segment_volume_m3)
            outgoing = [m * frac_out for m in water]
            for i in range(n):
                water[i] -= outgoing[i]
            for i in range(1, n):
                water[i] += outgoing[i - 1]
            cumulative_outflow += outgoing[-1]

        t = t_next
        steps += 1
        while next_output + output_interval <= t + 1e-9:
            next_output += output_interval
            record(min(next_output, duration))
        # Always track sub-step maxima so an acute pulse is not hidden by reporting interval.
        i = n - 1
        total_now = water[i] / segment_volume_l * 1000.0
        diss_now = water[i] / capacities.water_l * 1000.0
        sed_now = sediment[i] / sediment_mass_kg * 1000.0
        if total_now > max_water_total[0]: max_water_total = (total_now, t)
        if diss_now > max_water_dissolved[0]: max_water_dissolved = (diss_now, t)
        if sed_now > max_sed[0]: max_sed = (sed_now, t)

    if series[-1]["time_d"] < duration - 1e-9:
        record(duration)

    final_water = sum(water)
    final_sed = sum(sediment)
    expected = initial_mass + cumulative_input
    accounted = final_water + final_sed + cumulative_outflow + cumulative_water_transform + cumulative_sed_transform + cumulative_volatilised
    error = expected - accounted
    error_fraction = 0.0 if expected == 0 else error / expected

    # UI downsampling only; endpoint calculations use full samples.
    if len(series) > 800:
        stride = max(1, math.ceil(len(series) / 800))
        display_series = series[::stride]
        if display_series[-1] != series[-1]: display_series.append(series[-1])
    else:
        display_series = series

    water_twa = _moving_twa(samples_diss, TWA_WINDOWS_DAYS)
    sed_twa = _moving_twa(samples_sed, TWA_WINDOWS_DAYS)
    aq_pnec = payload.get("aquatic_pnec_ug_l")
    sed_pnec = payload.get("sediment_pnec_ug_kg")

    warnings: list[str] = [
        "This is the EnviroChem TOXSWA process screen, not execution of the official FOCUS_TOXSWA kernel.",
        "User-defined hydrology is intentionally separate from standard FOCUS Step 3 scenario hydrology.",
        "The native sediment representation uses one active sediment layer per water segment; official TOXSWA uses depth-resolved sediment discretisation.",
    ]
    route = _route_info(payload["contaminant_group"])
    if route["applicability"] in {"limited", "not_quantitative", "component_based"}:
        warnings.append(route["regulatory_note"])
    if float(payload["freundlich_exponent"]) != 1.0:
        warnings.append("The native alpha screen currently uses a linear Kd approximation; the entered Freundlich exponent is retained for official-input readiness but is not applied natively.")
    if float(payload["koc_l_kg"]) > 30000:
        warnings.append("Koc exceeds 30,000 L/kg. Official FOCUS_TOXSWA requires the high-Koc sediment discretisation; treat the native one-layer sediment result as qualitative until the official run is performed.")
    if mode in {"lateral_drainage", "lateral_runoff"}:
        warnings.append("The native alpha screen converts lateral water concentration × lateral flux to chemical mass loading but does not yet add the lateral water flux to the transient hydrology. Use official MACRO/PRZM → TOXSWA for FOCUS Step 3.")
    if payload["water_transformation_mode"] == "separate_dissolved_only":
        warnings.append("Separate-process mode applies transformation to dissolved water-phase mass only. Hydrolysis/photolysis/biotic sub-processes are not yet split into independent native rate constants in this alpha build.")

    return {
        "model_key": "ENVIROCHEM_TOXSWA_PROCESS_SCREEN",
        "model_version": MODEL_VERSION,
        "mode": "adapted_process_screen",
        "official_equivalence": False,
        "contaminant_group_routing": {**route, "contaminant_group": payload["contaminant_group"]},
        "resolved_inputs": {
            "geometry": {
                "waterbody_type": payload["waterbody_type"], "length_m": length, "width_m": width, "water_depth_m": depth,
                "segments": n, "segment_length_m": dx, "segment_water_volume_m3": segment_volume_m3,
                "receiving_flow_m3_day": flow, "nominal_residence_time_days": (length * width * depth / flow if flow > 0 else None),
            },
            "sediment": {
                "active_depth_m": sediment_depth, "bulk_density_kg_m3": payload["sediment_bulk_density_kg_m3"],
                "porosity": payload["sediment_porosity"], "organic_carbon_fraction": payload["sediment_organic_carbon_fraction"],
                "sediment_kd_l_kg": capacities.sediment_kd_l_kg,
            },
            "water_partitioning": {
                "suspended_solids_mg_l": payload["suspended_solids_mg_l"],
                "suspended_solids_kd_l_kg": capacities.suspended_kd_l_kg,
                "dissolved_fraction_at_linear_equilibrium": capacities.water_dissolved_fraction,
            },
            "transformation": {
                "water_dt50_input_days": payload["water_dt50_days"], "water_dt50_at_system_temperature_days": water_dt50,
                "sediment_dt50_input_days": payload["sediment_dt50_days"], "sediment_dt50_at_system_temperature_days": sed_dt50,
                "reference_temperature_c": payload["transformation_reference_temperature_c"], "system_temperature_c": payload["water_temperature_c"],
                "activation_energy_kj_mol": payload["activation_energy_kj_mol"], "water_mode": payload["water_transformation_mode"],
            },
            "numerics": {
                "resolved_substep_days": dt, "advective_stability_limit_days": None if not math.isfinite(advective_dt) else advective_dt,
                "exchange_stability_limit_days": None if not math.isfinite(exchange_dt) else exchange_dt, "steps": steps,
            },
            "loading": {
                "mode": mode, "continuous_rate_mg_day": continuous_rate, "pulse_days": app_days, "pulse_masses_mg": pulse_masses,
                "loaded_segments": selected, "loaded_start_m": payload["loaded_start_m"], "loaded_end_m": payload["loaded_end_m"],
            },
        },
        "summary": {
            "global_max_pecsw_total_ug_l": max_water_total[0], "global_max_pecsw_total_time_d": max_water_total[1],
            "global_max_pecsw_dissolved_ug_l": max_water_dissolved[0], "global_max_pecsw_dissolved_time_d": max_water_dissolved[1],
            "global_max_pecsed_ug_kg": max_sed[0], "global_max_pecsed_time_d": max_sed[1],
            "twaecsw_dissolved_ug_l": water_twa, "twaecsed_ug_kg": sed_twa,
            "aquatic_rq_peak": (max_water_dissolved[0] / float(aq_pnec)) if aq_pnec else None,
            "sediment_rq_peak": (max_sed[0] / float(sed_pnec)) if sed_pnec else None,
        },
        "mass_balance": {
            "initial_mass_mg": initial_mass, "external_input_mg": cumulative_input,
            "final_water_mass_mg": final_water, "final_sediment_mass_mg": final_sed,
            "outflow_mass_mg": cumulative_outflow, "water_transformed_mg": cumulative_water_transform,
            "sediment_transformed_mg": cumulative_sed_transform, "volatilised_mg": cumulative_volatilised,
            "gross_water_to_sediment_exchange_mg": cumulative_exchange_to_sed,
            "gross_sediment_to_water_exchange_mg": cumulative_exchange_to_water,
            "closure_error_mg": error, "closure_error_fraction": error_fraction,
        },
        "time_series": display_series,
        "official_input_readiness": _official_readiness(payload),
        "warnings": warnings,
    }


def parse_official_summary(text: str) -> dict[str, Any]:
    """Parse useful endpoints from a FOCUS_TOXSWA .sum/report text.

    The parser is intentionally conservative: it records matched values and leaves
    unmatched fields null rather than fabricating an endpoint.
    """
    if not text or not text.strip():
        raise ValueError("TOXSWA summary text is empty")

    version = None
    kernel = None
    for pattern in [r"FOCUS\s+TOXSWA\s+version\s*:\s*([^\r\n]+)", r"FOCUS_TOXSWA\s+version\s*:\s*([^\r\n]+)"]:
        m = re.search(pattern, text, flags=re.I)
        if m:
            version = m.group(1).strip(); break
    m = re.search(r"TOXSWA\s+model\s+version\s*:\s*([^\r\n]+)", text, flags=re.I)
    if m: kernel = m.group(1).strip()

    water_global: float | None = None
    sed_global: float | None = None
    water_twa: dict[str, float] = {}
    sed_twa: dict[str, float] = {}
    context = None
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if "pec in water layer" in low or "exposure concentrations in water" in low:
            context = "water"
        elif "pec in sediment" in low or "exposure concentrations in sediment" in low:
            context = "sediment"
        if low.startswith("global max"):
            m = re.search(r"Global\s+max\s+([-+0-9.eE]+)", line, flags=re.I)
            if m:
                try:
                    value = float(m.group(1))
                    if context == "water" and water_global is None: water_global = value
                    elif context == "sediment" and sed_global is None: sed_global = value
                    elif water_global is None: water_global = value
                    elif sed_global is None: sed_global = value
                except ValueError:
                    pass
        m = re.search(r"TWAECsw[_\s-]*(\d+)[_\s-]*days?\s+([-+0-9.eE]+)", line, flags=re.I)
        if m:
            try: water_twa[m.group(1)] = float(m.group(2))
            except ValueError: pass
        m = re.search(r"TWAECsed[_\s-]*(\d+)[_\s-]*days?\s+([-+0-9.eE]+)", line, flags=re.I)
        if m:
            try: sed_twa[m.group(1)] = float(m.group(2))
            except ValueError: pass

    # Parse mass-balance labels where available without assuming a specific report layout.
    mass_terms: dict[str, float] = {}
    for label in ["MasWatLay", "MasSed", "MasTraWatLay", "MasTraSed", "MasVolWatLay", "MasDwnWatLay"]:
        matches = re.findall(rf"\b{re.escape(label)}\b[^\r\n]*?([-+0-9.eE]+)\s*$", text, flags=re.I | re.M)
        if matches:
            try: mass_terms[label] = float(matches[-1])
            except ValueError: pass

    warnings = []
    if water_global is None: warnings.append("No global maximum PECsw was confidently parsed from the supplied text.")
    if sed_global is None: warnings.append("No global maximum PECsed was confidently parsed from the supplied text.")
    if not water_twa: warnings.append("No TWAECsw values were confidently parsed from the supplied text.")

    return {
        "source_type": "FOCUS_TOXSWA_official_output_import",
        "focus_toxswa_version": version,
        "toxswa_kernel_version": kernel,
        "global_max_pecsw_ug_l": water_global,
        "global_max_pecsed_reported": sed_global,
        "twaecsw_ug_l": water_twa,
        "twaecsed_reported": sed_twa,
        "mass_terms_reported": mass_terms,
        "warnings": warnings,
    }


def raw_output_hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()
