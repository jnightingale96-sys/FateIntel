"""Contaminated-land conceptual site model (source, pathway, receptor), fail-closed.

Structure only: it validates a site model, finds potential source-pathway-receptor linkages, and reports
which measurements are missing and which external assessment route applies. It quantifies NO risk, sets
no criteria and never states a receptor is safe: an absent linkage means "none identified", not "no risk".
The concept follows the UK LCRM conceptual site model / pollutant-linkage approach
(LEGACY_CONTAMINANTS_MATRIX_UK.md section 1); external routes only name tools the research confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .pathway_plausibility import (
    PropertyError, SubstanceProperties, evaluate_path, properties_from_dict, rules_metadata,
)
from .pops import pops_status
from .registry import CONTAMINANT_GROUPS, CONTAMINANT_TAXONOMY, NO_NATIVE_PATHWAY_GROUPS

SOURCE_KINDS = (
    "historic_industrial_activity", "landfill", "spill", "mining", "waste",
    "atmospheric_deposition", "contaminated_fill", "sludge_biosolids", "former_manufacturing",
)
MEDIA = ("soil", "groundwater", "surface_water", "sediment", "soil_gas", "air", "vegetation", "biota")
HUMAN_RECEPTORS = ("residents", "workers", "construction_workers", "children")
ECOLOGICAL_RECEPTORS = ("aquatic_organisms", "terrestrial_organisms", "livestock", "crops", "wildlife")
CONTROLLED_WATER_RECEPTORS = ("groundwater", "surface_water")
RECEPTORS = HUMAN_RECEPTORS + ECOLOGICAL_RECEPTORS + CONTROLLED_WATER_RECEPTORS

# Physical connectivity of each pathway: which nodes it can leave and reach. `direct_contact_ecological`
# is an addition to the founder's list so ecological receptors can be represented at all.
PATHWAY_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "ingestion": {
        "from": ("soil", "surface_water", "groundwater", "sediment", "vegetation", "biota"),
        "to": HUMAN_RECEPTORS + ("livestock", "wildlife"),
    },
    "dermal_contact": {
        "from": ("soil", "surface_water", "groundwater", "sediment"),
        "to": HUMAN_RECEPTORS,
    },
    "inhalation": {"from": ("air", "soil_gas", "soil"), "to": HUMAN_RECEPTORS},
    "soil_to_groundwater": {"from": ("soil",), "to": ("groundwater",)},
    "groundwater_to_surface_water": {"from": ("groundwater",), "to": ("surface_water",)},
    "runoff": {"from": ("soil",), "to": ("surface_water",)},
    "erosion": {"from": ("soil",), "to": ("sediment", "surface_water")},
    "volatilisation": {"from": ("soil", "groundwater", "surface_water"), "to": ("air", "soil_gas")},
    "plant_uptake": {"from": ("soil", "sediment"), "to": ("vegetation", "crops")},
    "food_chain_transfer": {
        "from": ("vegetation", "biota", "sediment", "surface_water", "crops"),
        "to": ("biota",) + HUMAN_RECEPTORS + ("livestock", "wildlife"),
    },
    "sediment_water_exchange": {"from": ("sediment", "surface_water"), "to": ("surface_water", "sediment")},
    "direct_contact_ecological": {
        "from": ("soil", "sediment", "surface_water"),
        "to": ("terrestrial_organisms", "aquatic_organisms", "wildlife"),
    },
}

# Only routes the research documents confirmed. Anything else is reported as not established.
_UK = "LEGACY_CONTAMINANTS_MATRIX_UK.md"
_US = "LEGACY_CONTAMINANTS_MATRIX_US.md"
_EU = "LEGACY_CONTAMINANTS_MATRIX_EU.md"
_T234 = "LEGACY_CONTAMINANTS_MATRIX_TIER234_AND_RADIONUCLIDES.md"
EXTERNAL_ROUTES: dict[tuple[str, str], dict[str, str]] = {
    ("UK", "human"): {"route": "CLEA-type human-health methodology (external); published values are limited (C4SLs for 6 substances, legacy SGVs)", "source": _UK},
    ("UK", "groundwater"): {"route": "Remedial Targets Methodology / ConSim (external)", "source": _UK},
    ("UK", "surface_water"): {"route": "EA surface-water pollution risk assessment and UK EQS (external)", "source": _UK},
    ("US", "human"): {"route": "EPA RAGS and Regional Screening Levels (external)", "source": _US},
    ("US", "ecological"): {"route": "ERAGS and Eco-SSLs (external; Eco-SSLs are not cleanup levels)", "source": _US},
    ("US", "surface_water"): {"route": "EPA aquatic-life water quality criteria and sediment benchmarks (external)", "source": _US},
    ("EU", "surface_water"): {"route": "WFD / EQS Directive standards (external)", "source": _EU},
    ("EU", "human"): {"route": "Member-State contaminated-land framework (no EU-wide regime; e.g. Germany BBodSchV, Netherlands target/intervention values)", "source": _EU},
    ("EU", "ecological"): {"route": "Member-State contaminated-land framework (no EU-wide regime)", "source": _EU},
    ("EU", "groundwater"): {"route": "Member-State contaminated-land framework (no EU-wide regime)", "source": _EU},
    ("CA", "human"): {"route": "FCSAP PQRA then DQRA staged risk assessment; CCME guidelines (external)", "source": _T234},
    ("CA", "ecological"): {"route": "FCSAP staged risk assessment; CCME guidelines (external)", "source": _T234},
    ("AU", "human"): {"route": "ASC NEPM Schedule B tiered assessment (HIL/EIL) (external)", "source": _T234},
    ("AU", "ecological"): {"route": "ASC NEPM Schedule B tiered assessment (HIL/EIL) (external)", "source": _T234},
    ("NZ", "human"): {"route": "NES-CS soil contaminants standard (planning-control regime, human health only) (external)", "source": _T234},
}
NOT_ESTABLISHED = "REGULATORY APPLICABILITY NOT ESTABLISHED (route not confirmed by the research for this jurisdiction and receptor)"


class ConceptualSiteModelError(ValueError):
    """Structurally invalid site model."""


@dataclass(frozen=True)
class Contaminant:
    name: str
    contaminant_group: str
    cas_number: str | None = None
    properties: SubstanceProperties | None = None  # sourced property values; see pathway_plausibility

    def __post_init__(self) -> None:
        if not (self.name or "").strip():
            raise ConceptualSiteModelError("Contaminant needs a name")
        if self.contaminant_group not in CONTAMINANT_GROUPS:
            raise ConceptualSiteModelError(f"Unknown contaminant_group {self.contaminant_group!r}")


@dataclass(frozen=True)
class Source:
    id: str
    kind: str
    release_media: tuple[str, ...]
    contaminants: tuple[Contaminant, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not (self.id or "").strip():
            raise ConceptualSiteModelError("Source needs an id")
        if self.kind not in SOURCE_KINDS:
            raise ConceptualSiteModelError(f"Unknown source kind {self.kind!r}")
        if not self.release_media or any(m not in MEDIA for m in self.release_media):
            raise ConceptualSiteModelError(f"Source {self.id}: release_media must be one or more of {MEDIA}")
        if not self.contaminants:
            raise ConceptualSiteModelError(f"Source {self.id}: at least one contaminant is required")


@dataclass(frozen=True)
class PathwayLink:
    pathway: str
    from_node: str
    to_node: str

    def __post_init__(self) -> None:
        rule = PATHWAY_RULES.get(self.pathway)
        if rule is None:
            raise ConceptualSiteModelError(f"Unknown pathway {self.pathway!r}")
        if self.from_node not in rule["from"]:
            raise ConceptualSiteModelError(f"{self.pathway} cannot start from {self.from_node!r}")
        if self.to_node not in rule["to"]:
            raise ConceptualSiteModelError(f"{self.pathway} cannot reach {self.to_node!r}")


@dataclass(frozen=True)
class ConceptualSiteModel:
    sources: tuple[Source, ...]
    receptors: tuple[str, ...]
    links: tuple[PathwayLink, ...]
    # medium -> names of contaminants for which a measured concentration is available in that medium
    measured: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ids = [s.id for s in self.sources]
        if not ids or len(set(ids)) != len(ids):
            raise ConceptualSiteModelError("Provide at least one source, with unique ids")
        bad = [r for r in self.receptors if r not in RECEPTORS]
        if bad:
            raise ConceptualSiteModelError(f"Unknown receptor(s) {bad}; allowed: {RECEPTORS}")
        for medium in self.measured:
            if medium not in MEDIA:
                raise ConceptualSiteModelError(f"Unknown medium {medium!r} in measured data")


def _receptor_class(receptor: str) -> str:
    if receptor in HUMAN_RECEPTORS:
        return "human"
    if receptor in ECOLOGICAL_RECEPTORS:
        return "ecological"
    return receptor  # groundwater / surface_water


def external_route(jurisdiction: str, receptor: str) -> dict[str, str]:
    found = EXTERNAL_ROUTES.get((jurisdiction, _receptor_class(receptor)))
    return found or {"route": NOT_ESTABLISHED, "source": ""}


def _simple_paths(links: tuple[PathwayLink, ...], start: str, receptors: set[str]) -> list[list[PathwayLink]]:
    """All simple node paths from `start` ending at a receptor node (start itself counts as a zero-length path)."""
    found: list[list[PathwayLink]] = []

    def walk(node: str, visited: set[str], trail: list[PathwayLink]) -> None:
        if node in receptors:
            found.append(list(trail))
        for link in links:
            if link.from_node == node and link.to_node not in visited:
                walk(link.to_node, visited | {link.to_node}, trail + [link])

    walk(start, {start}, [])
    return found


def assess(model: ConceptualSiteModel, jurisdiction: str) -> dict[str, Any]:
    """Map potential linkages, data gaps and external routes. Quantifies nothing."""
    receptor_nodes = set(model.receptors)
    linkages: list[dict[str, Any]] = []
    contaminant_flags: dict[tuple[str, str | None], dict[str, Any]] = {}
    reached_receptors: set[str] = set()
    used_links: set[PathwayLink] = set()
    sources_with_linkage: set[str] = set()

    for source in model.sources:
        for contaminant in source.contaminants:
            blocked = contaminant.contaminant_group in NO_NATIVE_PATHWAY_GROUPS
            flag_key = (contaminant.name, contaminant.cas_number)
            if flag_key not in contaminant_flags:
                contaminant_flags[flag_key] = pops_status(
                    cas_number=contaminant.cas_number, name=contaminant.name, jurisdiction=jurisdiction,
                )
            pops_summary = contaminant_flags[flag_key]["status"]
            for start in source.release_media:
                for path in _simple_paths(model.links, start, receptor_nodes):
                    receptor = path[-1].to_node if path else start
                    path_steps = [{"pathway": l.pathway, "from": l.from_node, "to": l.to_node} for l in path]
                    plausibility = [] if blocked else evaluate_path(
                        contaminant.name, contaminant.contaminant_group, contaminant.properties, path_steps, jurisdiction,
                    )
                    measured_here = contaminant.name in model.measured.get(start, ())
                    linkages.append({
                        "source_id": source.id,
                        "source_kind": source.kind,
                        "contaminant": contaminant.name,
                        "contaminant_group": contaminant.contaminant_group,
                        "taxonomy_letter": CONTAMINANT_TAXONOMY[contaminant.contaminant_group]["letter"],
                        "pops_status": pops_summary,
                        "release_medium": start,
                        "path": path_steps,
                        "plausibility": plausibility,
                        "receptor": receptor,
                        "receptor_class": _receptor_class(receptor),
                        "status": "POTENTIAL_LINKAGE_DATA_PRESENT" if measured_here else "POTENTIAL_LINKAGE_MEASUREMENT_MISSING",
                        "missing_data": [] if measured_here else [f"measured {contaminant.name} concentration in {start}"],
                        "native_assessment": "EXTERNAL MODEL REQUIRED / no native pathway" if blocked else "conceptual mapping only; no risk quantified",
                        "external_route": external_route(jurisdiction, receptor),
                    })
                    reached_receptors.add(receptor)
                    used_links.update(path)
                    sources_with_linkage.add(source.id)

    unreached = [r for r in model.receptors if r not in reached_receptors]
    unsupported = [l for l in model.links if l not in used_links]
    return {
        "jurisdiction": jurisdiction,
        "linkages": linkages,
        "contaminant_pops_flags": [
            {"contaminant": name, "cas_number": cas, **status}
            for (name, cas), status in contaminant_flags.items()
        ],
        "receptors_without_linkage": [
            {"receptor": r, "status": "NO_LINKAGE_IDENTIFIED",
             "note": "Not a finding of no risk: the model or the site investigation may be incomplete."}
            for r in unreached
        ],
        "sources_without_linkage": [s.id for s in model.sources if s.id not in sources_with_linkage],
        "unsupported_pathway_links": [
            {"pathway": l.pathway, "from": l.from_node, "to": l.to_node,
             "note": "Not connected to any source or receptor in this model."}
            for l in unsupported
        ],
        "summary": {
            "potential_linkages": len(linkages),
            "with_measured_data": sum(1 for x in linkages if x["status"] == "POTENTIAL_LINKAGE_DATA_PRESENT"),
            "measurement_gaps": sum(1 for x in linkages if x["missing_data"]),
            "receptors_without_linkage": len(unreached),
            "plausibility_questioned": sum(1 for x in linkages for r in x["plausibility"] if r["outcome"] == "QUESTIONS_RELEVANCE"),
            "plausibility_property_missing": sum(1 for x in linkages for r in x["plausibility"] if r["outcome"] == "PROPERTY_MISSING"),
        },
        "plausibility_rules": rules_metadata(),
        "disclaimer": (
            "Conceptual mapping only. No exposure, dose or risk is calculated and no assessment criteria are applied. "
            "Plausibility prompts use published screening definitions (see the rules and their sources) purely as "
            "prompts for review: they never remove a linkage."
        ),
    }


def model_from_dict(data: dict[str, Any]) -> ConceptualSiteModel:
    """Build a model from plain JSON. Any missing or malformed piece raises ConceptualSiteModelError."""
    try:
        sources = tuple(
            Source(
                id=s["id"], kind=s["kind"], release_media=tuple(s["release_media"]),
                contaminants=tuple(
                    Contaminant(c["name"], c["contaminant_group"], c.get("cas_number"),
                                properties_from_dict(c.get("properties")))
                    for c in s["contaminants"]
                ),
                description=s.get("description", ""),
            )
            for s in data["sources"]
        )
        links = tuple(PathwayLink(l["pathway"], l["from"], l["to"]) for l in data.get("links", []))
        measured = {m: tuple(names) for m, names in data.get("measured", {}).items()}
        return ConceptualSiteModel(sources=sources, receptors=tuple(data.get("receptors", [])), links=links, measured=measured)
    except (KeyError, TypeError) as exc:
        raise ConceptualSiteModelError(f"Malformed site model: {exc!r}") from exc
    except PropertyError as exc:
        raise ConceptualSiteModelError(str(exc)) from exc
