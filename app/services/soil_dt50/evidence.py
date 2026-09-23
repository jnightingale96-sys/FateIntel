"""Turn a soil-DT50 provider result into an evidence-hub candidate.

Measured values are always preferred (the provider returns the EAWAG-SOIL Bayesian mean whenever the compound is in
the training set); a prediction is offered only as a labelled estimate. Nothing here selects a value for a model --
like every other candidate it goes through professional review.
"""

from __future__ import annotations

from typing import Any

from ..evidence_sources import EvidenceCandidate, _candidate_id
from . import CITATION


def to_evidence_candidate(
    result: dict[str, Any], *, chemical_name: str, cas_number: str | None = None, import_allowed: bool = True,
) -> dict[str, Any] | None:
    """FATE.SOIL_DT50 candidate from one ``DT50Result.to_dict()``; None unless the provider returned a value."""

    recommended = result.get("recommended")
    if result.get("status") != "ok" or not recommended:
        return None
    measured = str(recommended.get("basis", "")).startswith("measured")
    prediction = result.get("prediction") or {}
    experimental = result.get("experimental") or {}
    applicability = result.get("applicability") or {}
    persistence = result.get("persistence") or {}
    if measured:
        snippet = (
            f"measured mean DT50 {recommended['DT50_ref_days']} d across {experimental.get('n_half_lives', '?')} "
            f"EAWAG-SOIL half-lives (between-soil log sd {experimental.get('logDT50_sd_between_soils')})"
        )
    else:
        snippet = (
            f"PEPPER GPR predicted DT50 {recommended['DT50_ref_days']} d; 90% CI of the mean "
            f"{prediction.get('DT50_mean_90CI_days')}; single-soil 90% prediction interval "
            f"{prediction.get('DT50_single_soil_90PI_days')}"
        )
    notes = [
        f"basis: {recommended.get('basis')}; confidence: {recommended.get('confidence')}",
        f"max Tanimoto to training set {applicability.get('max_tanimoto')}",
        f"P(P) {persistence.get('p_P')} (screening flag {persistence.get('screening_flag_potential_P')})",
        "reference conditions: aerobic laboratory soil (OECD 307), ~20 C, ~pF2; primary disappearance of the parent, "
        "not mineralisation or field dissipation",
        *result.get("warnings", []),
        *(applicability.get("notes") or []),
    ]
    if not measured:
        notes.append(
            "MODEL ESTIMATE: no measured value in the training set. Not a regulatory (OECD-accepted) QSAR; use as a "
            "Tier 1 screen and prefer a measured OECD 307 value."
        )
    return EvidenceCandidate(
        candidate_id=_candidate_id("pepper_soil_dt50", result.get("smiles"), recommended["DT50_ref_days"], measured),
        source_key="pepper_soil_dt50", source_name="PEPPER soil GPR (Eawag/UZH) via FateIntel provider",
        source_record_id=result.get("smiles"), source_url=None, chemical_name=chemical_name, cas_number=cas_number,
        property_code="FATE.SOIL_DT50", endpoint_label="Soil degradation DT50",
        value=recommended["DT50_ref_days"], unit="days", qualifier="=", matrix="soil", temperature_c=20.0, ph=None,
        guideline="OECD 307 (aerobic laboratory soil), reference conditions",
        evidence_type="database_record" if measured else "model_prediction",
        publication_title="Confidently Uncertain: Probabilistic Machine Learning to Predict Soil Biotransformation Half-Lives",
        publication_year=2026, doi=None, pmid=None, pmcid=None, original_source=CITATION,
        rights_status="training_data_licence_to_confirm", import_allowed=import_allowed, needs_professional_review=True,
        extraction_status="structured_database_field" if measured else "model_output",
        snippet=snippet, notes=" | ".join(str(n) for n in notes if n),
    ).to_dict()
