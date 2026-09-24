"""Assessment workflow registry: which stages and screens apply for a region and a chemical group.

The app used to show every screen to every assessment. This registry says, for one (region, chemical group) pair,
which track(s) apply, the ordered stages of each, and which screens (modules) belong to it. The front end reads this
and shows only those, so for example a contaminated-land site model never appears in a pharmaceutical assessment,
and an EU-only refinement never appears in a Canadian one.

Nothing here decides a scientific or regulatory question. It only arranges what the rest of the code base already
implements or names:
  * a region's regulatory route text comes from `registry._regulatory_programme`, not restated here;
  * the external method a site assessment is handed to comes from `conceptual_site_model.EXTERNAL_ROUTES`;
  * "native screen applies" is `registry.DISCRETE_ORGANIC_GROUPS`; blocked groups are `NO_NATIVE_PATHWAY_GROUPS`.
Which groups offer the contaminated-land track is a product decision (see FAMILIES), taken from the contaminant
list in the founder's brief, not a regulatory claim. Where a region has no dedicated refinement, the stage says so
("not built") and nothing is invented for it.
"""

from __future__ import annotations

from typing import Any

from .conceptual_site_model import EXTERNAL_ROUTES, NOT_ESTABLISHED
from .registry import (
    CONTAMINANT_GROUPS, CONTAMINANT_TAXONOMY, DISCRETE_ORGANIC_GROUPS, NO_NATIVE_PATHWAY_GROUPS, _regulatory_programme,
)

USE_RELEASE = "use_release"
SITE = "site"

# region key -> what that region's flow contains. `refinement` names the region-specific refinement screens that exist
# in the app today; None means no dedicated refinement screen has been built for that region. EU, UK and Switzerland
# each get their own tab and their own regulatory-route text (registry._regulatory_programme), but still share the
# app's native FOCUS/water-sediment refinement suite (refinement: "eu") -- that sharing is a pre-existing product
# claim (see toxswa_surface_water.py's own EU/UK/US/CH applicability note), not something split apart here.
REGIONS: dict[str, dict[str, Any]] = {
    "EU": {"label": "European Union", "jurisdictions": ["EU"], "default": "EU", "refinement": "eu"},
    "UK": {"label": "United Kingdom", "jurisdictions": ["UK"], "default": "UK", "refinement": "eu"},
    "CH": {"label": "Switzerland", "jurisdictions": ["CH"], "default": "CH", "refinement": "eu"},
    "US": {"label": "United States", "jurisdictions": ["US"], "default": "US", "refinement": "us"},
    "CA": {"label": "Canada", "jurisdictions": ["CA"], "default": "CA", "refinement": None},
    "AU": {"label": "Australia", "jurisdictions": ["AU"], "default": "AU", "refinement": None},
    "NZ": {"label": "New Zealand", "jurisdictions": ["NZ"], "default": "NZ", "refinement": None},
    "JP": {"label": "Japan", "jurisdictions": ["JP"], "default": "JP", "refinement": None},
    "CN": {"label": "China", "jurisdictions": ["CN"], "default": "CN", "refinement": None},
    "KR": {"label": "South Korea", "jurisdictions": ["KR"], "default": "KR", "refinement": None},
    "IN": {"label": "India", "jurisdictions": ["IN"], "default": "IN", "refinement": None},
    # Norway shares the FOCUS refinement suite (refinement: "eu") -- confirmed 2026-09-23, not assumed: Mattilsynet
    # mandates FOCUS MACRO 5.5.4 for groundwater leaching and its own six-scenario surface-water selection is drawn
    # from FOCUS's own standard set (see registry._regulatory_programme's "NO" branch and the PEARL/PELMO/MACRO/
    # SWASH/TOXSWA/PRZM regions lists).
    "NO": {"label": "Norway", "jurisdictions": ["NO"], "default": "NO", "refinement": "eu"},
    "AE": {"label": "United Arab Emirates", "jurisdictions": ["AE"], "default": "AE", "refinement": None},
    "SA": {"label": "Saudi Arabia", "jurisdictions": ["SA"], "default": "SA", "refinement": None},
    "BR": {"label": "Brazil", "jurisdictions": ["BR"], "default": "BR", "refinement": None},
    "MX": {"label": "Mexico", "jurisdictions": ["MX"], "default": "MX", "refinement": None},
    "SG": {"label": "Singapore", "jurisdictions": ["SG"], "default": "SG", "refinement": None},
    "TW": {"label": "Taiwan", "jurisdictions": ["TW"], "default": "TW", "refinement": None},
    "ZA": {"label": "South Africa", "jurisdictions": ["ZA"], "default": "ZA", "refinement": None},
}

GROUP_LABELS: dict[str, str] = {
    "industrial_organic": "Industrial organic chemical",
    "pesticide": "Pesticide (plant protection)",
    "biocide": "Biocide",
    "human_pharmaceutical": "Human pharmaceutical",
    "veterinary_pharmaceutical": "Veterinary medicine",
    "personal_care_cosmetic": "Personal care or cosmetic ingredient",
    "detergent_cleaner": "Detergent or cleaner ingredient",
    "emerging_contaminant": "Other emerging contaminant",
    "pfas_persistent_mobile": "PFAS or other persistent, mobile substance",
    "hydrocarbon_solvent": "Petroleum hydrocarbon or solvent",
    "metal_inorganic": "Metal or metalloid",
    "pah": "Polycyclic aromatic hydrocarbon (PAH)",
    "legacy_pop_organic": "Legacy persistent organic pollutant (PCBs, dioxins, organochlorine pesticides)",
    "organotin": "Organotin",
    "polymer_microplastic": "Polymer or microplastic",
    "nanomaterial": "Nanomaterial",
    "uvcb_complex_substance": "Complex substance (UVCB)",
    "mixture_formulation": "Formulated mixture",
    "radionuclide": "Radionuclide",
    "contaminated_mixture": "Contaminated mixture or unknown site material",
}

# The chemical-group families shown when a user chooses "what is the chemical". `tracks` are the assessments that
# family can be taken through; the contaminated-land (SITE) track is offered only where the founder's brief listed the
# contaminant as a contaminated-land concern. `default_track` is the one opened first.
FAMILIES: list[dict[str, Any]] = [
    {"id": "pharma_personal_care", "label": "Pharmaceuticals and personal care",
     "groups": ["human_pharmaceutical", "veterinary_pharmaceutical", "personal_care_cosmetic"],
     "tracks": [USE_RELEASE], "default_track": USE_RELEASE},
    {"id": "industrial_consumer", "label": "Industrial, detergent and consumer chemicals",
     "groups": ["industrial_organic", "detergent_cleaner", "emerging_contaminant"],
     "tracks": [USE_RELEASE], "default_track": USE_RELEASE},
    {"id": "crop_protection", "label": "Pesticides and biocides",
     "groups": ["pesticide", "biocide"], "tracks": [USE_RELEASE], "default_track": USE_RELEASE},
    {"id": "pfas", "label": "PFAS",
     "groups": ["pfas_persistent_mobile"], "tracks": [USE_RELEASE, SITE], "default_track": USE_RELEASE},
    {"id": "metals", "label": "Metals and metalloids",
     "groups": ["metal_inorganic"], "tracks": [SITE, USE_RELEASE], "default_track": SITE},
    {"id": "legacy_persistent", "label": "Legacy persistent organics (PCBs, PAHs, organotins)",
     "groups": ["legacy_pop_organic", "pah", "organotin"], "tracks": [SITE, USE_RELEASE], "default_track": SITE},
    {"id": "fuels_solvents", "label": "Petroleum hydrocarbons and solvents",
     "groups": ["hydrocarbon_solvent"], "tracks": [SITE, USE_RELEASE], "default_track": SITE},
    {"id": "particulate", "label": "Polymers, microplastics and nanomaterials",
     "groups": ["polymer_microplastic", "nanomaterial"], "tracks": [USE_RELEASE], "default_track": USE_RELEASE},
    {"id": "complex", "label": "Complex substances and formulated mixtures",
     "groups": ["uvcb_complex_substance", "mixture_formulation"], "tracks": [USE_RELEASE], "default_track": USE_RELEASE},
    {"id": "not_modelled", "label": "Radionuclides and contaminated mixtures",
     "groups": ["radionuclide", "contaminated_mixture"], "tracks": [], "default_track": None},
]

# module id -> the screen it opens. `section` is the element id on the guided page.
MODULES: dict[str, dict[str, str]] = {
    "evidence": {"section": "evidence-data-hub", "label": "Evidence data"},
    "assessment": {"section": "assessment-flow", "label": "Assessment"},
    "plan": {"section": "regulatory-pathway", "label": "Regulatory route"},
    "results": {"section": "results", "label": "Results and report"},
    "water_sediment": {"section": "toxswa-surface-water", "label": "Water-sediment"},
    "pearl": {"section": "pearl-groundwater", "label": "FOCUS PEARL"},
    "us_models": {"section": "us-models-placeholder", "label": "US EPA models"},
    "envirodesign": {"section": "envirodesign", "label": "EnviroDesign"},
    "identification": {"section": "analytical-identification", "label": "Identification"},
    "kinetics": {"section": "degradation-kinetics", "label": "Applied Environmental Fate"},
    "tp_soil_fate": {"section": "tp-soil-fate", "label": "Soil transformation products"},
    "contaminated_land": {"section": "contaminated-land", "label": "Contaminated land"},
}

# Families whose site track also offers the soil degradation and transformation-product screens (organic contaminants only:
# not metals, and not PFAS, whose soil DT50 is not meaningful).
SITE_ORGANIC_FAMILIES = ("legacy_persistent", "fuels_solvents")

# Site-assessment receptor classes that have a named external method for at least one jurisdiction.
_RECEPTOR_CLASSES = ("human", "ecological", "groundwater", "surface_water")
_PARTIAL_KEY_MARKERS = ("NOT_MAPPED", "NOT_CONFIRMED", "PARTIAL", "NO_ERA", "NOT_YET")


class WorkflowError(ValueError):
    """Unknown region or chemical group."""


def _family_of(group: str) -> dict[str, Any]:
    for family in FAMILIES:
        if group in family["groups"]:
            return family
    raise WorkflowError(f"Chemical group {group!r} is not assigned to a family")


def reference() -> dict[str, Any]:
    """What a front end needs to build its region and chemical-group choosers."""
    return {
        "regions": [{"key": k, **{f: v[f] for f in ("label", "jurisdictions", "default")}} for k, v in REGIONS.items()],
        "families": [
            {
                "id": f["id"], "label": f["label"], "tracks": f["tracks"], "default_track": f["default_track"],
                "groups": [{"key": g, "label": GROUP_LABELS[g], "taxonomy": CONTAMINANT_TAXONOMY[g]["label"]} for g in f["groups"]],
            }
            for f in FAMILIES
        ],
        "modules": MODULES,
        "note": "Which groups offer the contaminated-land track is a product decision, not a regulatory claim.",
    }


def _default_scenario(group: str) -> str:
    return "agricultural_spray" if group == "pesticide" else "municipal_wastewater"


def _programme_stage(region: dict[str, Any], group: str, scenario: str | None) -> dict[str, Any]:
    programme = _regulatory_programme(region["default"], group, scenario or _default_scenario(group))
    partial = any(marker in programme["key"] for marker in _PARTIAL_KEY_MARKERS)
    return {
        "id": "route", "label": "Regulatory route", "module": "plan",
        "status": "partial" if partial else "available",
        "detail": f"{programme['name']}: {programme['scope']}",
        "programme_key": programme["key"],
        "note": "Only partly mapped for this region and group. The plan says what is missing." if partial else None,
    }


def _use_release_track(region: dict[str, Any], group: str, scenario: str | None) -> tuple[dict[str, Any], set[str]]:
    native = group in DISCRETE_ORGANIC_GROUPS
    modules = {"evidence", "assessment", "plan"}
    stages = [
        {"id": "identify", "label": "Identify the substance", "module": "evidence", "status": "available", "detail": None, "note": None},
        {"id": "use", "label": "Describe use and release", "module": "assessment", "status": "available", "detail": None, "note": None},
        _programme_stage(region, group, scenario),
    ]
    if native:
        modules.add("results")
        stages.append({"id": "screen", "label": "Native exposure screen", "module": "results", "status": "available",
                       "detail": "Tier 1 to 2 predicted environmental concentration screen", "note": None})
    else:
        stages.append({"id": "screen", "label": "Native exposure screen", "module": None, "status": "external_required",
                       "detail": None, "note": "No native fate screen is valid for this group. The regulatory route names the external model to use."})
    refinement = region["refinement"]
    if native and refinement == "eu":
        modules |= {"water_sediment", "pearl"}
        stages.append({"id": "refine", "label": "Refine", "module": "water_sediment", "status": "available",
                       "detail": "Water-sediment process screen and FOCUS PEARL groundwater refinement", "note": "Each screen still appears only when the chosen tier and release route allow it."})
    elif native and refinement == "us":
        modules.add("us_models")
        stages.append({"id": "refine", "label": "Refine", "module": "us_models", "status": "managed_external",
                       "detail": "US EPA models, structured and reviewed in FateIntel", "note": None})
    elif native:
        stages.append({"id": "refine", "label": "Refine", "module": None, "status": "not_built", "detail": None,
                       "note": f"No dedicated refinement screen is built for {region['label']}."})
    if native:
        modules |= {"envirodesign", "identification", "kinetics", "tp_soil_fate"}
        stages.append({"id": "tools", "label": "Structure, identification, kinetics and soil transformation-product tools", "module": "envirodesign",
                       "status": "available", "detail": None, "note": None})
    stages.append({"id": "review", "label": "Review and report", "module": "results" if native else "plan",
                   "status": "available", "detail": None, "note": None})
    return {"id": USE_RELEASE, "label": "Use and release assessment", "stages": stages}, modules


def _site_methods(region: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for jurisdiction in region["jurisdictions"]:
        for receptor in _RECEPTOR_CLASSES:
            found = EXTERNAL_ROUTES.get((jurisdiction, receptor))
            out.append({
                "jurisdiction": jurisdiction, "receptor": receptor,
                "route": found["route"] if found else NOT_ESTABLISHED,
                "named": bool(found),
            })
    return out


def _site_track(region: dict[str, Any], family: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    basis_note = {
        "metals": "Concentrations keep the basis they were reported on (total, dissolved, bioavailable). No conversion without a sourced fraction.",
        "legacy_persistent": "Persistent organic pollutant status is checked against the Stockholm Convention and EU lists. Not found is not the same as not a POP.",
        "pfas": "Koc alone is a weak guide to PFAS mobility. Plausibility prompts say so.",
    }.get(family["id"])
    methods = _site_methods(region)
    named = sum(1 for m in methods if m["named"])
    stages = [
        {"id": "identify", "label": "Identify the substance", "module": "evidence", "status": "available", "detail": None, "note": basis_note},
        {"id": "site_model", "label": "Build the site model (sources, pathways, receptors)", "module": "contaminated_land",
         "status": "available", "detail": "Potential linkages only. No exposure or risk is calculated.", "note": None},
        {"id": "methods", "label": "Regional method", "module": "contaminated_land",
         "status": "managed_external" if named else "not_established",
         "detail": f"{named} of {len(methods)} receptor and jurisdiction combinations have a named external method",
         "note": "FateIntel names the method and hands over. It does not reproduce the regulator's calculation."},
        {"id": "review", "label": "Review", "module": "contaminated_land", "status": "available", "detail": None, "note": None},
    ]
    modules = {"evidence", "contaminated_land"}
    if family["id"] in SITE_ORGANIC_FAMILIES:
        # Organic contaminants degrade in soil and can leave transformation products, which is what a site assessor
        # wants to know about aged contamination. The tools are screens, not the regulator's site method.
        stages.insert(2, {
            "id": "degradation", "label": "Soil degradation and transformation products", "module": "kinetics", "status": "available",
            "detail": "Fit a DT50 from residue data, then model transformation products in soil. Screening tools, not a regulatory site method.",
            "note": None,
        })
        modules |= {"kinetics", "tp_soil_fate"}
    return {"id": SITE, "label": "Contaminated-site assessment", "stages": stages, "methods": methods}, modules


def resolve_workflow(region_key: str, group: str, scenario: str | None = None) -> dict[str, Any]:
    """The tracks, stages and screens for one region and chemical group. Raises WorkflowError on unknown input."""
    region = REGIONS.get(region_key)
    if region is None:
        raise WorkflowError(f"Unknown region {region_key!r}. Known: {', '.join(REGIONS)}")
    if group not in CONTAMINANT_GROUPS:
        raise WorkflowError(f"Unknown chemical group {group!r}")
    family = _family_of(group)
    base = {
        "region": region_key, "region_label": region["label"], "jurisdictions": region["jurisdictions"],
        "group": group, "group_label": GROUP_LABELS[group], "family": family["id"], "family_label": family["label"],
    }
    if group in NO_NATIVE_PATHWAY_GROUPS:
        return {
            **base, "blocked": True, "tracks": [], "default_track": None, "modules": ["plan"],
            "hidden_modules": [{"module": m, "reason": "FateIntel does not model this group."} for m in MODULES if m != "plan"],
            "reason": "FateIntel does not model this group. The regulatory route page explains what to use instead.",
        }
    tracks: list[dict[str, Any]] = []
    modules: set[str] = set()
    for track_id in family["tracks"]:
        if track_id == USE_RELEASE:
            track, mods = _use_release_track(region, group, scenario)
        else:
            track, mods = _site_track(region, family)
        track["modules"] = [m for m in MODULES if m in mods]
        tracks.append(track)
        modules |= mods
    order = list(MODULES)
    hidden_reason = {
        "contaminated_land": "Contaminated-land assessment does not apply to this chemical group.",
        "water_sediment": "Water-sediment refinement exists for the EU, UK and Switzerland flow only.",
        "pearl": "FOCUS PEARL exists for the EU, UK and Switzerland flow only.",
        "us_models": "US EPA model workflows exist for the United States flow only.",
    }
    return {
        **base, "blocked": False, "tracks": tracks, "default_track": family["default_track"],
        "modules": [m for m in order if m in modules],
        "hidden_modules": [
            {"module": m, "reason": hidden_reason.get(m, "A native fate screen is not valid for this group, so this tool does not apply.")}
            for m in order if m not in modules
        ],
    }
