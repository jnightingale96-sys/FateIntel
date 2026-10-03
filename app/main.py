from __future__ import annotations
from contextlib import asynccontextmanager
from dataclasses import asdict
from io import BytesIO
import json
import math
import re
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
from time import perf_counter
from uuid import uuid4

import httpx

from typing import Any

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, SessionLocal, get_db, database_diagnostics
from .exceptions import (
    ChemicalIdentityError, EnviroChemError, ExternalDataSourceError,
    ReachReviewError, ReachSigningUnavailableError,
)
from .logging_config import configure_logging, request_id_context
from .version import APP_VERSION, BUILD_ID, DEFAULT_PORT, RELEASE_NAME
from .models import (
    Project, Chemical, ProjectChemical, Source, EvidenceRecord,
    SelectionSet, SelectionMember, ModelRun, RiskAssessment, AuditEvent, ModelWorkflow,
    ChemicalIdentitySnapshot, ChemicalAssessmentProfile, ModelRunIdentityBinding,
    OrchestratedAssessmentRecord, MSRawEvidenceFile, MSFeature,
    SiteModelRecord, MetalMeasurementRecord,
)
from .schemas import (
    ProjectCreate, IdentityResolveCreate, ChemicalIdentityConfirmCreate,
    ChemicalAssessmentProfileUpsert, EvidenceCreate, SelectionCalculate, SelectionLock,
    WWTPRunCreate, SorptionRunCreate, PharmaceuticalEmissionRunCreate,
    ActivitySimpleTreatRunCreate, WastewaterIrrigationComparisonCreate,
    AssessmentPlanCreate, HomeUseSummaryCreate,
    ModelWorkflowCreate, ModelWorkflowExecute, ModelWorkflowOutputImport, ModelWorkflowReview,
    RegulatoryPathwayCreate, VeterinaryPhaseICreate, VeterinaryAssessmentCreate,
    BiosolidsLandApplicationCreate, PlantUptakeScreenCreate,
    EnviroDesignAnalyseCreate, EnviroDesignCompareCreate, EnviroDesignPathwayCreate,
    TransformationPathwayPredictCreate,
    PearlGroundwaterRunCreate, ToxswaSurfaceWaterRunCreate,
    EvidenceSourceSearchCreate, EvidenceCandidateImportCreate,
    MultimediaFateRunCreate, CatchmentRiverRunCreate,
    ReachPnecPreviewCreate, ReachReviewBundleCreate,
    EquilibriumPartitioningPnecCreate, PbtPmtClassificationCreate,
    FishSecondaryPoisoningTerCreate, EarthwormSecondaryPoisoningTerCreate,
    JapanCsclPnecCreate,
    BeeRexFoliarContactCreate, BeeRexFoliarDietaryCreate, BeeRexSeedTreatmentCreate, BeeRexSoilTreatmentCreate,
    QuickScreenRiskCreate,
    USIndustrialExposureRunCreate, USExposureCompletenessCreate,
    DegradationKineticsAssessmentCreate,
    MSFeatureReviewUpdate,
    OrchestrationHarmoniseCreate, OrchestrationCompatibilityCreate,
    ModelPortCompatibilityCreate, RiskCharacterisationCreate,
    CrossJurisdictionComparisonCreate, OrchestrationPlanCreate,
    OrchestratedAssessmentCreate, OrchestratedAssessmentFinaliseCreate,
)
from .seed import seed
from .services.selection import calculate_selection, evidence_hash
from .services.wwtp import run_wwtp, run_activity_simpletreat
from .services.sorption import run_sorption_model
from .services.emission import run_pharmaceutical_emission
from .services.pharma_consumption import oecd_2025_registry, oecd_2025_lookup, oecd_live_query_url, fetch_oecd_live
from .services.irrigation import run_wastewater_irrigation_comparison
from .services.registry import FRAMEWORKS, CONTAMINANT_GROUPS, SCENARIOS, MODELS, build_assessment_plan
from .services.home_summary import build_home_use_summary
from .services.sds import parse_sds_text, build_coshh_draft
from .services.adapters import ADAPTER_CONTRACTS, prepare_workflow_manifest, normalise_imported_output, sha256_payload
from .services.veterinary import animal_profiles as veterinary_animal_profiles, GUIDANCE as VETERINARY_GUIDANCE, phase_i_decision, run_veterinary_assessment
from .services.biosolids import run_biosolids_land_application
from .services.plant_uptake import run_plant_uptake_screen
from .services.focus_installation import manifest as focus_manifest, installation_status as focus_installation_status
from .services.external_models import integration_catalog as external_integration_catalog, integration_profile as external_integration_profile, validate_external_model_output
from .services.external_execution import (
    EPA_EXECUTION_MODEL_KEYS, ExternalExecutionError, build_handoff_bundle,
    execute_configured_tool, external_tool_status, sha256_file,
)
from .services.envirodesign import manifest as envirodesign_manifest, browser_config as envirodesign_browser_config, analyse_structure, compare_candidates, pathway_retention
from .services.transformation_pathways import (
    provider_capabilities as transformation_provider_capabilities,
    predict_environmental_pathway,
)
from .services.envipath import (
    provider_capabilities as envipath_provider_capabilities,
    predict_pathway as predict_envipath_pathway,
    search_curated_pathways as search_envipath_curated_pathways,
)
from .services.analytical_identification import (
    identification_profile as build_identification_profile,
    known_transformation_products,
    source_registry as analytical_source_registry,
)
from .services.ms_evidence import (
    parse_mzml,
    sha256_of as ms_evidence_sha256,
    workbench_capabilities as ms_evidence_capabilities,
    MzMLParseError,
)
from .services.degradation_kinetics import (
    run_degradation_kinetics_assessment,
    KineticFitError,
)
from .services.pearl_groundwater import manifest as pearl_manifest, focus_scenario_manifest, run_pearl_groundwater_screen
from .services.toxswa_surface_water import manifest as toxswa_manifest, route_recommendation as toxswa_route_recommendation, run_process_screen as run_toxswa_process_screen, parse_official_summary as parse_toxswa_official_summary, raw_output_hash as toxswa_raw_output_hash
from .services.multimedia_fate import run_multimedia_fate_screen
from .services.river_network import run_catchment_river_network
from .services.us_exposure import (
    manifest as us_exposure_manifest,
    source_catalogue as us_exposure_source_catalogue,
    scenario_catalogue as us_exposure_scenario_catalogue,
    scenario_by_key as us_exposure_scenario_by_key,
    assess_completeness as assess_us_exposure_completeness,
    run_industrial_exposure_screen,
)
from .services.evidence_sources import source_registry as evidence_source_registry, endpoint_catalog as evidence_endpoint_catalog, get_source as get_evidence_source, search_sources as search_evidence_sources, candidate_import_policy, candidate_provenance_hash
from .services.identity import (
    core_identity_hash, identity_conflicts, identity_matches_query,
    local_identity_candidate, normalise_identifier, resolve_pubchem_identity,
    validate_identity_candidate,
)
from .services.global_regulatory import (
    frameworks as global_frameworks, change_watch as global_change_watch,
    endpoint_checklist as global_endpoint_checklist, filter_frameworks,
    get_framework as get_global_framework, recommend_regulatory_pathway,
    research_status as global_research_status,
)
from .services.orchestration import (
    orchestration_manifest, semantic_contract_catalogue, harmonise_quantity,
    check_endpoint_compatibility, model_port_compatibility, characterise_risk,
    compare_jurisdictional_results, build_tier_sequence, build_assessment_record,
    record_hash as orchestration_record_hash,
)
from .services.specialist_groups import specialist_substance_group_requirements
from .reach.exporter import (
    BundleVerificationError, MAX_BUNDLE_BYTES, REVIEW_SCHEMA,
    build_review_bundle, verify_review_bundle,
)
from .reach.pnec import SUPPORTED_AQUATIC_ENDPOINTS, derive_pnec
from .reach.signing import (
    SigningError, read_private_key_file, signing_available,
)
from .services.equilibrium_partitioning import (
    derive_pnec_sediment_from_water, derive_pnec_soil_from_water,
)
from .services.pbt_pmt_classifier import classify_pbt_and_vpvb, classify_pmt_and_vpvm
from .services.eu_birds_mammals import fish_secondary_poisoning_ter, earthworm_secondary_poisoning_ter
from .services.japan_cscl import derive_pnec_japan_cscl
from .services.beerex import (
    foliar_spray_contact_rq, foliar_spray_dietary_rq, seed_treatment_dietary_rq, soil_treatment_dietary_rq,
)
from .services.quick_screen import screen_chemical_risk, QuickScreenInputError

BASE_DIR = Path(__file__).resolve().parent
logger = configure_logging(settings.log_level, settings.log_format)


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    logger.info(
        "application_started version=%s environment=%s database_backend=%s",
        APP_VERSION,
        settings.envirochem_environment,
        settings.database_backend,
    )
    try:
        yield
    finally:
        engine.dispose()
        logger.info("application_stopped version=%s", APP_VERSION)

app = FastAPI(
    title="FateIntel",
    version=APP_VERSION,
    description="Evidence-led, cross-jurisdiction environmental fate and tiered risk-assessment platform.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

from .services.soil_dt50.api import router as soil_dt50_router  # noqa: E402  (imports no heavy dependency)

app.include_router(soil_dt50_router, prefix="/api/providers")

from .services.biowin_dt50 import router as biowin_dt50_router  # noqa: E402

app.include_router(biowin_dt50_router, prefix="/api/providers")

from .services.oasis_soil_dt50 import router as oasis_soil_dt50_router  # noqa: E402

app.include_router(oasis_soil_dt50_router, prefix="/api/providers")

from .services.nite_ready_biodegradability import router as nite_ready_biodegradability_router  # noqa: E402

app.include_router(nite_ready_biodegradability_router, prefix="/api/providers")

from .services.tp_soil_fate import router as tp_soil_fate_router  # noqa: E402

app.include_router(tp_soil_fate_router, prefix="/api")

from .services.opera_local import router as opera_router  # noqa: E402

app.include_router(opera_router, prefix="/api/providers")


@app.exception_handler(EnviroChemError)
async def envirochem_exception_handler(request: Request, exc: EnviroChemError):
    request_id = request_id_context.get()
    logger.warning(
        "application_error code=%s path=%s message=%s",
        exc.error_code,
        request.url.path,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error": {"code": exc.error_code, "details": exc.details},
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.middleware("http")
async def request_tracing(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "").strip()
    request_id = supplied[:64] if supplied and supplied.replace("-", "").isalnum() else uuid4().hex
    token = request_id_context.set(request_id)
    started = perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        elapsed_ms = (perf_counter() - started) * 1000
        log_method = logger.debug if request.url.path in {"/health", "/api/health", "/api/ready"} else logger.info
        log_method(
            "request_completed method=%s path=%s status=%s duration_ms=%.3f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
    except Exception:
        logger.exception(
            "request_failed method=%s path=%s duration_ms=%.3f",
            request.method,
            request.url.path,
            (perf_counter() - started) * 1000,
        )
        raise
    finally:
        request_id_context.reset(token)


@app.middleware("http")
async def disable_browser_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-EnviroChem-Build"] = BUILD_ID
    response.headers["X-FateIntel-Build"] = BUILD_ID
    return response

@app.get("/api/build")
def build_information():
    return {
        "application": RELEASE_NAME,
        "build_id": BUILD_ID,
        "version": app.version,
        "runtime_port_configurable": True,
        "default_port": DEFAULT_PORT,
        "configured_port": settings.envirochem_port,
        "environment": settings.envirochem_environment,
        "database_backend": settings.database_backend,
        "request_tracing": True,
        "structured_logging": settings.log_format,
        "new_interface": True,
        "generic_chemical_assessment": True,
        "transformation_pathway_prediction": True,
        "reach_review_bundles": True,
        "provenance_explorer": True,
        "reviewed_home_profile_binding": True,
        "immutable_model_run_identity_binding": True,
        "us_exposure_foundations": True,
        "us_groundwater_leaching_screen": True,
        "epa_execution_bridge": True,
        "official_output_file_hashing": True,
        "tier_safe_water_sediment_routing": True,
        "alpha4_tier_orchestration": True,
        "semantic_model_compatibility": True,
        "cross_jurisdiction_comparison": True,
        "immutable_assessment_records": True,
        "navigation": ["Guided Assessment", "Chemical Identity + Reviewed Profile", "Tier Orchestration", "Human Pharma Influent", "Evidence Data Hub", "Tier 1–2 Results", "Transformation Pathways", "Catchment River Network", "Multimedia Fate", "US Exposure Foundations", "SPIN Dependency Workspace", "FOCUS MACRO", "GREAT-ER", "TOXSWA Surface Water", "EU FOCUS PEARL", "EnviroDesign", "Veterinary ERA", "Global Framework Navigator", "REACH Review Bundles", "Expert Workspace"],
    }


@app.get("/api/model-runs/{model_run_id}/identity-binding")
def model_run_identity_binding(model_run_id: int, db: Session = Depends(get_db)):
    run = db.get(ModelRun, model_run_id)
    if run is None:
        raise HTTPException(404, "Model run not found")
    binding = db.scalar(
        select(ModelRunIdentityBinding).where(
            ModelRunIdentityBinding.model_run_id == model_run_id
        )
    )
    if binding is None:
        raise HTTPException(
            409,
            "This historical model run predates immutable identity binding and could not be backfilled",
        )
    snapshot = json.loads(binding.snapshot_json)
    return {
        "model_run_id": binding.model_run_id,
        "project_id": binding.project_id,
        "chemical_id": binding.chemical_id,
        "identity_snapshot_id": binding.identity_snapshot_id,
        "identity_hash": binding.identity_hash,
        "preferred_name": snapshot.get("preferred_name"),
        "cas_number": snapshot.get("cas_number"),
        "inchikey": snapshot.get("inchikey"),
        "molecular_formula": snapshot.get("molecular_formula"),
        "molecular_weight_g_mol": snapshot.get("molecular_weight_g_mol"),
        "substance_form": snapshot.get("substance_form"),
        "source_key": snapshot.get("source_key"),
        "source_record_id": snapshot.get("source_record_id"),
        "identity_confirmed_at": (
            binding.identity_snapshot.confirmed_at.isoformat()
            if binding.identity_snapshot.confirmed_at
            else None
        ),
        "bound_at": binding.bound_at.isoformat(),
    }


def audit(
    db: Session,
    project_id: int | None,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: dict,
) -> None:
    db.add(AuditEvent(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        payload_json=json.dumps(payload, sort_keys=True),
    ))


def _profile_dict(profile: ChemicalAssessmentProfile | None) -> dict | None:
    if profile is None:
        return None
    return {
        "id": profile.id,
        "project_id": profile.project_id,
        "chemical_id": profile.chemical_id,
        "profile_origin": profile.profile_origin,
        "review_status": profile.review_status,
        "ionisation_class": profile.ionisation_class,
        "log_kow": profile.log_kow,
        "pkaa": profile.pkaa,
        "pkab": profile.pkab,
        "water_solubility_mg_l": profile.water_solubility_mg_l,
        "vapour_pressure_pa": profile.vapour_pressure_pa,
        "soil_dt50_days": profile.soil_dt50_days,
        "wwtp_biodegradation_fraction": profile.wwtp_biodegradation_fraction,
        "wwtp_primary_sludge_fraction": profile.wwtp_primary_sludge_fraction,
        "wwtp_secondary_sludge_fraction": profile.wwtp_secondary_sludge_fraction,
        "wwtp_volatilisation_fraction": profile.wwtp_volatilisation_fraction,
        "source_summary": profile.source_summary,
        "provenance": json.loads(profile.provenance_json or "{}"),
        "reviewer_confirmation": profile.reviewer_confirmation,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _ensure_assessment_profile(
    db: Session,
    project_id: int,
    chemical: Chemical,
) -> ChemicalAssessmentProfile:
    profile = db.scalar(select(ChemicalAssessmentProfile).where(
        ChemicalAssessmentProfile.project_id == project_id,
        ChemicalAssessmentProfile.chemical_id == chemical.id,
    ))
    if profile is not None:
        return profile
    is_benchmark = chemical.cas_number == "298-46-4" and chemical.substance_form == "parent"
    if is_benchmark:
        profile = ChemicalAssessmentProfile(
            project_id=project_id,
            chemical_id=chemical.id,
            profile_origin="protected_carbamazepine_benchmark",
            review_status="reviewed",
            ionisation_class="neutral",
            log_kow=2.45,
            pkaa=13.9,
            water_solubility_mg_l=17.7,
            soil_dt50_days=40.0,
            wwtp_biodegradation_fraction=0.07209507243873131,
            wwtp_primary_sludge_fraction=0.007868396178849157,
            wwtp_secondary_sludge_fraction=0.0028491031300824854,
            wwtp_volatilisation_fraction=1.6806982721404515e-8,
            source_summary="Protected Carbamazepine verification fixture from the supplied reviewed sorption and Activity SimpleTreat workbooks.",
            provenance_json=json.dumps({"fixture": "carbamazepine_workbook_9box", "transferable": False}, sort_keys=True),
            reviewer_confirmation=True,
        )
    else:
        profile = ChemicalAssessmentProfile(
            project_id=project_id,
            chemical_id=chemical.id,
            profile_origin="draft",
            review_status="draft",
            provenance_json="{}",
            reviewer_confirmation=False,
        )
    db.add(profile)
    db.flush()
    return profile


def _chemical_dict(chemical: Chemical) -> dict:
    snapshot = None
    if chemical.id:
        # Filled by endpoints that have a session when provenance is required.
        snapshot = None
    return {
        "id": chemical.id,
        "preferred_name": chemical.preferred_name,
        "cas_number": chemical.cas_number,
        "molecular_formula": chemical.molecular_formula,
        "molecular_weight_g_mol": chemical.molecular_weight_g_mol,
        "smiles": chemical.smiles,
        "inchikey": chemical.inchikey,
        "substance_form": chemical.substance_form,
        "review_status": chemical.review_status,
        "identity_snapshot": snapshot,
    }


def _profile_hash(profile: ChemicalAssessmentProfile) -> str:
    payload = _profile_dict(profile) or {}
    payload.pop("updated_at", None)
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validated_run_profile(
    db: Session,
    profile_id: int | None,
    project_id: int,
    chemical_id: int,
) -> ChemicalAssessmentProfile | None:
    if profile_id is None:
        return None
    profile = db.get(ChemicalAssessmentProfile, profile_id)
    if profile is None:
        raise HTTPException(404, "Assessment profile not found")
    if profile.project_id != project_id or profile.chemical_id != chemical_id:
        raise HTTPException(422, "Assessment profile does not belong to the selected project and chemical")
    if profile.review_status != "reviewed" or not profile.reviewer_confirmation:
        raise HTTPException(422, "Assessment profile has not been reviewed and confirmed")
    return profile

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/health", include_in_schema=False)
@app.get("/api/health")
def health():
    database = database_diagnostics()
    return {
        "status": "ok" if database["status"] == "ok" else "degraded",
        "version": app.version,
        "build_id": BUILD_ID,
        "environment": settings.envirochem_environment,
        "checks": {"database": database},
    }


@app.get("/api/ready")
def readiness():
    database = database_diagnostics()
    payload = {
        "status": "ready" if database["status"] == "ok" else "not_ready",
        "version": app.version,
        "checks": {"database": database},
    }
    return JSONResponse(payload, status_code=200 if database["status"] == "ok" else 503)


@app.post("/api/identities/resolve")
def resolve_identity(payload: IdentityResolveCreate, db: Session = Depends(get_db)):
    chemicals = list(db.scalars(select(Chemical).order_by(Chemical.id)).all())
    local = next((row for row in chemicals if identity_matches_query(row, payload.query)), None)
    if local is not None:
        return {"candidate": local_identity_candidate(local, query=payload.query, query_mode=payload.query_mode), "requires_confirmation": True}
    try:
        candidate = resolve_pubchem_identity(payload.query, payload.query_mode)
    except ValueError as exc:
        raise ChemicalIdentityError(str(exc), details={"query_mode": payload.query_mode}) from exc
    except (httpx.HTTPError, KeyError, TypeError) as exc:
        raise ExternalDataSourceError(
            "PubChem identity resolution is temporarily unavailable",
            details={"source": "pubchem", "failure_type": exc.__class__.__name__},
        ) from exc
    return {"candidate": candidate, "requires_confirmation": True}


_CAS_FORMAT_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


@app.post("/api/quick-screen/risk")
def quick_screen_risk(payload: QuickScreenRiskCreate, db: Session = Depends(get_db)):
    """Screen any chemical's aquatic risk in one call: resolves identity exactly like /api/identities/resolve
    (local record first, then PubChem), then runs app.services.quick_screen.screen_chemical_risk. Always
    returns 200 with `screening_estimate: true` -- this is a fast triage signal, never a reviewed assessment;
    see quick_screen.py's own module docstring for the full discipline this deliberately trades away.

    Real-chemical fallback (added 2026-10-01): PubChem only resolves single-structure compounds, so a real
    UVCB/mixture/complex-substance CAS number (confirmed example: 68585-34-2) is rejected by PubChem outright
    -- but US EPA ECOTOX is indexed by CAS number independently of PubChem and can have real data for exactly
    that kind of substance (confirmed: 8 real candidates for 68585-34-2). Rejecting the whole screen because
    PubChem alone couldn't confirm a single structure would throw away real, usable hazard data. So: when the
    query is CAS-shaped and PubChem fails, this falls back to screening by the bare CAS number with identity
    explicitly marked unconfirmed, rather than refusing outright. A name/SMILES query that PubChem can't
    resolve still 422s -- ECOTOX's local import has no name-only lookup (see ecotox_local.py), so there is no
    real data path left to fall back to, and guessing a name would be exactly the invented-chemistry this app
    never does.
    """

    chemicals = list(db.scalars(select(Chemical).order_by(Chemical.id)).all())
    local = next((row for row in chemicals if identity_matches_query(row, payload.query)), None)
    identity_confirmed = True
    if local is not None:
        identity = {"preferred_name": local.preferred_name, "cas_number": local.cas_number, "smiles": local.smiles}
    else:
        try:
            candidate = resolve_pubchem_identity(payload.query, payload.query_mode)
            identity = {"preferred_name": candidate["preferred_name"], "cas_number": candidate.get("cas_number"), "smiles": candidate.get("smiles")}
        except ValueError as exc:
            if payload.query_mode == "cas" and _CAS_FORMAT_RE.match(payload.query.strip()):
                # A real CAS number PubChem can't resolve to one structure (UVCB/mixture/complex substance) --
                # fall back to a CAS-only screen rather than refusing outright. See the route docstring.
                identity = {"preferred_name": payload.query.strip(), "cas_number": payload.query.strip(), "smiles": None}
                identity_confirmed = False
            else:
                raise ChemicalIdentityError(str(exc), details={"query_mode": payload.query_mode}) from exc
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise ExternalDataSourceError(
                "PubChem identity resolution is temporarily unavailable",
                details={"source": "pubchem", "failure_type": exc.__class__.__name__},
            ) from exc

    try:
        result = screen_chemical_risk(
            chemical_name=identity["preferred_name"], cas_number=identity["cas_number"], smiles=identity["smiles"],
            release_kg_year=payload.release_kg_year, scenario=payload.scenario,
            maximum_daily_dose_mg=payload.maximum_daily_dose_mg,
            market_penetration_fraction=payload.market_penetration_fraction,
            population=payload.population, wastewater_l_person_day=payload.wastewater_l_person_day,
            dilution_factor=payload.dilution_factor,
        )
    except (QuickScreenInputError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    identity["identity_confirmed"] = identity_confirmed
    if not identity_confirmed:
        identity["note"] = (
            "PubChem could not resolve this CAS number to a single confirmed structure (common for UVCB "
            "substances, mixtures and complex substances). Screened by CAS number against US EPA ECOTOX "
            "directly -- hazard results below may still be real and usable, but the name shown is the raw "
            "query, not a confirmed substance name, and structure-dependent results (sediment/soil PNEC, the "
            "secondary-poisoning flag) are unlikely to find anything without a resolvable name."
        )
    return {"identity": identity, **result}


@app.post("/api/chemicals/from-resolved-identity", status_code=201)
def confirm_resolved_identity(payload: ChemicalIdentityConfirmCreate, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    candidate = dict(payload.candidate)
    try:
        validate_identity_candidate(candidate)
    except ValueError as exc:
        raise ChemicalIdentityError(str(exc), details={"stage": "confirmation"}) from exc
    candidate["core_identity_hash"] = candidate.get("core_identity_hash") or core_identity_hash(candidate)

    supplied_cas = normalise_identifier("cas", candidate.get("cas_number")) or None
    supplied_inchikey = normalise_identifier("inchikey", candidate.get("inchikey")) or None
    by_cas = db.scalar(select(Chemical).where(Chemical.cas_number == supplied_cas)) if supplied_cas else None
    by_inchikey = db.scalar(select(Chemical).where(Chemical.inchikey == supplied_inchikey)) if supplied_inchikey else None
    if by_cas is not None and by_inchikey is not None and by_cas.id != by_inchikey.id:
        raise HTTPException(409, "CAS number and InChIKey resolve to different stored chemical records")
    chemical = by_cas or by_inchikey
    created = chemical is None
    if chemical is None:
        chemical = Chemical(
            preferred_name=str(candidate["preferred_name"])[:200],
            cas_number=supplied_cas[:50] if supplied_cas else None,
            molecular_formula=str(candidate["molecular_formula"])[:100],
            molecular_weight_g_mol=float(candidate["molecular_weight_g_mol"]),
            smiles=str(candidate["smiles"]),
            inchikey=supplied_inchikey[:100],
            substance_form=str(candidate.get("substance_form") or "parent")[:100],
            review_status="identity_confirmed",
        )
        db.add(chemical)
        db.flush()
    else:
        conflicts = identity_conflicts(chemical, candidate)
        if conflicts:
            raise HTTPException(
                409,
                "Confirmed identity conflicts with stored " + ", ".join(conflicts),
            )

    snapshot = db.scalar(select(ChemicalIdentitySnapshot).where(ChemicalIdentitySnapshot.chemical_id == chemical.id))
    if snapshot is None:
        snapshot = ChemicalIdentitySnapshot(
            chemical_id=chemical.id,
            source_key=str(candidate["source_key"]),
            source_record_id=str(candidate.get("source_record_id"))[:250] if candidate.get("source_record_id") else None,
            source_url=candidate.get("source_url"),
            query_text=str(candidate.get("query_text") or "")[:500] or None,
            query_mode=str(candidate.get("query_mode") or "")[:50] or None,
            identity_hash=str(candidate["identity_hash"]),
            snapshot_json=json.dumps(candidate, sort_keys=True),
        )
        db.add(snapshot)
        db.flush()

    membership = db.get(ProjectChemical, {"project_id": project.id, "chemical_id": chemical.id})
    if membership is None:
        db.add(ProjectChemical(project_id=project.id, chemical_id=chemical.id))
    profile = _ensure_assessment_profile(db, project.id, chemical)
    audit(db, project.id, "chemical", chemical.id, "identity_confirmed", {
        "identity_hash": candidate["identity_hash"],
        "source_key": candidate["source_key"],
        "created": created,
    })
    db.commit()
    chemical_out = _chemical_dict(chemical)
    chemical_out["identity_snapshot"] = {
        "source_key": snapshot.source_key,
        "source_record_id": snapshot.source_record_id,
        "source_url": snapshot.source_url,
        "identity_hash": snapshot.identity_hash,
        "confirmed_at": snapshot.confirmed_at.isoformat(),
    }
    return {"chemical": chemical_out, "profile": _profile_dict(profile), "created": created}


@app.get("/api/projects/{project_id}/chemicals/{chemical_id}/assessment-profile")
def get_assessment_profile(project_id: int, chemical_id: int, db: Session = Depends(get_db)):
    membership = db.get(ProjectChemical, {"project_id": project_id, "chemical_id": chemical_id})
    if membership is None:
        raise HTTPException(404, "Chemical is not attached to the selected project")
    chemical = db.get(Chemical, chemical_id)
    profile = _ensure_assessment_profile(db, project_id, chemical)
    db.commit()
    return _profile_dict(profile)


@app.put("/api/projects/{project_id}/chemicals/{chemical_id}/assessment-profile")
def update_assessment_profile(
    project_id: int,
    chemical_id: int,
    payload: ChemicalAssessmentProfileUpsert,
    db: Session = Depends(get_db),
):
    membership = db.get(ProjectChemical, {"project_id": project_id, "chemical_id": chemical_id})
    if membership is None:
        raise HTTPException(404, "Chemical is not attached to the selected project")
    chemical = db.get(Chemical, chemical_id)
    profile = _ensure_assessment_profile(db, project_id, chemical)
    values = payload.model_dump(exclude={"provenance"})
    for key, value in values.items():
        if key == "reviewer_confirmation":
            continue
        setattr(profile, key, value)
    profile.provenance_json = json.dumps(payload.provenance, sort_keys=True)
    profile.reviewer_confirmation = payload.reviewer_confirmation
    profile.review_status = "reviewed" if payload.reviewer_confirmation else "draft"
    benchmark_values = {
        "log_kow": 2.45,
        "water_solubility_mg_l": 17.7,
        "soil_dt50_days": 40.0,
        "wwtp_biodegradation_fraction": 0.07209507243873131,
        "wwtp_primary_sludge_fraction": 0.007868396178849157,
        "wwtp_secondary_sludge_fraction": 0.0028491031300824854,
        "wwtp_volatilisation_fraction": 1.6806982721404515e-8,
    }
    benchmark_match = (
        chemical.cas_number == "298-46-4"
        and chemical.substance_form == "parent"
        and payload.ionisation_class == "neutral"
        and all(
            getattr(payload, key) is not None and abs(float(getattr(payload, key)) - expected) <= max(1e-12, abs(expected) * 1e-10)
            for key, expected in benchmark_values.items()
        )
    )
    profile.profile_origin = "protected_carbamazepine_benchmark" if benchmark_match else (
        "reviewed_custom" if payload.reviewer_confirmation else "draft"
    )
    audit(db, project_id, "chemical_assessment_profile", profile.id, "updated", {
        "chemical_id": chemical_id,
        "review_status": profile.review_status,
        "profile_origin": profile.profile_origin,
    })
    db.commit()
    return _profile_dict(profile)


@app.get("/api/projects/{project_id}/chemicals/{chemical_id}/guided-readiness")
def guided_readiness(
    project_id: int,
    chemical_id: int,
    release: str = Query(default="wastewater"),
    db: Session = Depends(get_db),
):
    chemical = db.get(Chemical, chemical_id)
    membership = db.get(ProjectChemical, {"project_id": project_id, "chemical_id": chemical_id})
    if chemical is None or membership is None:
        raise HTTPException(404, "Chemical is not attached to the selected project")
    profile = _ensure_assessment_profile(db, project_id, chemical)
    required = [
        "ionisation_class", "log_kow", "wwtp_biodegradation_fraction",
        "wwtp_primary_sludge_fraction", "wwtp_secondary_sludge_fraction",
        "wwtp_volatilisation_fraction",
    ]
    if profile.ionisation_class == "acid":
        required.append("pkaa")
    if profile.ionisation_class == "base":
        required.append("pkab")
    if release in {"biosolids", "irrigation"}:
        required.append("soil_dt50_days")
    if release == "irrigation":
        required.append("water_solubility_mg_l")
    missing = [key for key in required if getattr(profile, key) is None]
    if profile.review_status != "reviewed" or not profile.reviewer_confirmation:
        missing.insert(0, "reviewer_confirmation")
    mode = "supplied_workbook_9box_preset" if (
        profile.profile_origin == "protected_carbamazepine_benchmark"
        and chemical.cas_number == "298-46-4"
        and chemical.substance_form == "parent"
    ) else "custom_screening"
    db.commit()
    return {
        "ready": not missing,
        "missing": list(dict.fromkeys(missing)),
        "wwtp_model_mode": mode,
        "chemical": _chemical_dict(chemical),
        "profile": _profile_dict(profile),
        "warnings": [
            "The Carbamazepine 9-box fixture is never transferred to another identity."
            if mode == "custom_screening" else
            "This project is using the protected Carbamazepine verification fixture."
        ],
    }


def _json_record(value: str, *, label: str) -> object:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReachReviewError(
            f"Stored {label} is not valid JSON and cannot be exported",
            details={"record": label},
        ) from exc


def _reach_evidence_snapshot(row: EvidenceRecord) -> dict:
    return {
        "id": row.id,
        "chemical_id": row.chemical_id,
        "property_code": row.property_code,
        "evidence_type": row.evidence_type,
        "original_value": row.original_value,
        "original_unit": row.original_unit,
        "endpoint_kind": row.endpoint_kind,
        "test_guideline": row.test_guideline,
        "reliability_score": row.reliability_score,
        "representative_group_key": row.representative_group_key,
        "include_by_default": row.include_by_default,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "source": {
            "id": row.source.id,
            "source_type": row.source.source_type,
            "title": row.source.title,
            "organisation": row.source.organisation,
            "publication_year": row.source.publication_year,
            "identifier": row.source.identifier,
            "url": row.source.url,
            "access_date": row.source.access_date,
        },
    }


def _reach_model_run_snapshot(row: ModelRun) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "chemical_id": row.chemical_id,
        "model_key": row.model_key,
        "model_version": row.model_version,
        "scenario_name": row.scenario_name,
        "status": row.status,
        "input": _json_record(row.input_json, label=f"model run {row.id} input"),
        "output": _json_record(row.output_json, label=f"model run {row.id} output"),
        "assumptions": _json_record(row.assumptions_json, label=f"model run {row.id} assumptions"),
        "evidence_hash": row.evidence_hash,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _build_reach_review_record(
    db: Session,
    payload: ReachReviewBundleCreate,
) -> dict:
    project = db.get(Project, payload.project_id)
    chemical = db.get(Chemical, payload.chemical_id)
    membership = db.get(ProjectChemical, {
        "project_id": payload.project_id,
        "chemical_id": payload.chemical_id,
    })
    if project is None or chemical is None or membership is None:
        raise ReachReviewError("Chemical is not attached to the selected project")
    profile = _validated_run_profile(
        db,
        payload.assessment_profile_id,
        payload.project_id,
        payload.chemical_id,
    )
    if profile is None:
        raise ReachReviewError("A reviewed assessment profile is required")
    identity = db.scalar(select(ChemicalIdentitySnapshot).where(
        ChemicalIdentitySnapshot.chemical_id == chemical.id,
    ))
    if identity is None:
        raise ReachReviewError(
            "A confirmed identity snapshot is required before preparing a REACH review bundle"
        )

    evidence_rows = list(db.scalars(select(EvidenceRecord).where(
        EvidenceRecord.id.in_(payload.selected_evidence_ids)
    )).all())
    evidence_by_id = {row.id: row for row in evidence_rows}
    missing_evidence = [item for item in payload.selected_evidence_ids if item not in evidence_by_id]
    if missing_evidence:
        raise ReachReviewError(
            "One or more selected evidence records do not exist",
            details={"missing_evidence_ids": missing_evidence},
        )
    wrong_chemical_evidence = [
        row.id for row in evidence_rows if row.chemical_id != payload.chemical_id
    ]
    if wrong_chemical_evidence:
        raise ReachReviewError(
            "Selected evidence does not belong to the selected chemical",
            details={"evidence_ids": wrong_chemical_evidence},
        )

    critical = evidence_by_id[payload.pnec.critical_evidence_id]
    endpoint_type = SUPPORTED_AQUATIC_ENDPOINTS.get(critical.property_code)
    if endpoint_type is None:
        raise ReachReviewError(
            "Critical PNEC evidence must use ECOTOX.AQUATIC.LC50, EC50, NOEC or EC10",
            details={
                "critical_evidence_id": critical.id,
                "property_code": critical.property_code,
            },
        )
    if critical.endpoint_kind:
        normalised_kind = re.sub(r"[^A-Z0-9]", "", critical.endpoint_kind.upper())
        if normalised_kind != endpoint_type:
            raise ReachReviewError(
                "Critical evidence endpoint_kind conflicts with its aquatic property code",
                details={
                    "critical_evidence_id": critical.id,
                    "property_code": critical.property_code,
                    "endpoint_kind": critical.endpoint_kind,
                },
            )
    try:
        pnec = derive_pnec(
            endpoint_value=critical.original_value,
            endpoint_unit=critical.original_unit,
            endpoint_type=endpoint_type,
            assessment_factor=payload.pnec.assessment_factor,
            assessment_factor_rationale=payload.pnec.assessment_factor_rationale,
            guidance_reference=payload.pnec.guidance_reference,
            target_compartment=payload.pnec.target_compartment,
        )
    except ValueError as exc:
        raise ReachReviewError(str(exc), details={"critical_evidence_id": critical.id}) from exc
    pnec["critical_endpoint"].update({
        "evidence_id": critical.id,
        "property_code": critical.property_code,
        "endpoint_kind": critical.endpoint_kind,
        "test_guideline": critical.test_guideline,
        "source_id": critical.source_id,
    })

    model_rows: list[ModelRun] = []
    if payload.selected_model_run_ids:
        model_rows = list(db.scalars(select(ModelRun).where(
            ModelRun.id.in_(payload.selected_model_run_ids)
        )).all())
        model_by_id = {row.id: row for row in model_rows}
        missing_runs = [item for item in payload.selected_model_run_ids if item not in model_by_id]
        if missing_runs:
            raise ReachReviewError(
                "One or more selected model runs do not exist",
                details={"missing_model_run_ids": missing_runs},
            )
        invalid_runs = [
            row.id for row in model_rows
            if row.project_id != payload.project_id
            or row.chemical_id != payload.chemical_id
            or row.status != "completed"
        ]
        if invalid_runs:
            raise ReachReviewError(
                "Selected model runs must be completed and belong to the selected project and chemical",
                details={"model_run_ids": invalid_runs},
            )

    prepared_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile_data = _profile_dict(profile) or {}
    profile_data["profile_hash"] = _profile_hash(profile)
    return {
        "schema": REVIEW_SCHEMA,
        "schema_version": "1.0",
        "prepared_at": prepared_at,
        "release": {"version": APP_VERSION, "build_id": BUILD_ID},
        "scope": {
            "kind": "reach_preparation_review_bundle",
            "submission_ready": False,
            "iuclid_format": False,
            "purpose": "evidence review and controlled hand-off before authoritative dossier preparation",
        },
        "project": {
            "id": project.id,
            "name": project.name,
            "jurisdiction": project.jurisdiction,
            "purpose": project.purpose,
        },
        "chemical": {
            "id": chemical.id,
            "preferred_name": chemical.preferred_name,
            "cas_number": chemical.cas_number,
            "molecular_formula": chemical.molecular_formula,
            "molecular_weight_g_mol": chemical.molecular_weight_g_mol,
            "smiles": chemical.smiles,
            "inchikey": chemical.inchikey,
            "substance_form": chemical.substance_form,
            "identity_hash": identity.identity_hash,
            "identity_source": {
                "source_key": identity.source_key,
                "source_record_id": identity.source_record_id,
                "source_url": identity.source_url,
                "confirmed_at": identity.confirmed_at.isoformat(),
            },
        },
        "assessment_profile": profile_data,
        "pnec_derivation": pnec,
        "evidence": [
            _reach_evidence_snapshot(evidence_by_id[item])
            for item in payload.selected_evidence_ids
        ],
        "model_runs": [
            _reach_model_run_snapshot({row.id: row for row in model_rows}[item])
            for item in payload.selected_model_run_ids
        ],
        "review": {
            "reviewer_name": payload.reviewer_name.strip(),
            "reviewer_role": payload.reviewer_role.strip(),
            "confirmed_at": prepared_at,
            "statement": (
                "The reviewer confirmed the identity, reviewed assessment profile, selected "
                "evidence, selected model runs and explicit assessment-factor rationale for "
                "preparation use. This confirmation does not assert IUCLID or submission readiness."
            ),
        },
    }


@app.get("/api/reach/review-bundles/capabilities")
def reach_review_bundle_capabilities():
    return {
        "format": "envirochem-reach-review",
        "format_version": "1.0",
        "boundary": "NOT_IUCLID_NOT_SUBMISSION_READY",
        "pnec_compartments": ["freshwater"],
        "concentration_units": ["ng/L", "µg/L", "mg/L", "g/L"],
        "signing": {
            "modes": ["unsigned", "rsa"],
            "algorithm": "rsa-pss-sha256",
            "cryptography_available": signing_available(),
            "private_key_configured": settings.reach_manifest_private_key_path is not None,
            "silent_fallback": False,
        },
        "requirements": [
            "confirmed identity snapshot",
            "reviewed and confirmed assessment profile",
            "stored aquatic ecotoxicity evidence",
            "explicit assessment factor, rationale and reference",
            "reviewer confirmation",
        ],
    }


@app.post("/api/reach/pnec/derive")
def preview_reach_pnec(payload: ReachPnecPreviewCreate):
    try:
        return derive_pnec(**payload.model_dump())
    except ValueError as exc:
        raise ReachReviewError(str(exc)) from exc


# --- Sediment/soil PNEC (equilibrium partitioning), PBT/PMT classification, secondary poisoning -------------------
# These three reviewer-input calculation modules (app/services/equilibrium_partitioning.py,
# pbt_pmt_classifier.py, eu_birds_mammals.py) existed before this wiring but had no API route, matching the
# same "built but not yet exposed" pattern the OASIS/NITE/OPERA providers went through. None of these derive or
# guess an input on the reviewer's behalf; every route 422s with the module's own message on an invalid input.

@app.post("/api/pnec/sediment-from-water")
def derive_sediment_pnec(payload: EquilibriumPartitioningPnecCreate):
    try:
        return asdict(derive_pnec_sediment_from_water(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/pnec/soil-from-water")
def derive_soil_pnec(payload: EquilibriumPartitioningPnecCreate):
    try:
        return asdict(derive_pnec_soil_from_water(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/pbt-pmt/classify")
def classify_pbt_pmt(payload: PbtPmtClassificationCreate):
    """Runs both the PBT/vPvB (REACH Annex XIII) and PMT/vPvM (CLP Annex I 4.4.2) classifications from one
    reviewer-supplied substance record, since most of their inputs (persistence half-lives, toxicity/CLP
    classification flags) are shared -- only bioaccumulation (BCF) vs. mobility (log Koc) differ."""

    data = payload.model_dump()
    try:
        pbt_vpvb = classify_pbt_and_vpvb(
            half_life_days=data["half_life_days"], bcf_l_per_kg=data["bcf_l_per_kg"],
            noec_or_ec10_mg_l=data["noec_or_ec10_mg_l"],
            carcinogenic_category_1a_1b=data["carcinogenic_category_1a_1b"],
            germ_cell_mutagen_category_1a_1b=data["germ_cell_mutagen_category_1a_1b"],
            reproductive_toxicant_category_1a_1b_2=data["reproductive_toxicant_category_1a_1b_2"],
            stot_re_category_1_2=data["stot_re_category_1_2"], substance_group=data["substance_group"],
        )
        pmt_vpvm = classify_pmt_and_vpvm(
            half_life_days=data["half_life_days"], log_koc=data["log_koc"],
            noec_or_ec10_mg_l=data["noec_or_ec10_mg_l"],
            carcinogenic_category_1a_1b=data["carcinogenic_category_1a_1b"],
            germ_cell_mutagen_category_1a_1b=data["germ_cell_mutagen_category_1a_1b"],
            reproductive_toxicant_category_1a_1b_2=data["reproductive_toxicant_category_1a_1b_2"],
            stot_re_category_1_2=data["stot_re_category_1_2"],
            endocrine_disruptor_category_1=data["endocrine_disruptor_category_1"], substance_group=data["substance_group"],
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"pbt_vpvb": pbt_vpvb, "pmt_vpvm": pmt_vpvm}


@app.post("/api/secondary-poisoning/fish")
def fish_secondary_poisoning(payload: FishSecondaryPoisoningTerCreate):
    try:
        return fish_secondary_poisoning_ter(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/secondary-poisoning/earthworm")
def earthworm_secondary_poisoning(payload: EarthwormSecondaryPoisoningTerCreate):
    try:
        return earthworm_secondary_poisoning_ter(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/pnec/japan-cscl")
def derive_japan_cscl_pnec(payload: JapanCsclPnecCreate):
    try:
        return asdict(derive_pnec_japan_cscl(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


# --- Tri-agency (US EPA/PMRA/CADPR) Bee-REX Tier 1 exposure screen (app/services/beerex.py) -----------------------

@app.post("/api/bee-rex/foliar-spray/contact")
def bee_rex_foliar_contact(payload: BeeRexFoliarContactCreate):
    try:
        return asdict(foliar_spray_contact_rq(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/bee-rex/foliar-spray/dietary")
def bee_rex_foliar_dietary(payload: BeeRexFoliarDietaryCreate):
    try:
        return asdict(foliar_spray_dietary_rq(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/bee-rex/seed-treatment/dietary")
def bee_rex_seed_treatment(payload: BeeRexSeedTreatmentCreate):
    try:
        return asdict(seed_treatment_dietary_rq(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/bee-rex/soil-treatment/dietary")
def bee_rex_soil_treatment(payload: BeeRexSoilTreatmentCreate):
    try:
        return asdict(soil_treatment_dietary_rq(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/reach/review-bundles")
def create_reach_review_bundle(
    payload: ReachReviewBundleCreate,
    db: Session = Depends(get_db),
):
    record = _build_reach_review_record(db, payload)
    private_key_pem = None
    if payload.signing_mode == "rsa":
        if settings.reach_manifest_private_key_path is None:
            raise ReachSigningUnavailableError(
                "RSA signing was requested but REACH_MANIFEST_PRIVATE_KEY_PATH is not configured"
            )
        try:
            private_key_pem = read_private_key_file(settings.reach_manifest_private_key_path)
        except SigningError as exc:
            raise ReachSigningUnavailableError(str(exc)) from exc
    try:
        bundle = build_review_bundle(
            record,
            exporter_version=APP_VERSION,
            signing_mode=payload.signing_mode,
            private_key_pem=private_key_pem,
        )
    except SigningError as exc:
        raise ReachSigningUnavailableError(str(exc)) from exc
    except ValueError as exc:
        raise ReachReviewError(str(exc)) from exc

    audit(db, payload.project_id, "reach_review_bundle", bundle.manifest_sha256, "exported", {
        "chemical_id": payload.chemical_id,
        "assessment_profile_id": payload.assessment_profile_id,
        "selected_evidence_ids": payload.selected_evidence_ids,
        "selected_model_run_ids": payload.selected_model_run_ids,
        "critical_evidence_id": payload.pnec.critical_evidence_id,
        "manifest_sha256": bundle.manifest_sha256,
        "bundle_sha256": bundle.bundle_sha256,
        "signing_mode": bundle.signing_mode,
        "key_fingerprint_sha256": bundle.key_fingerprint_sha256,
        "boundary": "NOT_IUCLID_NOT_SUBMISSION_READY",
    })
    db.commit()
    slug = re.sub(r"[^a-z0-9]+", "-", record["chemical"]["preferred_name"].casefold()).strip("-")
    filename = f"fateintel-reach-review-{slug or 'chemical'}.zip"
    return StreamingResponse(
        BytesIO(bundle.data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-EnviroChem-Manifest-SHA256": bundle.manifest_sha256,
            "X-EnviroChem-Bundle-SHA256": bundle.bundle_sha256,
            "X-EnviroChem-Signing-Mode": bundle.signing_mode,
            "X-EnviroChem-Submission-Status": "NOT_IUCLID_NOT_SUBMISSION_READY",
            "X-FateIntel-Manifest-SHA256": bundle.manifest_sha256,
            "X-FateIntel-Bundle-SHA256": bundle.bundle_sha256,
            "X-FateIntel-Signing-Mode": bundle.signing_mode,
            "X-FateIntel-Submission-Status": "NOT_IUCLID_NOT_SUBMISSION_READY",
        },
    )


@app.post("/api/reach/review-bundles/verify")
async def verify_uploaded_reach_review_bundle(
    bundle: UploadFile = File(...),
    public_key: UploadFile | None = File(default=None),
):
    data = await bundle.read(MAX_BUNDLE_BYTES + 1)
    await bundle.close()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ReachReviewError("Bundle exceeds the 25 MiB verification limit")
    public_key_pem = None
    if public_key is not None:
        public_key_pem = await public_key.read(1024 * 1024 + 1)
        await public_key.close()
        if len(public_key_pem) > 1024 * 1024:
            raise ReachReviewError("Public key exceeds the 1 MiB verification limit")
    try:
        return verify_review_bundle(data, public_key_pem=public_key_pem)
    except (BundleVerificationError, SigningError) as exc:
        raise ReachReviewError(str(exc)) from exc


@app.get("/api/evidence-sources")
def list_evidence_sources():
    return {
        "sources": evidence_source_registry(),
        "endpoint_catalog": evidence_endpoint_catalog(),
        "rule": "Automated retrieval creates evidence candidates only. No value becomes a modelling input until it is reviewed and explicitly selected.",
    }


@app.get("/api/evidence-sources/{source_key}")
def evidence_source_detail(source_key: str):
    try:
        return get_evidence_source(source_key)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/evidence-sources/search")
def search_evidence_source_data(payload: EvidenceSourceSearchCreate):
    unknown = [key for key in payload.source_keys if key not in {x["key"] for x in evidence_source_registry()}]
    if unknown:
        raise HTTPException(400, f"Unknown evidence sources: {', '.join(unknown)}")
    return search_evidence_sources(
        chemical_name=payload.chemical_name,
        cas_number=payload.cas_number,
        source_keys=payload.source_keys,
        endpoint_codes=payload.endpoint_codes,
        limit_per_source=payload.limit_per_source,
        include_open_access_full_text=payload.include_open_access_full_text,
        molecular_weight_g_mol=payload.molecular_weight_g_mol,
        smiles=payload.smiles,
    )


@app.post("/api/evidence-sources/import-candidate", status_code=201)
def import_evidence_candidate(payload: EvidenceCandidateImportCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Project not found")
    chemical = db.get(Chemical, payload.chemical_id)
    if chemical is None:
        raise HTTPException(404, "Chemical not found")
    membership = db.get(ProjectChemical, {"project_id": payload.project_id, "chemical_id": payload.chemical_id})
    if membership is None:
        raise HTTPException(422, "Evidence cannot be staged until the chemical is attached to the selected project")

    candidate = dict(payload.candidate)
    candidate_cas = str(candidate.get("cas_number") or "").strip()
    candidate_name = "".join(character for character in str(candidate.get("chemical_name") or "").casefold() if character.isalnum())
    target_name = "".join(character for character in chemical.preferred_name.casefold() if character.isalnum())
    if candidate_cas:
        if not chemical.cas_number or candidate_cas != chemical.cas_number:
            raise HTTPException(422, "Evidence candidate CAS does not match the selected chemical identity")
    elif not candidate_name or candidate_name != target_name:
        raise HTTPException(422, "Evidence candidate name does not match the selected chemical identity")
    source_key = str(candidate.get("source_key"))
    try:
        source_manifest = get_evidence_source(source_key)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    permitted, policy_message = candidate_import_policy(source_key, payload.rights_asserted)
    if not permitted:
        raise HTTPException(403, policy_message)
    if candidate.get("import_allowed") is False:
        raise HTTPException(403, "The retrieved candidate is marked as non-importable by its source adapter.")

    try:
        original_value = float(candidate["value"])
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(400, "Candidate must contain a numeric value") from exc
    if original_value <= 0:
        raise HTTPException(400, "Candidate value must be positive")

    source_title = candidate.get("publication_title") or candidate.get("original_source") or source_manifest["name"]
    source_identifier = candidate.get("doi") or candidate.get("pmid") or candidate.get("source_record_id")
    source_type = "machine_extracted_literature" if source_key == "europe_pmc" else "external_database_annotation"
    source = Source(
        source_type=source_type,
        title=str(source_title)[:500],
        organisation=source_manifest.get("owner"),
        publication_year=candidate.get("publication_year"),
        identifier=str(source_identifier)[:250] if source_identifier else None,
        url=candidate.get("source_url") or source_manifest.get("homepage"),
        access_date=datetime.now(timezone.utc).date().isoformat(),
    )
    db.add(source)
    db.flush()

    provenance_hash = candidate_provenance_hash(candidate)
    note_parts = [
        f"Imported from FateIntel evidence candidate {candidate.get('candidate_id') or provenance_hash[:24]}.",
        f"Source key: {source_key}; rights status: {candidate.get('rights_status') or source_manifest.get('commercial_status')}.",
        f"Extraction status: {candidate.get('extraction_status', 'external_candidate')}.",
        f"Candidate SHA-256: {provenance_hash}.",
        policy_message,
        "Machine-extracted/aggregated evidence is never selected automatically; verify the original study and endpoint context.",
    ]
    if candidate.get("matrix"):
        note_parts.append(f"Matrix candidate: {candidate['matrix']}.")
    if candidate.get("qualifier") and candidate.get("qualifier") != "=":
        note_parts.append(f"Original qualifier: {candidate['qualifier']}.")
    if candidate.get("snippet"):
        note_parts.append("Extraction context: " + str(candidate["snippet"])[:1000])
    if payload.review_notes:
        note_parts.append("Reviewer note: " + payload.review_notes)

    representative_group_key = payload.representative_group_key or f"{source_key}:{candidate.get('source_record_id') or provenance_hash[:16]}:{candidate.get('property_code')}"
    evidence = EvidenceRecord(
        chemical_id=payload.chemical_id,
        source_id=source.id,
        property_code=str(candidate["property_code"]),
        evidence_type=str(candidate.get("evidence_type") or "machine_extracted_candidate"),
        original_value=original_value,
        original_unit=str(candidate["unit"]),
        soil_type=candidate.get("matrix") if candidate.get("matrix") in {"soil", "manure", "activated_sludge", "water_sediment", "sediment", "surface_water"} else None,
        soil_ph=candidate.get("ph"),
        temperature_c=candidate.get("temperature_c"),
        endpoint_kind=candidate.get("endpoint_label"),
        test_guideline=candidate.get("guideline"),
        reliability_score=payload.reliability_score,
        representative_group_key=representative_group_key,
        include_by_default=False,
        notes=" ".join(note_parts),
    )
    db.add(evidence)
    db.flush()
    audit(db, payload.project_id, "evidence", evidence.id, "candidate_imported", {
        "chemical_id": payload.chemical_id,
        "source_key": source_key,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_hash": provenance_hash,
        "scientist_reviewed": payload.scientist_reviewed,
        "rights_asserted": payload.rights_asserted,
        "include_by_default": False,
    })
    db.commit()
    return {
        "id": evidence.id,
        "source_id": source.id,
        "candidate_hash": provenance_hash,
        "include_by_default": False,
        "review_required": True,
        "message": "Candidate stored in the evidence review queue. It is not yet a selected modelling value.",
    }



@app.get("/api/frameworks")
def list_frameworks():
    return FRAMEWORKS


@app.get("/api/contaminant-groups")
def list_contaminant_groups():
    return CONTAMINANT_GROUPS


@app.get("/api/scenarios")
def list_scenarios():
    return SCENARIOS


@app.get("/api/pops/status")
def pops_status_lookup(cas_number: str | None = None, name: str | None = None, jurisdiction: str | None = None):
    from .services import pops
    if jurisdiction is not None and jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    return pops.pops_status(cas_number=cas_number, name=name, jurisdiction=jurisdiction)


@app.get("/api/pops/reference")
def pops_reference():
    from .services import pops
    return {"metadata": pops.reference_metadata(), "substance_count": len(pops._reference()["entries"])}


@app.get("/api/chemicals/{chemical_id}/pops-status")
def chemical_pops_status(chemical_id: int, jurisdiction: str | None = None, db: Session = Depends(get_db)):
    from .services import pops
    chemical = db.get(Chemical, chemical_id)
    if chemical is None:
        raise HTTPException(404, "Chemical not found")
    if jurisdiction is not None and jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    return pops.pops_status(
        cas_number=chemical.cas_number, name=chemical.preferred_name, jurisdiction=jurisdiction,
    )


@app.get("/api/workflow/reference")
def workflow_reference():
    from .services import workflow_registry
    return workflow_registry.reference()


@app.get("/api/workflow")
def workflow(region: str, group: str, scenario: str | None = None):
    """Tracks, stages and screens for a region and chemical group. Arranges existing routes; decides nothing."""
    from .services import workflow_registry
    try:
        return workflow_registry.resolve_workflow(region, group, scenario)
    except workflow_registry.WorkflowError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/conceptual-site-model/reference")
def conceptual_site_model_reference():
    from .services import conceptual_site_model as csm
    from .services import metals, pathway_plausibility
    from .services.registry import CONTAMINANT_TAXONOMY
    return {
        "source_kinds": csm.SOURCE_KINDS, "media": csm.MEDIA, "receptors": csm.RECEPTORS,
        "pathways": {k: {"from": v["from"], "to": v["to"]} for k, v in csm.PATHWAY_RULES.items()},
        "contaminant_groups": [
            {"key": g, "label": CONTAMINANT_TAXONOMY[g]["label"], "letter": CONTAMINANT_TAXONOMY[g]["letter"]}
            for g in CONTAMINANT_GROUPS
        ],
        "metal_elements": metals.METAL_METALLOID_ELEMENTS,
        "property_specs": {k: label for k, (label, _) in pathway_plausibility.PROPERTY_SPECS.items()},
        "measurement": {
            "bases": [b for b in metals.BASES], "media": metals.MEDIA, "origins": metals.ORIGINS,
            "water_units": list(metals._WATER_TO_UG_L), "solid_units": list(metals._SOLID_TO_MG_KG),
        },
    }


def _site_model_row(db: Session, project_id: int, site_model_id: int) -> SiteModelRecord:
    row = db.get(SiteModelRecord, site_model_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(404, "Site model not found for this project")
    return row


def _site_model_summary(row: SiteModelRecord) -> dict[str, Any]:
    return {"id": row.id, "project_id": row.project_id, "name": row.name, "jurisdiction": row.jurisdiction,
            "created_at": row.created_at.isoformat() if row.created_at else None}


def _merged_site_model(db: Session, row: SiteModelRecord):
    from .services import conceptual_site_model as csm
    from .services.site_records import merge_measured
    model = csm.model_from_dict(json.loads(row.model_json))
    measurements = db.query(MetalMeasurementRecord).filter(MetalMeasurementRecord.project_id == row.project_id).all()
    return merge_measured(model, measurements)


def _apply_measurement(row: MetalMeasurementRecord, m: Any, site_medium: str | None) -> None:
    row.element, row.value, row.unit, row.basis, row.medium = m.element, m.value, m.unit, m.basis, m.medium
    row.weight_basis, row.source, row.origin = m.weight_basis, m.source, m.origin
    row.oxidation_state, row.species, row.method, row.measured_date = m.oxidation_state, m.species, m.method, m.date
    row.jurisdiction, row.confidence, row.applicability = m.jurisdiction, m.confidence, m.applicability
    row.assumptions_json = json.dumps(list(m.assumptions))
    row.site_medium = site_medium


@app.post("/api/projects/{project_id}/metal-measurements", status_code=201)
def create_metal_measurement(project_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    from .services.metals import MetalDataError
    from .services.site_records import measurement_from_payload, record_to_dict
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    try:
        m, site_medium = measurement_from_payload(payload)
    except MetalDataError as exc:
        raise HTTPException(422, str(exc))
    row = MetalMeasurementRecord(project_id=project_id)
    _apply_measurement(row, m, site_medium)
    db.add(row)
    db.flush()
    audit(db, project_id, "metal_measurement", row.id, "created",
          {"element": m.element, "basis": m.basis, "medium": m.medium, "source": m.source})
    db.commit()
    db.refresh(row)
    return record_to_dict(row)


@app.get("/api/projects/{project_id}/metal-measurements")
def list_metal_measurements(project_id: int, db: Session = Depends(get_db)):
    from .services.site_records import record_to_dict
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    rows = db.query(MetalMeasurementRecord).filter(MetalMeasurementRecord.project_id == project_id).order_by(MetalMeasurementRecord.id).all()
    return [record_to_dict(r) for r in rows]


@app.put("/api/projects/{project_id}/metal-measurements/{measurement_id}")
def update_metal_measurement(project_id: int, measurement_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    """Replace a measurement. Validated exactly like creation; the previous values are kept in the audit trail."""
    from .services.metals import MetalDataError
    from .services.site_records import measurement_from_payload, record_to_dict
    row = db.get(MetalMeasurementRecord, measurement_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(404, "Measurement not found for this project")
    try:
        m, site_medium = measurement_from_payload(payload)
    except MetalDataError as exc:
        raise HTTPException(422, str(exc))
    previous = record_to_dict(row)
    _apply_measurement(row, m, site_medium)
    db.flush()
    audit(db, project_id, "metal_measurement", row.id, "updated", {"previous": previous, "current": record_to_dict(row)})
    db.commit()
    db.refresh(row)
    return record_to_dict(row)


@app.delete("/api/projects/{project_id}/metal-measurements/{measurement_id}", status_code=204)
def delete_metal_measurement(project_id: int, measurement_id: int, db: Session = Depends(get_db)):
    row = db.get(MetalMeasurementRecord, measurement_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(404, "Measurement not found for this project")
    audit(db, project_id, "metal_measurement", row.id, "deleted", {"element": row.element, "source": row.source})
    db.delete(row)
    db.commit()


@app.post("/api/projects/{project_id}/site-models/analyse")
def analyse_draft_site_model(project_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    """Assess an unsaved draft model with this project's saved metal measurements merged in. Stores nothing."""
    from .services import conceptual_site_model as csm
    from .services.csm_diagram import render_svg
    from .services.site_records import merge_measured
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    jurisdiction = payload.get("jurisdiction")
    if jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    try:
        model = csm.model_from_dict({k: v for k, v in payload.items() if k not in {"name", "jurisdiction"}})
    except csm.ConceptualSiteModelError as exc:
        raise HTTPException(422, str(exc))
    measurements = db.query(MetalMeasurementRecord).filter(MetalMeasurementRecord.project_id == project_id).all()
    merged, linkage_report = merge_measured(model, measurements)
    result = csm.assess(merged, jurisdiction)
    return {**result, "measurement_linkage": linkage_report, "diagram_svg": render_svg(merged, jurisdiction, result)}


@app.post("/api/projects/{project_id}/site-models", status_code=201)
def create_site_model(project_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    from .services import conceptual_site_model as csm
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "A site model needs a name")
    jurisdiction = payload.get("jurisdiction")
    if jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    model_data = {k: v for k, v in payload.items() if k not in {"name", "jurisdiction"}}
    try:
        csm.model_from_dict(model_data)
    except csm.ConceptualSiteModelError as exc:
        raise HTTPException(422, str(exc))
    row = SiteModelRecord(project_id=project_id, name=name, jurisdiction=jurisdiction, model_json=json.dumps(model_data))
    db.add(row)
    db.flush()
    audit(db, project_id, "site_model", row.id, "created", {"name": name, "jurisdiction": jurisdiction})
    db.commit()
    db.refresh(row)
    return _site_model_summary(row)


@app.get("/api/projects/{project_id}/site-models")
def list_site_models(project_id: int, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    rows = db.query(SiteModelRecord).filter(SiteModelRecord.project_id == project_id).order_by(SiteModelRecord.id).all()
    return [_site_model_summary(r) for r in rows]


@app.get("/api/projects/{project_id}/site-models/{site_model_id}")
def get_site_model(project_id: int, site_model_id: int, db: Session = Depends(get_db)):
    row = _site_model_row(db, project_id, site_model_id)
    return {**_site_model_summary(row), "model": json.loads(row.model_json)}


@app.put("/api/projects/{project_id}/site-models/{site_model_id}")
def update_site_model(project_id: int, site_model_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    """Replace a saved site model. Validated exactly like creation; the previous model is kept in the audit trail."""
    from .services import conceptual_site_model as csm
    row = _site_model_row(db, project_id, site_model_id)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "A site model needs a name")
    jurisdiction = payload.get("jurisdiction")
    if jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    model_data = {k: v for k, v in payload.items() if k not in {"name", "jurisdiction"}}
    try:
        csm.model_from_dict(model_data)
    except csm.ConceptualSiteModelError as exc:
        raise HTTPException(422, str(exc))
    audit(db, project_id, "site_model", row.id, "updated", {
        "previous_name": row.name, "previous_jurisdiction": row.jurisdiction,
        "previous_model": json.loads(row.model_json), "name": name, "jurisdiction": jurisdiction,
    })
    row.name, row.jurisdiction, row.model_json = name, jurisdiction, json.dumps(model_data)
    db.commit()
    db.refresh(row)
    return _site_model_summary(row)


@app.delete("/api/projects/{project_id}/site-models/{site_model_id}", status_code=204)
def delete_site_model(project_id: int, site_model_id: int, db: Session = Depends(get_db)):
    row = _site_model_row(db, project_id, site_model_id)
    audit(db, project_id, "site_model", row.id, "deleted", {"name": row.name})
    db.delete(row)
    db.commit()


@app.get("/api/projects/{project_id}/site-models/{site_model_id}/assessment")
def assess_saved_site_model(project_id: int, site_model_id: int, db: Session = Depends(get_db)):
    from .services import conceptual_site_model as csm
    row = _site_model_row(db, project_id, site_model_id)
    merged, linkage_report = _merged_site_model(db, row)
    return {**csm.assess(merged, row.jurisdiction), "measurement_linkage": linkage_report}


@app.get("/api/projects/{project_id}/site-models/{site_model_id}/diagram")
def saved_site_model_diagram(project_id: int, site_model_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from .services.csm_diagram import render_svg
    row = _site_model_row(db, project_id, site_model_id)
    merged, _ = _merged_site_model(db, row)
    return Response(render_svg(merged, row.jurisdiction), media_type="image/svg+xml")


@app.post("/api/conceptual-site-model/diagram")
def conceptual_site_model_diagram(payload: dict[str, Any]):
    from fastapi.responses import Response
    from .services import conceptual_site_model as csm
    from .services.csm_diagram import render_svg
    jurisdiction = payload.get("jurisdiction")
    if jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    try:
        model = csm.model_from_dict(payload)
    except csm.ConceptualSiteModelError as exc:
        raise HTTPException(422, str(exc))
    return Response(render_svg(model, jurisdiction), media_type="image/svg+xml")


@app.get("/api/conceptual-site-model/example")
def conceptual_site_model_example():
    from .services.csm_diagram import EXAMPLE_SITE_PAYLOAD
    return EXAMPLE_SITE_PAYLOAD


@app.get("/api/conceptual-site-model/diagram/example")
def conceptual_site_model_diagram_example():
    from fastapi.responses import Response
    from .services import conceptual_site_model as csm
    from .services.csm_diagram import EXAMPLE_SITE_PAYLOAD, render_svg
    model = csm.model_from_dict(EXAMPLE_SITE_PAYLOAD)
    return Response(render_svg(model, EXAMPLE_SITE_PAYLOAD["jurisdiction"]), media_type="image/svg+xml")


@app.post("/api/conceptual-site-model/assess")
def conceptual_site_model_assess(payload: dict[str, Any]):
    from .services import conceptual_site_model as csm
    jurisdiction = payload.get("jurisdiction")
    if jurisdiction not in {f["key"] for f in FRAMEWORKS}:
        raise HTTPException(422, "jurisdiction must be one of the registered frameworks")
    try:
        model = csm.model_from_dict(payload)
    except csm.ConceptualSiteModelError as exc:
        raise HTTPException(422, str(exc))
    return csm.assess(model, jurisdiction)




@app.get("/api/global-regulatory/frameworks")
def list_global_regulatory_frameworks(
    jurisdiction: str | None = None,
    product_class: str | None = None,
    verification_tier: str | None = None,
    query: str | None = None,
):
    return filter_frameworks(
        jurisdiction=jurisdiction,
        product_class=product_class,
        verification_tier=verification_tier,
        query=query,
    )


@app.get("/api/global-regulatory/frameworks/{framework_id}")
def global_regulatory_framework(framework_id: str):
    row = get_global_framework(framework_id)
    if row is None:
        raise HTTPException(404, "Global regulatory framework not found")
    return row


@app.get("/api/global-regulatory/change-watch")
def list_global_change_watch():
    return global_change_watch()


@app.get("/api/global-regulatory/endpoint-checklist")
def list_global_endpoint_checklist():
    return global_endpoint_checklist()


@app.get("/api/global-regulatory/research-status")
def get_global_regulatory_research_status():
    return global_research_status()


@app.post("/api/global-regulatory/pathway")
def create_global_regulatory_pathway(payload: RegulatoryPathwayCreate):
    return recommend_regulatory_pathway(payload.model_dump())


@app.get("/api/veterinary/animal-profiles")
def list_veterinary_animal_profiles():
    return veterinary_animal_profiles()


@app.get("/api/veterinary/guidance")
def veterinary_guidance():
    return VETERINARY_GUIDANCE


@app.post("/api/veterinary/phase-i")
def veterinary_phase_i(payload: VeterinaryPhaseICreate):
    try:
        return phase_i_decision(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/veterinary/assessment")
def veterinary_assessment(payload: VeterinaryAssessmentCreate):
    try:
        return run_veterinary_assessment(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc






def _persist_envirodesign_run(
    db: Session,
    project_id: int | None,
    chemical_id: int | None,
    model_key: str,
    scenario_name: str,
    payload: dict,
    output: dict,
) -> int | None:
    if project_id is None or chemical_id is None:
        return None
    if db.get(Project, project_id) is None or db.get(Chemical, chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    row = ModelRun(
        project_id=project_id, chemical_id=chemical_id,
        model_key=model_key, model_version=output.get("model_version", "0.1.0"),
        scenario_name=scenario_name, status="completed",
        input_json=json.dumps(payload, sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
        evidence_hash=None,
    )
    db.add(row); db.flush()
    audit(db, project_id, "model_run", row.id, "envirodesign_completed", {"model_key": model_key})
    db.commit(); db.refresh(row)
    return row.id


@app.get("/api/envirodesign/manifest")
def get_envirodesign_manifest():
    return envirodesign_manifest()


@app.get("/api/envirodesign/browser-config")
def get_envirodesign_browser_config():
    return envirodesign_browser_config()


@app.post("/api/envirodesign/persist-browser")
def persist_browser_envirodesign(payload: dict, db: Session = Depends(get_db)):
    model_key = str(payload.get("model_key") or "ENVIRODESIGN_BROWSER_WASM")
    allowed = {
        "ENVIRODESIGN_BROWSER_WASM",
        "ENVIRODESIGN_BROWSER_WASM_COMPARISON",
        "ENVIRODESIGN_BROWSER_WASM_PATHWAY",
    }
    if model_key not in allowed:
        raise HTTPException(422, "Unsupported browser EnviroDesign model key")
    output = payload.get("outputs")
    inputs = payload.get("inputs") or {}
    if not isinstance(output, dict):
        raise HTTPException(422, "outputs must be an object")
    project_id = payload.get("project_id")
    chemical_id = payload.get("chemical_id")
    if (project_id is None) != (chemical_id is None):
        raise HTTPException(422, "Provide both project_id and chemical_id, or neither")
    run_id = _persist_envirodesign_run(
        db, project_id, chemical_id, model_key,
        str(payload.get("scenario_name") or "EnviroDesign browser/WASM analysis"),
        inputs, output,
    )
    return {"model_run_id": run_id, "outputs": output}


@app.post("/api/envirodesign/analyse")
def run_envirodesign_analysis(payload: EnviroDesignAnalyseCreate, db: Session = Depends(get_db)):
    try:
        output = analyse_structure(payload.smiles, payload.name, payload.include_svg)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    model_run_id = _persist_envirodesign_run(
        db, payload.project_id, payload.chemical_id,
        "ENVIRODESIGN_BIOWIN34_ATTRIBUTION", payload.scenario_name, payload.model_dump(), output,
    )
    return {"model_run_id": model_run_id, "outputs": output}


@app.post("/api/envirodesign/compare")
def run_envirodesign_comparison(payload: EnviroDesignCompareCreate, db: Session = Depends(get_db)):
    try:
        output = compare_candidates(
            payload.original_smiles,
            [row.model_dump() for row in payload.candidates],
            payload.protected_smarts,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    model_run_id = _persist_envirodesign_run(
        db, payload.project_id, payload.chemical_id,
        "ENVIRODESIGN_CANDIDATE_COMPARISON", payload.scenario_name, payload.model_dump(), output,
    )
    return {"model_run_id": model_run_id, "outputs": output}


@app.post("/api/envirodesign/pathway-retention")
def run_envirodesign_pathway(payload: EnviroDesignPathwayCreate, db: Session = Depends(get_db)):
    try:
        output = pathway_retention(payload.parent_smiles, [row.model_dump() for row in payload.products])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    model_run_id = _persist_envirodesign_run(
        db, payload.project_id, payload.chemical_id,
        "ENVIRODESIGN_PATHWAY_RETENTION", payload.scenario_name, payload.model_dump(), output,
    )
    return {"model_run_id": model_run_id, "outputs": output}


@app.get("/api/transformation-pathways/providers")
def get_transformation_pathway_providers():
    return {
        "default_provider": "biotransformer",
        "providers": [transformation_provider_capabilities(), envipath_provider_capabilities()],
        "architecture": "provider_neutral",
        "scientific_rule": (
            "Provider output proposes structures and reaction edges. Observed occurrence, formation fractions "
            "and degradation kinetics require separate evidence and fitting."
        ),
    }


@app.get("/api/transformation-pathways/search-curated")
def search_curated_transformation_pathways(parent_smiles: str, package_ids: str | None = None):
    package_id_list = [value for value in (package_ids or "").split(",") if value.strip()] or None
    try:
        return search_envipath_curated_pathways(parent_smiles, package_ids=package_id_list)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/transformation-pathways/predict")
def create_transformation_pathway_prediction(
    payload: TransformationPathwayPredictCreate,
    db: Session = Depends(get_db),
):
    model_key = "BIOTRANSFORMER_ENVMICRO" if payload.provider == "biotransformer" else "ENVIPATH_ENVMICRO"
    try:
        if payload.provider == "biotransformer":
            output = predict_environmental_pathway(
                payload.parent_smiles,
                parent_name=payload.parent_name,
                number_of_steps=payload.number_of_steps,
            )
        else:
            output = predict_envipath_pathway(
                payload.parent_smiles,
                parent_name=payload.parent_name,
                package_id=payload.envipath_package_id,
                number_of_steps=payload.number_of_steps,
            )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    model_run_id = None
    if payload.project_id is not None and payload.chemical_id is not None:
        if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
            raise HTTPException(404, "Project or chemical not found")
        row = ModelRun(
            project_id=payload.project_id,
            chemical_id=payload.chemical_id,
            model_key=model_key,
            model_version=output["model_version"],
            scenario_name=payload.scenario_name,
            status="completed",
            input_json=json.dumps(payload.model_dump(), sort_keys=True),
            output_json=json.dumps(output, sort_keys=True),
            assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
            evidence_hash=output["query"]["raw_response_sha256"],
        )
        db.add(row)
        db.flush()
        audit(
            db,
            payload.project_id,
            "model_run",
            row.id,
            "transformation_pathway_predicted",
            {
                "provider": payload.provider,
                "provider_query_id": output["query"]["provider_query_id"],
                "unique_product_count": output["summary"]["unique_product_count"],
            },
        )
        db.commit()
        db.refresh(row)
        model_run_id = row.id
    return {"model_run_id": model_run_id, "outputs": output}


@app.post("/api/degradation-kinetics/assess")
def run_degradation_kinetics(payload: DegradationKineticsAssessmentCreate, db: Session = Depends(get_db)):
    try:
        output = run_degradation_kinetics_assessment(
            regulatory_framework=payload.regulatory_framework,
            matrix=payload.matrix,
            parent_name=payload.parent_name,
            parent_observations=[row.model_dump() for row in payload.parent_observations],
            metabolites=[row.model_dump() for row in payload.metabolites],
        )
    except (ValueError, KineticFitError) as exc:
        raise HTTPException(422, str(exc)) from exc

    model_run_id = None
    if payload.project_id is not None and payload.chemical_id is not None:
        if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
            raise HTTPException(404, "Project or chemical not found")
        row = ModelRun(
            project_id=payload.project_id,
            chemical_id=payload.chemical_id,
            model_key="ENVIROCHEM_DEGRADATION_KINETICS",
            model_version="0.1.0",
            scenario_name=payload.scenario_name,
            status="completed",
            input_json=json.dumps(payload.model_dump(), sort_keys=True),
            output_json=json.dumps(output, sort_keys=True),
            assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
            evidence_hash=None,
        )
        db.add(row)
        db.flush()
        audit(
            db, payload.project_id, "model_run", row.id, "degradation_kinetics_assessed",
            {
                "regulatory_framework": payload.regulatory_framework,
                "parent_selected_model": output["parent"]["kinetics"]["selected_model"],
                "metabolite_count": len(output["metabolites"]),
            },
        )
        db.commit()
        db.refresh(row)
        model_run_id = row.id
    return {"model_run_id": model_run_id, "outputs": output}


@app.get("/api/analytical-sources")
def get_analytical_sources():
    return {"sources": analytical_source_registry()}


@app.get("/api/chemicals/{chemical_id}/identification")
def get_chemical_identification_profile(chemical_id: int, ion_mode: str | None = None, db: Session = Depends(get_db)):
    chemical = db.get(Chemical, chemical_id)
    if chemical is None:
        raise HTTPException(404, "Chemical not found")
    if not chemical.inchikey:
        raise HTTPException(
            422,
            "This chemical has no recorded InChIKey; an identification profile cannot be looked up without one.",
        )
    try:
        return build_identification_profile(chemical.inchikey, ion_mode=ion_mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/analytical-identification/{inchikey}/transformation-products")
def get_known_transformation_products_by_inchikey(inchikey: str):
    """Curated (NORMAN EAWAGTPS) parent -> transformation-product pairs only: local data, no live third-party call."""
    try:
        return known_transformation_products(inchikey)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/analytical-identification/{inchikey}")
def get_identification_profile_by_inchikey(inchikey: str, ion_mode: str | None = None):
    """Look up an identification profile directly by InChIKey.

    A known transformation product is a real substance in its own right and may not have a
    ``Chemical`` row of its own -- this lets the Identification screen follow parent -> TP ->
    that TP's own profile without first requiring the TP to be imported as a project chemical.
    """
    try:
        return build_identification_profile(inchikey, ion_mode=ion_mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/ms-evidence/capabilities")
def get_ms_evidence_capabilities():
    return ms_evidence_capabilities()


@app.post("/api/ms-evidence/import")
async def import_ms_evidence_file(
    mzml_file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    chemical_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if project_id is not None or chemical_id is not None:
        if project_id is None or chemical_id is None:
            raise HTTPException(422, "Provide both project_id and chemical_id to link this import, or neither")
        if db.get(Project, project_id) is None or db.get(Chemical, chemical_id) is None:
            raise HTTPException(404, "Project or chemical not found")

    raw = await mzml_file.read()
    if not raw:
        raise HTTPException(422, "mzML file is empty")
    digest = ms_evidence_sha256(raw)
    existing = db.query(MSRawEvidenceFile).filter(MSRawEvidenceFile.sha256 == digest).one_or_none()
    if existing is not None:
        raise HTTPException(409, f"This exact file was already imported as raw evidence file #{existing.id}")

    try:
        parsed = parse_mzml(raw)
    except MzMLParseError as exc:
        raise HTTPException(422, str(exc)) from exc

    raw_file = MSRawEvidenceFile(
        project_id=project_id,
        chemical_id=chemical_id,
        filename=mzml_file.filename or "unnamed.mzML",
        sha256=digest,
        format="mzml",
        ionisation_mode=parsed["ionisation_mode"],
        ms1_scan_count=parsed["ms1_scan_count"],
        ms2_scan_count=parsed["ms2_scan_count"],
        tic_json=json.dumps(parsed["tic"], sort_keys=True),
    )
    db.add(raw_file)
    db.flush()
    for feature in parsed["features"]:
        db.add(MSFeature(
            raw_file_id=raw_file.id,
            feature_index=feature["feature_index"],
            retention_time_min=feature["retention_time_min"],
            precursor_mz=feature["precursor_mz"],
            precursor_charge=feature["precursor_charge"],
            collision_energy=feature["collision_energy"],
            scan_id=feature["scan_id"],
            base_peak_mz=feature["base_peak_mz"],
            product_ion_count=len(feature["product_ions"]),
            product_ions_json=json.dumps(feature["product_ions"], sort_keys=True),
            xic_json=json.dumps(feature["xic"], sort_keys=True),
        ))
    if project_id is not None:
        audit(db, project_id, "ms_raw_evidence_file", raw_file.id, "ms_evidence_imported", {
            "filename": raw_file.filename,
            "sha256": digest,
            "ms1_scan_count": raw_file.ms1_scan_count,
            "ms2_scan_count": raw_file.ms2_scan_count,
        })
    db.commit()
    db.refresh(raw_file)
    return _ms_raw_file_summary(raw_file)


def _ms_raw_file_summary(raw_file: MSRawEvidenceFile) -> dict:
    return {
        "id": raw_file.id,
        "filename": raw_file.filename,
        "sha256": raw_file.sha256,
        "format": raw_file.format,
        "project_id": raw_file.project_id,
        "chemical_id": raw_file.chemical_id,
        "ionisation_mode": raw_file.ionisation_mode,
        "ms1_scan_count": raw_file.ms1_scan_count,
        "ms2_scan_count": raw_file.ms2_scan_count,
        "uploaded_at": raw_file.uploaded_at.isoformat(),
        "tic": json.loads(raw_file.tic_json),
        "features": [_ms_feature_summary(f) for f in raw_file.features],
    }


def _ms_feature_summary(feature: MSFeature) -> dict:
    return {
        "id": feature.id,
        "feature_index": feature.feature_index,
        "retention_time_min": feature.retention_time_min,
        "precursor_mz": feature.precursor_mz,
        "precursor_charge": feature.precursor_charge,
        "collision_energy": feature.collision_energy,
        "base_peak_mz": feature.base_peak_mz,
        "product_ion_count": feature.product_ion_count,
        "confidence_level": feature.confidence_level,
    }


@app.get("/api/ms-evidence/files")
def list_ms_evidence_files(project_id: int | None = None, chemical_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(MSRawEvidenceFile)
    if project_id is not None:
        query = query.filter(MSRawEvidenceFile.project_id == project_id)
    if chemical_id is not None:
        query = query.filter(MSRawEvidenceFile.chemical_id == chemical_id)
    return [_ms_raw_file_summary(row) for row in query.order_by(MSRawEvidenceFile.uploaded_at.desc()).all()]


@app.get("/api/ms-evidence/files/{file_id}")
def get_ms_evidence_file(file_id: int, db: Session = Depends(get_db)):
    raw_file = db.get(MSRawEvidenceFile, file_id)
    if raw_file is None:
        raise HTTPException(404, "Raw evidence file not found")
    return _ms_raw_file_summary(raw_file)


@app.get("/api/ms-evidence/features/{feature_id}")
def get_ms_evidence_feature(feature_id: int, db: Session = Depends(get_db)):
    feature = db.get(MSFeature, feature_id)
    if feature is None:
        raise HTTPException(404, "Feature not found")
    return {
        **_ms_feature_summary(feature),
        "raw_file_id": feature.raw_file_id,
        "scan_id": feature.scan_id,
        "reviewer_note": feature.reviewer_note,
        "product_ions": json.loads(feature.product_ions_json),
        "xic": json.loads(feature.xic_json),
    }


@app.patch("/api/ms-evidence/features/{feature_id}/review")
def review_ms_evidence_feature(feature_id: int, payload: MSFeatureReviewUpdate, db: Session = Depends(get_db)):
    feature = db.get(MSFeature, feature_id)
    if feature is None:
        raise HTTPException(404, "Feature not found")
    feature.confidence_level = payload.confidence_level
    feature.reviewer_note = payload.reviewer_note
    raw_file = db.get(MSRawEvidenceFile, feature.raw_file_id)
    if raw_file is not None and raw_file.project_id is not None:
        audit(db, raw_file.project_id, "ms_feature", feature.id, "ms_feature_reviewed", {
            "confidence_level": payload.confidence_level,
        })
    db.commit()
    db.refresh(feature)
    return {
        **_ms_feature_summary(feature),
        "reviewer_note": feature.reviewer_note,
    }


@app.get("/api/focus/manifest")
def get_focus_manifest():
    return focus_manifest()


@app.get("/api/focus/installation-status")
def get_focus_installation_status():
    return focus_installation_status()


@app.get("/api/external-model-integrations")
def get_external_model_integrations():
    return external_integration_catalog()


@app.get("/api/external-model-integrations/{model_key}")
def get_external_model_integration(model_key: str):
    profile = external_integration_profile(model_key.upper())
    if profile is None:
        raise HTTPException(404, "External model integration profile not found")
    return profile


@app.get("/api/external-tools/status")
def get_external_tool_statuses():
    return [external_tool_status(key) for key in sorted(EPA_EXECUTION_MODEL_KEYS)]


@app.get("/api/external-tools/status/{model_key}")
def get_external_tool_status(model_key: str):
    key = model_key.upper()
    if key not in EPA_EXECUTION_MODEL_KEYS:
        raise HTTPException(404, "No controlled EPA execution bridge is registered for this model")
    return external_tool_status(key)


@app.get("/api/us-exposure/manifest")
def get_us_exposure_manifest():
    return us_exposure_manifest()


@app.get("/api/us-exposure/sources")
def get_us_exposure_sources():
    return us_exposure_source_catalogue()


@app.get("/api/us-exposure/scenarios")
def get_us_exposure_scenarios(
    status: str | None = Query(default=None),
    include_reference_only: bool = Query(default=False),
):
    try:
        return us_exposure_scenario_catalogue(
            status=status,
            include_reference_only=include_reference_only,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/us-exposure/scenarios/{scenario_key}")
def get_us_exposure_scenario(scenario_key: str):
    scenario = us_exposure_scenario_by_key(scenario_key)
    if scenario is None:
        raise HTTPException(404, "US exposure scenario not found")
    return scenario


@app.post("/api/us-exposure/completeness")
def check_us_exposure_completeness(payload: USExposureCompletenessCreate):
    return assess_us_exposure_completeness(payload.model_dump())


@app.post("/api/model-runs/us-industrial-exposure")
def create_us_industrial_exposure_run(
    payload: USIndustrialExposureRunCreate,
    db: Session = Depends(get_db),
):
    project = db.get(Project, payload.project_id)
    chemical = db.get(Chemical, payload.chemical_id)
    if project is None or chemical is None:
        raise HTTPException(404, "Project or chemical not found")
    if db.get(
        ProjectChemical,
        {"project_id": payload.project_id, "chemical_id": payload.chemical_id},
    ) is None:
        raise HTTPException(422, "Chemical is not attached to the selected project")
    if payload.source_scenario_key:
        scenario = us_exposure_scenario_by_key(payload.source_scenario_key)
        if scenario is None:
            raise HTTPException(422, "Unknown US exposure scenario key")
    try:
        output = run_industrial_exposure_screen(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN",
        model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        status="completed_reviewed" if payload.scientist_review_confirmed else "completed_screening",
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output["warnings"], sort_keys=True),
        evidence_hash=None,
    )
    db.add(row)
    db.flush()
    audit(db, payload.project_id, "model_run", row.id, "us_industrial_exposure_completed", {
        "model_key": row.model_key,
        "source_scenario_key": payload.source_scenario_key,
        "review_status": output["review_status"],
        "direct_environmental_release_kg_day": output["releases"]["direct_environmental_release_kg_day"],
        "managed_waste_transfer_kg_day": output["releases"]["managed_waste_transfer_kg_day"],
        "worker_task_count": len(output["worker_exposure"]),
        "mass_balance_error_fraction": output["mass_balance"]["closure_error_fraction"],
    })
    db.commit()
    db.refresh(row)
    return {"model_run_id": row.id, "outputs": output}


@app.get("/api/toxswa/manifest")
def toxswa_model_manifest():
    result = toxswa_manifest()
    result["installation_status"] = focus_installation_status()
    return result


@app.get("/api/toxswa/route/{contaminant_group}")
def toxswa_route(contaminant_group: str):
    if contaminant_group not in CONTAMINANT_GROUPS:
        raise HTTPException(422, "Unsupported contaminant group")
    return toxswa_route_recommendation(contaminant_group)


def _persist_toxswa_screen(db: Session, payload: ToxswaSurfaceWaterRunCreate, output: dict) -> int:
    if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_TOXSWA_PROCESS_SCREEN",
        model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        status="completed_screening",
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
        evidence_hash=None,
    )
    db.add(row); db.flush()
    audit(db, payload.project_id, "model_run", row.id, "toxswa_process_screen_completed", {
        "model_key": row.model_key,
        "contaminant_group": payload.contaminant_group,
        "loading_mode": payload.loading_mode,
        "global_max_pecsw_dissolved_ug_l": output["summary"]["global_max_pecsw_dissolved_ug_l"],
        "global_max_pecsed_ug_kg": output["summary"]["global_max_pecsed_ug_kg"],
        "mass_balance_error_fraction": output["mass_balance"]["closure_error_fraction"],
        "official_equivalence": False,
    })
    db.commit(); db.refresh(row)
    return row.id


@app.post("/api/model-runs/toxswa-surface-water")
def create_toxswa_surface_water_run(payload: ToxswaSurfaceWaterRunCreate, db: Session = Depends(get_db)):
    if payload.contaminant_group not in CONTAMINANT_GROUPS:
        raise HTTPException(422, "Unsupported contaminant group")
    try:
        output = run_toxswa_process_screen(payload.model_dump())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    run_id = _persist_toxswa_screen(db, payload, output)
    return {"model_run_id": run_id, "outputs": output}


@app.post("/api/toxswa/import-official-summary")
async def import_toxswa_official_summary(
    summary_file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    chemical_id: int | None = Form(default=None),
    scenario_name: str = Form(default="Imported FOCUS_TOXSWA result"),
    db: Session = Depends(get_db),
):
    raw = await summary_file.read()
    if not raw:
        raise HTTPException(422, "TOXSWA summary file is empty")
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = parse_toxswa_official_summary(text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    parsed["raw_output_sha256"] = toxswa_raw_output_hash(raw)
    parsed["filename"] = summary_file.filename
    model_run_id = None
    if project_id is not None or chemical_id is not None:
        if project_id is None or chemical_id is None:
            raise HTTPException(422, "Provide both project_id and chemical_id to persist the official import")
        if db.get(Project, project_id) is None or db.get(Chemical, chemical_id) is None:
            raise HTTPException(404, "Project or chemical not found")
        row = ModelRun(
            project_id=project_id,
            chemical_id=chemical_id,
            model_key="FOCUS_TOXSWA_OFFICIAL_IMPORT",
            model_version=parsed.get("focus_toxswa_version") or "unknown",
            scenario_name=scenario_name,
            status="official_output_imported",
            input_json=json.dumps({"filename": summary_file.filename, "sha256": parsed["raw_output_sha256"]}, sort_keys=True),
            output_json=json.dumps(parsed, sort_keys=True),
            assumptions_json=json.dumps(parsed.get("warnings", []), sort_keys=True),
            evidence_hash=None,
        )
        db.add(row); db.flush()
        audit(db, project_id, "model_run", row.id, "focus_toxswa_output_imported", {
            "filename": summary_file.filename,
            "sha256": parsed["raw_output_sha256"],
            "focus_toxswa_version": parsed.get("focus_toxswa_version"),
            "toxswa_kernel_version": parsed.get("toxswa_kernel_version"),
        })
        db.commit(); db.refresh(row)
        model_run_id = row.id
    return {"model_run_id": model_run_id, "parsed": parsed}


@app.get("/api/pearl/manifest")
def pearl_model_manifest():
    return pearl_manifest()


@app.get("/api/pearl/focus-scenarios")
def pearl_focus_scenarios():
    return focus_scenario_manifest()


def _persist_pearl_run(db: Session, payload: PearlGroundwaterRunCreate, output: dict, *, hydrology_mode: str) -> int:
    if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    stored_input = payload.model_dump()
    stored_input["hydrology_mode"] = hydrology_mode
    row = ModelRun(
        project_id=payload.project_id, chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_PEARLPY_GROUNDWATER", model_version=output["model_version"],
        scenario_name=payload.scenario_name, status="completed",
        input_json=json.dumps(stored_input, sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
        evidence_hash=None,
    )
    db.add(row); db.flush()
    audit(db, payload.project_id, "model_run", row.id, "pearl_groundwater_completed", {
        "model_key": row.model_key,
        "hydrology_mode": hydrology_mode,
        "bottom_leached_fraction": output["summary"]["bottom_leached_fraction"],
    })
    db.commit(); db.refresh(row)
    return row.id


@app.post("/api/model-runs/pearl-groundwater")
def create_pearl_groundwater_run(payload: PearlGroundwaterRunCreate, db: Session = Depends(get_db)):
    try:
        output = run_pearl_groundwater_screen(payload.model_dump())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    run_id = _persist_pearl_run(db, payload, output, hydrology_mode=output["resolved_inputs"]["hydrology"]["mode"])
    return {"model_run_id": run_id, "outputs": output}


@app.post("/api/model-runs/pearl-groundwater/swap")
async def create_pearl_groundwater_swap_run(
    payload_json: str = Form(...),
    swap_csv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        payload = PearlGroundwaterRunCreate.model_validate_json(payload_json)
    except Exception as exc:
        raise HTTPException(422, f"Invalid PEARL payload: {exc}") from exc
    suffix = Path(swap_csv.filename or "swap_output.csv").suffix or ".csv"
    raw = await swap_csv.read()
    if not raw:
        raise HTTPException(422, "SWAP CSV is empty")
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(raw)
            temp_path = Path(handle.name)
        output = run_pearl_groundwater_screen(payload.model_dump(), swap_csv_path=temp_path)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        if 'temp_path' in locals():
            temp_path.unlink(missing_ok=True)
    run_id = _persist_pearl_run(db, payload, output, hydrology_mode="imported_swap_csv")
    return {"model_run_id": run_id, "outputs": output}


@app.post("/api/model-runs/biosolids")
def create_biosolids_run(payload: BiosolidsLandApplicationCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    if db.get(ProjectChemical, {"project_id": payload.project_id, "chemical_id": payload.chemical_id}) is None:
        raise HTTPException(422, "Chemical is not attached to the selected project")
    profile = _validated_run_profile(
        db, payload.assessment_profile_id, payload.project_id, payload.chemical_id,
    )
    if profile is not None:
        if (
            profile.soil_dt50_days is None
            or payload.soil_dt50_days is None
            or abs(payload.soil_dt50_days - profile.soil_dt50_days)
            > max(1e-12, abs(profile.soil_dt50_days) * 1e-10)
        ):
            raise HTTPException(422, "Biosolids soil DT50 differs from the reviewed assessment profile")
    if payload.activity_simpletreat_model_run_id is not None:
        activity_run = db.get(ModelRun, payload.activity_simpletreat_model_run_id)
        if activity_run is None or activity_run.model_key != "ENVIROCHEM_ACTIVITY_SIMPLETREAT":
            raise HTTPException(404, "Activity SimpleTreat model run not found")
        if activity_run.project_id != payload.project_id or activity_run.chemical_id != payload.chemical_id:
            raise HTTPException(422, "Activity SimpleTreat run does not belong to the selected project and chemical")
        expected_sludge_mass = json.loads(activity_run.output_json).get("sludge_mass_kg_day")
        if (
            payload.source_mode != "wwtp_chemical_mass"
            or expected_sludge_mass is None
            or payload.chemical_mass_to_sludge_kg_day is None
            or abs(payload.chemical_mass_to_sludge_kg_day - expected_sludge_mass)
            > max(1e-12, abs(expected_sludge_mass) * 1e-10)
        ):
            raise HTTPException(422, "Biosolids sludge mass differs from the linked Activity SimpleTreat run")
    try:
        output = run_biosolids_land_application(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = ModelRun(
        project_id=payload.project_id, chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_BIOSOLIDS_LAND_APPLICATION", model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("assumptions", []) + output.get("warnings", []), sort_keys=True),
        evidence_hash=_profile_hash(profile) if profile is not None else None, status="completed",
    )
    db.add(row); db.flush()
    audit(db, payload.project_id, "model_run", row.id, "biosolids_completed", {"model_key": row.model_key, "annual_loading_kg_ha": output["annual_chemical_loading_kg_ha"]})
    db.commit(); db.refresh(row)
    return {"model_run_id": row.id, "outputs": output}


@app.post("/api/model-runs/plant-uptake")
def create_plant_uptake_run(payload: PlantUptakeScreenCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    if db.get(ProjectChemical, {"project_id": payload.project_id, "chemical_id": payload.chemical_id}) is None:
        raise HTTPException(422, "Chemical is not attached to the selected project")
    profile = _validated_run_profile(
        db, payload.assessment_profile_id, payload.project_id, payload.chemical_id,
    )
    if profile is not None:
        if payload.ionisation_class != profile.ionisation_class:
            raise HTTPException(422, "Plant-uptake ionisation class differs from the reviewed assessment profile")
        if (
            profile.log_kow is None
            or payload.log_kow is None
            or abs(payload.log_kow - profile.log_kow) > max(1e-12, abs(profile.log_kow) * 1e-10)
        ):
            raise HTTPException(422, "Plant-uptake log Kow differs from the reviewed assessment profile")
    if payload.sorption_model_run_id is not None:
        sorption_run = db.get(ModelRun, payload.sorption_model_run_id)
        if sorption_run is None or sorption_run.model_key != "ENVIROCHEM_SORPTION":
            raise HTTPException(404, "Sorption model run not found")
        if sorption_run.project_id != payload.project_id or sorption_run.chemical_id != payload.chemical_id:
            raise HTTPException(422, "Sorption run does not belong to the selected project and chemical")
        expected_kd = json.loads(sorption_run.output_json).get("selected", {}).get("kd_l_kg")
        if expected_kd is None or abs(payload.kd_l_kg - expected_kd) > max(1e-12, abs(expected_kd) * 1e-10):
            raise HTTPException(422, "Plant-uptake Kd differs from the linked sorption run")
    try:
        output = run_plant_uptake_screen(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = ModelRun(
        project_id=payload.project_id, chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_PLANT_UPTAKE", model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("assumptions", []) + output.get("warnings", []), sort_keys=True),
        evidence_hash=_profile_hash(profile) if profile is not None else None, status="completed",
    )
    db.add(row); db.flush()
    audit(db, payload.project_id, "model_run", row.id, "plant_uptake_completed", {"model_key": row.model_key, "edible_tissue_mg_kg_fw": output["edible_tissue_concentration_mg_kg_fw"]})
    db.commit(); db.refresh(row)
    return {"model_run_id": row.id, "outputs": output}


@app.post("/api/model-runs/multimedia-fate")
def create_multimedia_fate_run(payload: MultimediaFateRunCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    try:
        output = run_multimedia_fate_screen(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key=output["model_key"],
        model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
        evidence_hash=None,
        status="completed",
    )
    db.add(row)
    db.flush()
    audit(db, payload.project_id, "model_run", row.id, "multimedia_fate_completed", {
        "model_key": row.model_key,
        "emission_input_kg_day": output["mass_balance"]["emission_input_kg_day"],
        "relative_closure_error": output["mass_balance"]["relative_closure_error"],
    })
    db.commit()
    db.refresh(row)
    return {"model_run_id": row.id, "outputs": output}


@app.post("/api/model-runs/catchment-river")
def create_catchment_river_run(payload: CatchmentRiverRunCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None or db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Project or chemical not found")
    try:
        output = run_catchment_river_network(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key=output["model_key"],
        model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output.get("warnings", []), sort_keys=True),
        evidence_hash=None,
        status="completed",
    )
    db.add(row)
    db.flush()
    audit(db, payload.project_id, "model_run", row.id, "catchment_river_completed", {
        "model_key": row.model_key,
        "peak_mean_concentration_ug_l": output["network_summary"]["peak_mean_concentration_ug_l"],
        "peak_segment_id": output["network_summary"]["peak_segment_id"],
    })
    db.commit()
    db.refresh(row)
    return {"model_run_id": row.id, "outputs": output}


@app.get("/api/model-registry")
def model_registry():
    return [
        {**model, "adapter_contract_available": model["key"] in ADAPTER_CONTRACTS}
        for model in MODELS
    ]


@app.get("/api/model-adapter-contracts")
def model_adapter_contracts():
    return ADAPTER_CONTRACTS


@app.post("/api/assessment-plan")
def assessment_plan(payload: AssessmentPlanCreate):
    if payload.contaminant_group not in CONTAMINANT_GROUPS:
        raise HTTPException(422, "Unsupported contaminant group")
    if payload.scenario not in SCENARIOS:
        raise HTTPException(422, "Unsupported exposure scenario")
    return build_assessment_plan(payload.model_dump())


def _orchestration_model(model_key: str) -> dict:
    model = next((item for item in MODELS if item["key"] == model_key), None)
    if model is None:
        raise HTTPException(422, f"Unknown model key: {model_key}")
    return model


OFFICIAL_REGULATORY_WORKFLOW_KEYS = {
    "PEARL", "PELMO", "MACRO", "SWASH", "TOXSWA", "PRZM", "EXAMS",
    "PWC", "AGDRIFT", "TERRPLANT", "TREX", "BEEREX",
    "CHEMSTEER", "CEM", "EFAST",
}


def _orchestration_identity(
    db: Session,
    project_id: int,
    chemical_id: int,
) -> tuple[Project, Chemical, ChemicalIdentitySnapshot, dict]:
    project = db.get(Project, project_id)
    chemical = db.get(Chemical, chemical_id)
    if project is None or chemical is None:
        raise HTTPException(404, "Project or chemical not found")
    membership = db.get(
        ProjectChemical,
        {"project_id": project_id, "chemical_id": chemical_id},
    )
    if membership is None:
        raise HTTPException(422, "Chemical is not attached to the selected project")
    snapshot = db.scalar(
        select(ChemicalIdentitySnapshot).where(
            ChemicalIdentitySnapshot.chemical_id == chemical_id
        )
    )
    if snapshot is None:
        raise HTTPException(
            422,
            "A confirmed immutable chemical identity snapshot is required before orchestration",
        )
    identity = json.loads(snapshot.snapshot_json)
    identity.update({
        "identity_snapshot_id": snapshot.id,
        "identity_hash": snapshot.identity_hash,
        "source_key": snapshot.source_key,
        "source_record_id": snapshot.source_record_id,
        "source_url": snapshot.source_url,
        "confirmed_at": snapshot.confirmed_at.isoformat(),
    })
    return project, chemical, snapshot, identity


def _orchestration_evidence_snapshot(row: EvidenceRecord) -> dict:
    payload = {
        "id": row.id,
        "chemical_id": row.chemical_id,
        "property_code": row.property_code,
        "evidence_type": row.evidence_type,
        "value": row.original_value,
        "unit": row.original_unit,
        "endpoint_kind": row.endpoint_kind,
        "test_guideline": row.test_guideline,
        "reliability_score": row.reliability_score,
        "representative_group_key": row.representative_group_key,
        "source": {
            "id": row.source.id,
            "title": row.source.title,
            "organisation": row.source.organisation,
            "publication_year": row.source.publication_year,
            "identifier": row.source.identifier,
            "url": row.source.url,
        },
    }
    payload["evidence_hash"] = sha256_payload(payload)
    return payload


def _validate_benchmark_evidence(
    db: Session,
    *,
    risk: dict,
    project_id: int,
    chemical_id: int,
    jurisdiction: str,
) -> None:
    evidence_ids = risk.get("benchmark_evidence_ids") or []
    if not evidence_ids:
        risk["benchmark_evidence"] = []
        risk["benchmark_value_verified"] = False
        risk["benchmark_derivation"] = {
            "status": "unverified_manual_benchmark",
            "message": "No reviewed benchmark evidence was bound to this risk calculation.",
        }
        return
    if db.get(ProjectChemical, {"project_id": project_id, "chemical_id": chemical_id}) is None:
        raise HTTPException(422, "Benchmark evidence chemical is not attached to this project")
    rows = list(db.scalars(
        select(EvidenceRecord).where(EvidenceRecord.id.in_(evidence_ids))
    ).all())
    by_id = {row.id: row for row in rows}
    if set(by_id) != set(evidence_ids):
        raise HTTPException(404, "One or more benchmark evidence records were not found")
    if any(row.chemical_id != chemical_id for row in rows):
        raise HTTPException(422, "Benchmark evidence does not belong to the selected chemical")
    critical = by_id[risk["critical_benchmark_evidence_id"]]
    risk["benchmark_evidence"] = [
        _orchestration_evidence_snapshot(by_id[evidence_id])
        for evidence_id in evidence_ids
    ]

    if risk["metric"] == "pec_pnec_rq":
        endpoint_type = SUPPORTED_AQUATIC_ENDPOINTS.get(critical.property_code)
        if endpoint_type is None:
            raise HTTPException(422, "Evidence-derived freshwater PNEC requires LC50, EC50, NOEC or EC10 evidence")
        if critical.endpoint_kind:
            normalised_kind = re.sub(r"[^A-Z0-9]", "", critical.endpoint_kind.upper())
            if normalised_kind != endpoint_type:
                raise HTTPException(422, "Critical evidence endpoint kind conflicts with its property code")
        if risk["benchmark"]["compartment"] not in {"water", "surface_water"}:
            raise HTTPException(422, "This evidence-derived PNEC implementation currently supports freshwater only")
        try:
            derivation = derive_pnec(
                endpoint_value=critical.original_value,
                endpoint_unit=critical.original_unit,
                endpoint_type=endpoint_type,
                assessment_factor=risk["assessment_factor"],
                assessment_factor_rationale=risk["assessment_factor_rationale"],
                guidance_reference=risk["guidance_reference"],
                target_compartment="freshwater",
            )
            derived_quantity = {
                **risk["benchmark"],
                "value": derivation["pnec"]["value"],
                "unit": derivation["pnec"]["unit"],
            }
            derived_on_declared_basis = harmonise_quantity(
                derived_quantity, risk["benchmark"]["unit"]
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        declared_value = float(risk["benchmark"]["value"])
        if not math.isclose(
            derived_on_declared_basis["value"], declared_value,
            rel_tol=1e-9, abs_tol=1e-12,
        ):
            raise HTTPException(
                422,
                "Declared PNEC does not match the selected critical endpoint divided by the explicit assessment factor",
            )
        derivation["critical_evidence_id"] = critical.id
        derivation["jurisdiction"] = jurisdiction
        derivation["jurisdictional_status"] = (
            "eu_style_explicit_af_requires_competent_review"
            if jurisdiction in {"EU", "UK", "CH"}
            else "research_adaptation_not_us_programme_pnec"
        )
        risk["benchmark_derivation"] = derivation
    elif risk["metric"] == "pesticide_rq_loc":
        if not critical.property_code.startswith("ECOTOX."):
            raise HTTPException(422, "Pesticide RQ/LOC requires an ecotoxicity effect endpoint")
        evidence_quantity = {
            **risk["benchmark"],
            "value": critical.original_value,
            "unit": critical.original_unit,
        }
        try:
            effect_on_declared_basis = harmonise_quantity(
                evidence_quantity, risk["benchmark"]["unit"]
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if not math.isclose(
            effect_on_declared_basis["value"], float(risk["benchmark"]["value"]),
            rel_tol=1e-9, abs_tol=1e-12,
        ):
            raise HTTPException(422, "Declared pesticide effect benchmark does not match the selected evidence")
        risk["benchmark_derivation"] = {
            "critical_evidence_id": critical.id,
            "jurisdiction": jurisdiction,
            "calculation": "reviewed effect endpoint used directly; RQ compared with explicit programme LOC",
            "jurisdictional_status": "programme_specific_loc_requires_competent_review",
        }
    risk["benchmark_value_verified"] = True


def _model_run_output_payload(row: ModelRun):
    try:
        return json.loads(row.output_json)
    except (json.JSONDecodeError, TypeError):
        return row.output_json


def _model_run_output_hash(row: ModelRun) -> str:
    return sha256_payload(_model_run_output_payload(row))


def _find_output_endpoint(payload, endpoint_key: str) -> list:
    matches: list = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == endpoint_key:
                matches.append(value)
            matches.extend(_find_output_endpoint(value, endpoint_key))
    elif isinstance(payload, list):
        for value in payload:
            matches.extend(_find_output_endpoint(value, endpoint_key))
    return matches


def _endpoint_unit_from_key(endpoint_key: str) -> str | None:
    token = endpoint_key.casefold().replace("µ", "u").replace("μ", "u")
    suffixes = {
        "_ng_l": "ng/L",
        "_ug_l": "µg/L",
        "_mg_l": "mg/L",
        "_ng_kg": "ng/kg",
        "_ug_kg": "µg/kg",
        "_mg_kg": "mg/kg",
        "_kg_day": "kg/day",
        "_g_day": "g/day",
        "_kg_ha": "kg/ha",
    }
    return next((unit for suffix, unit in suffixes.items() if token.endswith(suffix)), None)


def _reconcile_exposure_value(risk: dict, output_payload) -> dict:
    endpoint_key = risk.get("exposure_endpoint_key")
    if not endpoint_key:
        return {
            "verified": False,
            "status": "endpoint_key_required",
            "message": "Name the stored exposure endpoint before this value can control a tier gate.",
        }
    matches = _find_output_endpoint(output_payload, endpoint_key)
    if len(matches) != 1:
        if not matches:
            raise HTTPException(422, f"Exposure endpoint {endpoint_key} was not found in the referenced output")
        raise HTTPException(422, f"Exposure endpoint {endpoint_key} is ambiguous in the referenced output")
    stored = matches[0]
    stored_unit = None
    if isinstance(stored, dict):
        stored_unit = stored.get("unit")
        stored = stored.get("value")
    try:
        stored_value = float(stored)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, f"Exposure endpoint {endpoint_key} is not a numeric output") from exc
    if not math.isfinite(stored_value):
        raise HTTPException(422, f"Exposure endpoint {endpoint_key} is not finite")
    stored_unit = stored_unit or _endpoint_unit_from_key(endpoint_key)
    if not stored_unit:
        return {
            "verified": False,
            "status": "stored_unit_not_machine_readable",
            "stored_value": stored_value,
            "message": "The stored endpoint unit could not be verified from output metadata or its key.",
        }
    try:
        declared = harmonise_quantity(risk["exposure"], stored_unit)
    except ValueError as exc:
        raise HTTPException(422, f"Exposure endpoint unit reconciliation failed: {exc}") from exc
    if not math.isclose(declared["value"], stored_value, rel_tol=1e-9, abs_tol=1e-12):
        raise HTTPException(
            422,
            f"Declared exposure does not match stored endpoint {endpoint_key}: "
            f"{declared['value']} {stored_unit} versus {stored_value} {stored_unit}",
        )
    return {
        "verified": True,
        "status": "matched_stored_output",
        "endpoint_key": endpoint_key,
        "stored_value": stored_value,
        "stored_unit": stored_unit,
    }


def _validated_execution_reference(
    db: Session,
    *,
    project_id: int,
    chemical_id: int,
    identity_hash: str,
    model_key: str,
    run_id: int | None,
    workflow_id: int | None,
    supplied_output_hash: str | None,
) -> dict:
    if run_id is not None and workflow_id is not None:
        raise HTTPException(422, "Use either a model run or a model workflow reference, not both")
    if run_id is None and workflow_id is None:
        if supplied_output_hash:
            raise HTTPException(422, "An output hash must be accompanied by an internal run or workflow reference")
        return {
            "provenance_verified": False,
            "reference_kind": None,
            "execution_status": None,
            "output_hash": None,
            "model_version": None,
            "output_payload": None,
        }

    if run_id is not None:
        row = db.get(ModelRun, run_id)
        if row is None:
            raise HTTPException(404, f"Model run {run_id} not found")
        if (row.project_id, row.chemical_id, row.model_key) != (
            project_id, chemical_id, model_key,
        ):
            raise HTTPException(422, "Model run does not belong to the selected project, chemical and model")
        binding = db.scalar(
            select(ModelRunIdentityBinding).where(
                ModelRunIdentityBinding.model_run_id == row.id
            )
        )
        if binding is None or binding.identity_hash != identity_hash:
            raise HTTPException(422, "Model run is not bound to the selected confirmed identity")
        actual_hash = _model_run_output_hash(row)
        if supplied_output_hash and supplied_output_hash.casefold() != actual_hash.casefold():
            raise HTTPException(422, "Supplied output hash does not match the referenced model run")
        execution_status = "completed" if row.status.startswith("completed") else row.status
        return {
            "provenance_verified": True,
            "reference_kind": "model_run",
            "execution_status": execution_status,
            "output_hash": actual_hash,
            "model_version": row.model_version,
            "run_id": row.id,
            "workflow_id": None,
            "output_payload": _model_run_output_payload(row),
        }

    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, f"Model workflow {workflow_id} not found")
    if (row.project_id, row.chemical_id, row.model_key) != (
        project_id, chemical_id, model_key,
    ):
        raise HTTPException(422, "Model workflow does not belong to the selected project, chemical and model")
    actual_hash = row.output_hash
    if supplied_output_hash and (
        actual_hash is None or supplied_output_hash.casefold() != actual_hash.casefold()
    ):
        raise HTTPException(422, "Supplied output hash does not match the referenced model workflow")
    return {
        "provenance_verified": bool(actual_hash),
        "reference_kind": "model_workflow",
        "execution_status": row.status,
        "output_hash": actual_hash,
        "model_version": row.model_version,
        "run_id": None,
        "workflow_id": row.id,
        "review_decision": row.review_decision,
        "jurisdiction": row.jurisdiction,
        "output_payload": json.loads(row.output_record_json) if row.output_record_json else None,
    }


def _validated_orchestration_payload(
    payload: OrchestratedAssessmentCreate,
    db: Session,
) -> tuple[dict, ChemicalIdentitySnapshot, dict]:
    if payload.contaminant_group not in CONTAMINANT_GROUPS:
        raise HTTPException(422, "Unsupported contaminant group")
    if payload.scenario not in SCENARIOS:
        raise HTTPException(422, "Unsupported exposure scenario")
    _, _, snapshot, identity = _orchestration_identity(
        db, payload.project_id, payload.chemical_id
    )
    data = payload.model_dump(mode="json")
    tier_sequence = build_tier_sequence(data)
    applicable_by_tier = {
        stage["tier"]: {model["key"] for model in stage["models"]}
        for stage in tier_sequence
    }

    validated_results: list[dict] = []
    for result in data["model_results"]:
        model = _orchestration_model(result["model_key"])
        if result["jurisdiction"] not in model["regions"]:
            raise HTTPException(
                422,
                f"{model['name']} is not registered for {result['jurisdiction']}",
            )
        tier_ok = result["tier"] in model["tiers"] or (
            result["tier"] > max(model["tiers"]) and max(model["tiers"]) >= 3
        )
        if not tier_ok or result["tier"] > payload.current_tier:
            raise HTTPException(422, f"{model['name']} result is not valid at the declared current tier")
        if (
            payload.assessment_mode == "regulatory"
            and result["model_key"] not in applicable_by_tier[result["tier"]]
        ):
            raise HTTPException(
                422,
                f"{model['name']} is not part of this jurisdiction, use, release and tier route",
            )
        reference = _validated_execution_reference(
            db,
            project_id=payload.project_id,
            chemical_id=payload.chemical_id,
            identity_hash=snapshot.identity_hash,
            model_key=result["model_key"],
            run_id=result.get("run_id"),
            workflow_id=result.get("workflow_id"),
            supplied_output_hash=result.get("output_hash"),
        )
        if reference.get("jurisdiction") and reference["jurisdiction"] != result["jurisdiction"]:
            raise HTTPException(422, "Model workflow jurisdiction does not match the declared result")
        if result.get("run_id") or result.get("workflow_id"):
            result["execution_status"] = reference["execution_status"]
            result["output_hash"] = reference["output_hash"]
            result["model_version"] = reference["model_version"] or result.get("model_version")
        else:
            result["execution_status"] = "not_started"
        result["provenance_verified"] = reference["provenance_verified"]
        if result["alignment_claim"] == "regulatory_accepted":
            alignment_verified = (
                reference.get("reference_kind") == "model_workflow"
                and reference.get("review_decision") == "accepted"
                and reference.get("provenance_verified")
                and result["model_key"] in OFFICIAL_REGULATORY_WORKFLOW_KEYS
            )
            if not alignment_verified:
                result["alignment_claim"] = (
                    "research_screen" if reference.get("reference_kind") == "model_run"
                    else "adapted_method"
                )
                result["alignment_validation"] = "requested regulatory alignment was not supported by a reviewed official workflow and was downgraded"
            else:
                result["alignment_validation"] = "reviewed official workflow provenance verified"
        result["declared_output_values_status"] = (
            "declared_against_hashed_execution_not_machine_reconciled"
            if result.get("outputs") and reference["provenance_verified"]
            else "no_declared_output_values" if not result.get("outputs")
            else "unverified_declared_values"
        )
        validated_results.append(result)
    data["model_results"] = validated_results

    validated_risks: list[dict] = []
    for risk in data["risk_characterisations"]:
        _validate_benchmark_evidence(
            db,
            risk=risk,
            project_id=payload.project_id,
            chemical_id=payload.chemical_id,
            jurisdiction=payload.jurisdiction,
        )
        if risk.get("model_key"):
            risk_model = _orchestration_model(risk["model_key"])
            if (
                payload.assessment_mode == "regulatory"
                and payload.jurisdiction not in risk_model["regions"]
            ):
                raise HTTPException(
                    422,
                    "A single-jurisdiction regulatory risk result cannot use a model from another jurisdiction",
                )
        if risk.get("exposure_run_id") or risk.get("exposure_workflow_id"):
            if not risk.get("model_key"):
                raise HTTPException(422, "A model_key is required for an internal exposure reference")
            reference = _validated_execution_reference(
                db,
                project_id=payload.project_id,
                chemical_id=payload.chemical_id,
                identity_hash=snapshot.identity_hash,
                model_key=risk["model_key"],
                run_id=risk.get("exposure_run_id"),
                workflow_id=risk.get("exposure_workflow_id"),
                supplied_output_hash=risk.get("exposure_output_hash"),
            )
            if not reference["provenance_verified"]:
                raise HTTPException(422, "Referenced exposure has no genuine hashed output")
            risk["exposure_output_hash"] = reference["output_hash"]
            reconciliation = _reconcile_exposure_value(risk, reference["output_payload"])
            execution_eligible = (
                reference["reference_kind"] == "model_run"
                and reference["execution_status"] in {"completed", "reviewed"}
            ) or (
                reference["reference_kind"] == "model_workflow"
                and reference["execution_status"] == "reviewed"
                and reference.get("review_decision") == "accepted"
            )
            risk["exposure_value_verified"] = bool(reconciliation["verified"] and execution_eligible)
            if reconciliation["verified"] and not execution_eligible:
                reconciliation["status"] = "value_matched_but_execution_not_reviewed"
                reconciliation["message"] = "The endpoint value matches, but the referenced execution is not complete/reviewed."
            risk["exposure_reconciliation"] = reconciliation
        validated_risks.append(risk)
    data["risk_characterisations"] = validated_risks
    return data, snapshot, identity


def _orchestrated_assessment_dict(row: OrchestratedAssessmentRecord) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "chemical_id": row.chemical_id,
        "identity_snapshot_id": row.identity_snapshot_id,
        "supersedes_id": row.supersedes_id,
        "jurisdiction": row.jurisdiction,
        "contaminant_group": row.contaminant_group,
        "scenario": row.scenario,
        "current_tier": row.current_tier,
        "maximum_tier": row.maximum_tier,
        "assessment_mode": row.assessment_mode,
        "status": row.status,
        "record_hash": row.record_hash,
        "reviewer": row.reviewer,
        "review_decision": row.review_decision,
        "review_rationale": row.review_rationale,
        "stated_purpose": row.stated_purpose,
        "created_at": row.created_at.isoformat(),
        "record": json.loads(row.record_json),
    }


@app.get("/api/orchestration/manifest")
def get_orchestration_manifest():
    return orchestration_manifest()


@app.get("/api/orchestration/model-contracts")
def get_orchestration_model_contracts():
    return semantic_contract_catalogue()


@app.get("/api/orchestration/specialist-substance-groups")
def get_specialist_substance_group_requirements():
    """Expose evidenced requirements without claiming executable specialist rules."""

    return specialist_substance_group_requirements()


@app.get("/api/orchestration/specialist-substance-groups")
def get_specialist_substance_groups():
    """Expose implementation requirements without claiming an executable method."""

    return specialist_substance_group_requirements()


@app.post("/api/orchestration/plan")
def orchestration_plan(payload: OrchestrationPlanCreate):
    if payload.contaminant_group not in CONTAMINANT_GROUPS:
        raise HTTPException(422, "Unsupported contaminant group")
    if payload.scenario not in SCENARIOS:
        raise HTTPException(422, "Unsupported exposure scenario")
    try:
        sequence = build_tier_sequence(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "context": payload.model_dump(mode="json"),
        "tier_sequence": sequence,
        "boundary": "A routed plan identifies applicable work; it does not claim those models have been executed.",
    }


@app.post("/api/orchestration/harmonise")
def orchestration_harmonise(payload: OrchestrationHarmoniseCreate):
    try:
        return harmonise_quantity(
            payload.quantity.model_dump(mode="json"), payload.target_unit
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/orchestration/compatibility")
def orchestration_compatibility(payload: OrchestrationCompatibilityCreate):
    return check_endpoint_compatibility(
        payload.source.model_dump(mode="json"),
        payload.target.model_dump(mode="json"),
        allow_unspecified=payload.allow_unspecified,
    )


@app.post("/api/orchestration/model-compatibility")
def orchestration_model_compatibility(payload: ModelPortCompatibilityCreate):
    return model_port_compatibility(**payload.model_dump(mode="json"))


@app.post("/api/orchestration/risk-characterise")
def orchestration_risk_characterise(payload: RiskCharacterisationCreate):
    if payload.benchmark_evidence_ids:
        raise HTTPException(
            422,
            "Evidence-bound risk characterisation requires an assessment preview or saved assessment with project and chemical context",
        )
    try:
        return characterise_risk(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/orchestration/compare")
def orchestration_compare(payload: CrossJurisdictionComparisonCreate):
    try:
        return compare_jurisdictional_results(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/orchestration/preview")
def preview_orchestrated_assessment(
    payload: OrchestratedAssessmentCreate,
    db: Session = Depends(get_db),
):
    data, _, identity = _validated_orchestration_payload(payload, db)
    try:
        return build_assessment_record(data, identity)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/orchestration/assessments", status_code=201)
def create_orchestrated_assessment(
    payload: OrchestratedAssessmentCreate,
    db: Session = Depends(get_db),
):
    data, snapshot, identity = _validated_orchestration_payload(payload, db)
    try:
        record = build_assessment_record(data, identity)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = OrchestratedAssessmentRecord(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        identity_snapshot_id=snapshot.id,
        jurisdiction=payload.jurisdiction,
        contaminant_group=payload.contaminant_group,
        scenario=payload.scenario,
        current_tier=payload.current_tier,
        maximum_tier=payload.maximum_tier,
        assessment_mode=payload.assessment_mode,
        status="assessment_snapshot",
        record_json=json.dumps(record, sort_keys=True),
        record_hash=record["record_hash"],
    )
    db.add(row)
    db.flush()
    audit(db, row.project_id, "orchestrated_assessment", row.id, "assessment_snapshot_created", {
        "record_hash": row.record_hash,
        "identity_hash": snapshot.identity_hash,
        "jurisdiction": row.jurisdiction,
        "current_tier": row.current_tier,
        "gate_action": record["current_tier_decision"]["action"],
        "regulatory_status": record["regulatory_status"]["code"],
    })
    db.commit()
    db.refresh(row)
    return _orchestrated_assessment_dict(row)


@app.get("/api/projects/{project_id}/orchestrated-assessments")
def list_orchestrated_assessments(
    project_id: int,
    chemical_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    statement = select(OrchestratedAssessmentRecord).where(
        OrchestratedAssessmentRecord.project_id == project_id
    )
    if chemical_id is not None:
        statement = statement.where(OrchestratedAssessmentRecord.chemical_id == chemical_id)
    rows = list(db.scalars(
        statement.order_by(OrchestratedAssessmentRecord.created_at.desc())
    ).all())
    return [_orchestrated_assessment_dict(row) for row in rows]


@app.get("/api/orchestration/assessments/{assessment_id}")
def get_orchestrated_assessment(assessment_id: int, db: Session = Depends(get_db)):
    row = db.get(OrchestratedAssessmentRecord, assessment_id)
    if row is None:
        raise HTTPException(404, "Orchestrated assessment not found")
    return _orchestrated_assessment_dict(row)


@app.post("/api/orchestration/assessments/{assessment_id}/finalise", status_code=201)
def finalise_orchestrated_assessment(
    assessment_id: int,
    payload: OrchestratedAssessmentFinaliseCreate,
    db: Session = Depends(get_db),
):
    row = db.get(OrchestratedAssessmentRecord, assessment_id)
    if row is None:
        raise HTTPException(404, "Orchestrated assessment not found")
    if row.status == "finalised_review_record":
        raise HTTPException(409, "This immutable assessment has already been finalised")
    existing_successor = db.scalar(
        select(OrchestratedAssessmentRecord).where(
            OrchestratedAssessmentRecord.supersedes_id == row.id
        )
    )
    if existing_successor is not None:
        raise HTTPException(409, "This immutable assessment already has a final review successor")
    record = json.loads(row.record_json)
    record.pop("record_hash", None)
    record["supersedes_record_id"] = row.id
    record["finalised_at"] = datetime.now(timezone.utc).isoformat()
    record["review"] = payload.model_dump(mode="json")
    record["overall_conclusion"]["final_regulatory_decision"] = False
    record["overall_conclusion"]["review_decision"] = payload.decision
    record["record_hash"] = orchestration_record_hash(record)
    successor = OrchestratedAssessmentRecord(
        project_id=row.project_id,
        chemical_id=row.chemical_id,
        identity_snapshot_id=row.identity_snapshot_id,
        supersedes_id=row.id,
        jurisdiction=row.jurisdiction,
        contaminant_group=row.contaminant_group,
        scenario=row.scenario,
        current_tier=row.current_tier,
        maximum_tier=row.maximum_tier,
        assessment_mode=row.assessment_mode,
        status="finalised_review_record",
        record_json=json.dumps(record, sort_keys=True),
        record_hash=record["record_hash"],
        reviewer=payload.reviewer,
        review_decision=payload.decision,
        review_rationale=payload.rationale,
        stated_purpose=payload.stated_purpose,
    )
    db.add(successor)
    db.flush()
    audit(db, successor.project_id, "orchestrated_assessment", successor.id, "review_record_finalised", {
        "supersedes_id": row.id,
        "record_hash": successor.record_hash,
        "decision": payload.decision,
        "reviewer": payload.reviewer,
        "final_regulatory_decision": False,
    })
    db.commit()
    db.refresh(successor)
    return _orchestrated_assessment_dict(successor)


@app.get("/api/orchestration/assessments/{assessment_id}/export")
def export_orchestrated_assessment(assessment_id: int, db: Session = Depends(get_db)):
    row = db.get(OrchestratedAssessmentRecord, assessment_id)
    if row is None:
        raise HTTPException(404, "Orchestrated assessment not found")
    payload = json.dumps(json.loads(row.record_json), indent=2, sort_keys=True).encode("utf-8")
    filename = f"FateIntel_assessment_{row.id}_{row.record_hash[:12]}.json"
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _workflow_dict(row: ModelWorkflow) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "chemical_id": row.chemical_id,
        "model_key": row.model_key,
        "jurisdiction": row.jurisdiction,
        "tier": row.tier,
        "scenario_name": row.scenario_name,
        "implementation": row.implementation,
        "status": row.status,
        "executable_path": row.executable_path,
        "model_version": row.model_version,
        "executable_version": row.executable_version,
        "manifest": json.loads(row.input_manifest_json),
        "expected_outputs": json.loads(row.expected_outputs_json),
        "output_record": json.loads(row.output_record_json) if row.output_record_json else None,
        "input_hash": row.input_hash,
        "output_hash": row.output_hash,
        "review_decision": row.review_decision,
        "reviewer": row.reviewer,
        "review_notes": row.review_notes,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@app.post("/api/model-workflows")
def create_model_workflow(payload: ModelWorkflowCreate, db: Session = Depends(get_db)):
    project = db.get(Project, payload.project_id)
    chemical = db.get(Chemical, payload.chemical_id)
    if project is None or chemical is None:
        raise HTTPException(404, "Project or chemical not found")
    model = next((x for x in MODELS if x["key"] == payload.model_key), None)
    if model is None:
        raise HTTPException(422, "Unknown model key")
    if payload.jurisdiction not in model["regions"]:
        raise HTTPException(422, f"{model['name']} is not registered for {payload.jurisdiction}")
    if payload.tier not in model["tiers"]:
        raise HTTPException(422, f"{model['name']} is not registered for Tier {payload.tier}")
    if payload.model_key in {"PWC", "TOXSWA", "AGDRIFT", "TERRPLANT", "TREX", "BEEREX"} and payload.input_data.get("contaminant_group") != "pesticide":
        raise HTTPException(422, f"{model['name']} official workflow requires contaminant_group=pesticide")
    manifest = prepare_workflow_manifest(payload.model_dump(), model)
    row = ModelWorkflow(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key=model["key"],
        jurisdiction=payload.jurisdiction,
        tier=payload.tier,
        scenario_name=payload.scenario_name,
        implementation=model["implementation"],
        status="prepared" if not manifest["missing_inputs"] else "inputs_required",
        executable_path=payload.executable_path,
        input_manifest_json=json.dumps(manifest, sort_keys=True),
        expected_outputs_json=json.dumps(manifest["expected_outputs"], sort_keys=True),
        input_hash=manifest["input_hash"],
    )
    db.add(row)
    db.flush()
    audit(db, row.project_id, "model_workflow", row.id, "prepared", {
        "model_key": row.model_key, "jurisdiction": row.jurisdiction, "tier": row.tier,
        "status": row.status, "input_hash": row.input_hash,
        "missing_inputs": manifest["missing_inputs"],
    })
    db.commit()
    db.refresh(row)
    return _workflow_dict(row)


@app.get("/api/projects/{project_id}/model-workflows")
def list_model_workflows(project_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(ModelWorkflow).where(ModelWorkflow.project_id == project_id).order_by(ModelWorkflow.created_at.desc())
    ).all())
    return [_workflow_dict(row) for row in rows]


@app.get("/api/model-workflows/{workflow_id}")
def get_model_workflow(workflow_id: int, db: Session = Depends(get_db)):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    return _workflow_dict(row)


@app.get("/api/model-workflows/{workflow_id}/manifest")
def download_model_workflow_manifest(workflow_id: int, db: Session = Depends(get_db)):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    target = BASE_DIR.parent / "data" / f"model_workflow_{row.id}_{row.model_key}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(row.input_manifest_json, encoding="utf-8")
    return FileResponse(target, filename=target.name, media_type="application/json")


@app.get("/api/model-workflows/{workflow_id}/handoff")
def download_model_workflow_handoff(workflow_id: int, db: Session = Depends(get_db)):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    workflow = _workflow_dict(row)
    profile = external_integration_profile(row.model_key)
    tool_status = external_tool_status(row.model_key) if row.model_key in EPA_EXECUTION_MODEL_KEYS else None
    payload = build_handoff_bundle(workflow=workflow, profile=profile, tool_status=tool_status)
    filename = f"FateIntel_workflow_{row.id}_{row.model_key}_official_handoff.zip"
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/model-workflows/{workflow_id}/execute")
def execute_model_workflow(
    workflow_id: int, payload: ModelWorkflowExecute, db: Session = Depends(get_db)
):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    if row.model_key not in EPA_EXECUTION_MODEL_KEYS:
        raise HTTPException(409, "This model uses a manual or model-specific execution route")
    if row.status == "inputs_required":
        raise HTTPException(409, "Complete every required workflow input before execution")
    if row.status in {"reviewed", "rejected"}:
        raise HTTPException(409, "Create a new workflow revision rather than re-running a closed review record")
    manifest = json.loads(row.input_manifest_json)
    try:
        execution = execute_configured_tool(
            model_key=row.model_key,
            workflow_id=row.id,
            manifest=manifest,
            expected_executable_sha256=payload.expected_executable_sha256,
            operator=payload.operator,
            installed_version=payload.installed_version,
        )
    except ExternalExecutionError as exc:
        raise HTTPException(409, str(exc)) from exc

    captured_text = [
        value for value in [execution["stdout"]["excerpt"], execution["stderr"]["excerpt"]] if value
    ]
    execution_workspace = Path(execution["workspace"])
    for artifact in execution["artifacts"]:
        artifact_path = execution_workspace / artifact["relative_path"]
        if artifact_path.suffix.casefold() in {".txt", ".csv"} and artifact["size_bytes"] <= 1024 * 1024:
            captured_text.append(
                f"# FILE: {artifact['relative_path']}\n" + artifact_path.read_text(encoding="utf-8", errors="replace")
            )
    combined_log = "\n\n".join(captured_text) or None
    output_record = normalise_imported_output(combined_log, {})
    output_record.pop("output_hash", None)
    output_record["execution_provenance"] = execution
    output_record["source_files"] = execution["artifacts"]
    output_record["structured_outputs"].setdefault("model_version", payload.installed_version)
    output_record["structured_outputs"].setdefault("raw_output_archive", {
        "artifact_set_sha256": execution["artifact_set_sha256"],
        "files": execution["artifacts"],
    })
    model_validation = validate_external_model_output(row.model_key, output_record["structured_outputs"])
    if model_validation:
        output_record["model_specific_validation"] = model_validation
    output_record["output_hash"] = sha256_payload(output_record)
    row.output_record_json = json.dumps(output_record, sort_keys=True)
    row.output_hash = output_record["output_hash"]
    row.executable_path = execution["executable_path"]
    row.model_version = payload.installed_version
    row.executable_version = payload.installed_version
    row.status = "execution_captured" if execution["succeeded"] else "execution_failed"
    audit(db, row.project_id, "model_workflow", row.id, row.status, {
        "model_key": row.model_key,
        "operator": payload.operator,
        "executable_sha256": execution["executable_sha256"],
        "exit_code": execution["exit_code"],
        "artifact_set_sha256": execution["artifact_set_sha256"],
        "output_hash": row.output_hash,
    })
    db.commit()
    db.refresh(row)
    return _workflow_dict(row)


MAX_OFFICIAL_OUTPUT_FILE_BYTES = 25 * 1024 * 1024
MAX_OFFICIAL_OUTPUT_SET_BYTES = 50 * 1024 * 1024
MAX_OFFICIAL_OUTPUT_FILES = 20


@app.post("/api/model-workflows/{workflow_id}/import-output-files")
async def import_model_workflow_output_files(
    workflow_id: int,
    files: list[UploadFile] = File(...),
    model_version: str = Form(...),
    executable_version: str = Form(...),
    operator: str = Form(...),
    execution_notes: str = Form(...),
    structured_outputs_json: str = Form("{}"),
    confirm_genuine_execution: bool = Form(False),
    confirm_authorised_installation: bool = Form(False),
    db: Session = Depends(get_db),
):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    if row.status in {"reviewed", "rejected"}:
        raise HTTPException(409, "This workflow has already been reviewed; create a new workflow revision rather than overwriting a closed review record")
    # Available to every registered model, not just EPA_EXECUTION_MODEL_KEYS: this
    # is the genuine, hashed-file, confirmation-gated import route, and every
    # official external model -- not only the four with a local execution bridge
    # -- needs a path to produce real execution_provenance before it can be
    # reviewed as accepted (see the /review gate below).
    if row.status == "inputs_required":
        raise HTTPException(409, "Complete every required workflow input before importing an official result")
    if not confirm_genuine_execution or not confirm_authorised_installation:
        raise HTTPException(422, "Confirm genuine execution in an authorised, separately installed official tool")
    if len(operator.strip()) < 2 or not model_version.strip() or not executable_version.strip() or len(execution_notes.strip()) < 2:
        raise HTTPException(422, "Operator, model version, executable version and execution notes are required")
    if not files or len(files) > MAX_OFFICIAL_OUTPUT_FILES:
        raise HTTPException(422, f"Provide between 1 and {MAX_OFFICIAL_OUTPUT_FILES} original output files")
    try:
        structured_outputs = json.loads(structured_outputs_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"structured_outputs_json is invalid: {exc.msg}") from exc
    if not isinstance(structured_outputs, dict):
        raise HTTPException(422, "structured_outputs_json must contain a JSON object")

    accepted = {suffix.casefold() for suffix in ADAPTER_CONTRACTS[row.model_key]["accepted_output_formats"]}
    import_root = BASE_DIR.parent / "data" / "model_workflows" / f"workflow_{row.id}" / "imports"
    import_root.mkdir(parents=True, exist_ok=True)
    import_dir = import_root / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:10]}"
    import_dir.mkdir(parents=False, exist_ok=False)
    records: list[dict] = []
    text_parts: list[str] = []
    total_bytes = 0
    try:
        for index, upload in enumerate(files, start=1):
            original_name = Path(upload.filename or f"output_{index}").name
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name).strip("._") or f"output_{index}"
            extension = Path(safe_name).suffix.casefold().lstrip(".")
            if extension not in accepted:
                raise HTTPException(422, f"{original_name}: expected one of {', '.join(sorted(accepted))}")
            target = import_dir / f"{index:02d}_{safe_name}"
            size = 0
            with target.open("wb") as handle:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    total_bytes += len(chunk)
                    if size > MAX_OFFICIAL_OUTPUT_FILE_BYTES or total_bytes > MAX_OFFICIAL_OUTPUT_SET_BYTES:
                        raise HTTPException(413, "Official output upload exceeds the 25 MB/file or 50 MB/set limit")
                    handle.write(chunk)
            record = {
                "original_name": original_name,
                "stored_relative_path": target.relative_to(BASE_DIR.parent).as_posix(),
                "size_bytes": size,
                "sha256": sha256_file(target),
                "content_type": upload.content_type,
            }
            records.append(record)
            if extension in {"txt", "csv"} and size <= 1024 * 1024:
                text_parts.append(f"# FILE: {original_name}\n{target.read_text(encoding='utf-8', errors='replace')}")
    except Exception:
        shutil.rmtree(import_dir, ignore_errors=True)
        raise

    file_set_hash = sha256_payload([{key: row[key] for key in ("original_name", "size_bytes", "sha256")} for row in records])
    structured_outputs.setdefault("model_version", model_version.strip())
    structured_outputs.setdefault("raw_output_archive", {"file_set_sha256": file_set_hash, "files": records})
    raw_text = "\n\n".join(text_parts) or None
    output_record = normalise_imported_output(raw_text, structured_outputs)
    output_record.pop("output_hash", None)
    output_record["source_files"] = records
    output_record["execution_provenance"] = {
        "real_execution": True,
        "method": "manual_official_installation",
        "operator": operator.strip(),
        "model_version": model_version.strip(),
        "executable_version": executable_version.strip(),
        "execution_notes": execution_notes.strip(),
        "confirmed_authorised_installation": True,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "file_set_sha256": file_set_hash,
    }
    model_validation = validate_external_model_output(row.model_key, output_record["structured_outputs"])
    if model_validation:
        output_record["model_specific_validation"] = model_validation
    output_record["output_hash"] = sha256_payload(output_record)
    row.output_record_json = json.dumps(output_record, sort_keys=True)
    row.output_hash = output_record["output_hash"]
    row.model_version = model_version.strip()
    row.executable_version = executable_version.strip()
    row.status = "output_imported"
    audit(db, row.project_id, "model_workflow", row.id, "official_output_files_imported", {
        "model_key": row.model_key,
        "operator": operator.strip(),
        "source_file_count": len(records),
        "source_file_set_sha256": file_set_hash,
        "output_hash": row.output_hash,
        "model_version": row.model_version,
        "executable_version": row.executable_version,
    })
    db.commit()
    db.refresh(row)
    return _workflow_dict(row)


@app.post("/api/model-workflows/{workflow_id}/import-output")
def import_model_workflow_output(
    workflow_id: int, payload: ModelWorkflowOutputImport, db: Session = Depends(get_db)
):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    if row.status in {"reviewed", "rejected"}:
        raise HTTPException(409, "This workflow has already been reviewed; create a new workflow revision rather than overwriting a closed review record")
    if row.model_key in EPA_EXECUTION_MODEL_KEYS:
        raise HTTPException(
            409,
            "Official EPA workflows require original output files; use /import-output-files or the controlled /execute bridge",
        )
    output_record = normalise_imported_output(payload.raw_output_text, payload.structured_outputs)
    model_validation = validate_external_model_output(row.model_key, output_record["structured_outputs"])
    if model_validation:
        output_record["model_specific_validation"] = model_validation
    output_record["execution_notes"] = payload.execution_notes
    row.output_record_json = json.dumps(output_record, sort_keys=True)
    row.output_hash = output_record["output_hash"]
    row.model_version = payload.model_version
    row.executable_version = payload.executable_version
    row.status = "output_imported"
    audit(db, row.project_id, "model_workflow", row.id, "output_imported", {
        "model_key": row.model_key, "output_hash": row.output_hash,
        "model_version": row.model_version, "executable_version": row.executable_version,
    })
    db.commit()
    db.refresh(row)
    return _workflow_dict(row)


@app.post("/api/model-workflows/{workflow_id}/review")
def review_model_workflow(
    workflow_id: int, payload: ModelWorkflowReview, db: Session = Depends(get_db)
):
    row = db.get(ModelWorkflow, workflow_id)
    if row is None:
        raise HTTPException(404, "Model workflow not found")
    if row.status in {"reviewed", "rejected"}:
        raise HTTPException(409, "This workflow has already been reviewed; create a new workflow revision rather than changing a closed review record")
    if not row.output_record_json:
        raise HTTPException(409, "Import model output before review")
    if payload.decision == "accepted":
        # Applies to every model, not just EPA_EXECUTION_MODEL_KEYS -- an
        # arbitrary plain-text /import-output paste (which never sets
        # execution_provenance) must never be acceptable as "reviewed" for any
        # official model. Genuine provenance comes from either real local
        # execution (the execution-bridge models) or a hashed-file import via
        # /import-output-files (available to every model).
        output_record = json.loads(row.output_record_json)
        provenance = output_record.get("execution_provenance") or {}
        validation = output_record.get("model_specific_validation") or {}
        if not provenance.get("real_execution"):
            raise HTTPException(409, "A genuine official execution or hashed-file import record is required before acceptance")
        missing_outputs = validation.get("missing_recommended_outputs") or []
        if missing_outputs:
            raise HTTPException(409, "Map the required reviewed outputs before acceptance: " + ", ".join(missing_outputs))
    row.reviewer = payload.reviewer
    row.review_decision = payload.decision
    row.review_notes = payload.notes
    row.status = "reviewed" if payload.decision == "accepted" else payload.decision
    audit(db, row.project_id, "model_workflow", row.id, "reviewed", {
        "model_key": row.model_key, "decision": payload.decision, "reviewer": payload.reviewer,
        "input_hash": row.input_hash, "output_hash": row.output_hash,
    })
    db.commit()
    db.refresh(row)
    return _workflow_dict(row)


@app.post("/api/home-use-summary")
def home_use_summary(payload: HomeUseSummaryCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if payload.bind_to_reviewed_profile:
        membership = db.get(ProjectChemical, {
            "project_id": payload.project_id,
            "chemical_id": payload.chemical_id,
        })
        if membership is None:
            raise HTTPException(404, "Chemical is not attached to the selected project")
        chemical = db.get(Chemical, payload.chemical_id)
        profile = _validated_run_profile(
            db,
            payload.assessment_profile_id,
            payload.project_id,
            payload.chemical_id,
        )
        snapshot = db.scalar(select(ChemicalIdentitySnapshot).where(
            ChemicalIdentitySnapshot.chemical_id == payload.chemical_id
        ))
        if snapshot is None:
            raise HTTPException(422, "A confirmed chemical identity is required for reviewed-profile binding")
        data["chemical_name"] = chemical.preferred_name
        data["log_kow"] = profile.log_kow
        data["soil_dt50_days"] = profile.soil_dt50_days
        data["reviewed_property_fields"] = [
            key for key in ("log_kow", "soil_dt50_days")
            if data.get(key) is not None
        ]
        data["identity_binding"] = {
            "project_id": payload.project_id,
            "chemical_id": chemical.id,
            "assessment_profile_id": profile.id,
            "preferred_name": chemical.preferred_name,
            "cas_number": chemical.cas_number,
            "identity_hash": snapshot.identity_hash,
            "profile_origin": profile.profile_origin,
            "profile_updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
    return build_home_use_summary(data)


@app.post("/api/lab/coshh-draft")
async def coshh_draft(
    sds_file: UploadFile = File(...),
    substance_name: str = Form(...),
    task_description: str = Form(...),
    quantity: str = Form(...),
    frequency: str = Form(...),
    persons_at_risk: str = Form("laboratory workers"),
    open_handling: bool = Form(True),
    heating_or_aerosol: bool = Form(False),
):
    raw = await sds_file.read()
    filename = (sds_file.filename or "").lower()
    text = ""
    if filename.endswith(".pdf"):
        try:
            from io import BytesIO
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(raw))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise HTTPException(422, f"Could not extract text from PDF: {exc}") from exc
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")
    if len(text.strip()) < 100:
        raise HTTPException(422, "The SDS contained too little extractable text")
    parsed = parse_sds_text(text)
    context = {
        "substance_name": substance_name,
        "task_description": task_description,
        "quantity": quantity,
        "frequency": frequency,
        "persons_at_risk": persons_at_risk,
        "open_handling": open_handling,
        "heating_or_aerosol": heating_or_aerosol,
    }
    return {"sds": parsed, "coshh_draft": build_coshh_draft(parsed, context)}


@app.get("/api/projects")
def list_projects(q: str | None = None, limit: int | None = None, db: Session = Depends(get_db)):
    """``q`` and ``limit`` are both optional and additive -- omitting them returns every project, exactly the
    existing behaviour relied on elsewhere (the project switcher, the example-loader's state.projects lookup).
    Added for the new "Saved assessments" view, which needs to search rather than load every project (2,300+
    accumulated test-fixture rows as of 2026-10-01, not yet cleaned -- see scripts/cleanup_db.py)."""
    stmt = select(Project).order_by(Project.created_at.desc())
    if q and q.strip():
        stmt = stmt.where(Project.name.ilike(f"%{q.strip()}%"))
    if limit is not None:
        stmt = stmt.limit(max(1, min(limit, 200)))
    rows = list(db.scalars(stmt).all())
    return [{
        "id": x.id, "name": x.name, "jurisdiction": x.jurisdiction,
        "purpose": x.purpose, "status": x.status,
        "created_at": x.created_at.isoformat(),
    } for x in rows]

@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    row = Project(**payload.model_dump())
    db.add(row)
    db.flush()
    audit(db, row.id, "project", row.id, "created", payload.model_dump())
    db.commit()
    return {"id": row.id, "name": row.name}

@app.get("/api/chemicals")
def list_chemicals(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Chemical).order_by(Chemical.preferred_name)).all())
    out = []
    for x in rows:
        item = _chemical_dict(x)
        snapshot = db.scalar(select(ChemicalIdentitySnapshot).where(ChemicalIdentitySnapshot.chemical_id == x.id))
        if snapshot is not None:
            saved = json.loads(snapshot.snapshot_json)
            item["identity_snapshot"] = {
                "source_key": snapshot.source_key,
                "source_record_id": snapshot.source_record_id,
                "source_url": snapshot.source_url,
                "identity_hash": snapshot.identity_hash,
                "confirmed_at": snapshot.confirmed_at.isoformat(),
            }
            item["structure_image_url"] = saved.get("structure_image_url")
        out.append(item)
    return out

@app.post("/api/projects/{project_id}/chemicals/{chemical_id}", status_code=201)
def add_chemical_to_project(project_id: int, chemical_id: int, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    if db.get(Chemical, chemical_id) is None:
        raise HTTPException(404, "Chemical not found")
    existing = db.get(ProjectChemical, {"project_id": project_id, "chemical_id": chemical_id})
    if existing is None:
        db.add(ProjectChemical(project_id=project_id, chemical_id=chemical_id))
        db.flush()
        audit(db, project_id, "chemical", chemical_id, "added_to_project", {})
    profile = _ensure_assessment_profile(db, project_id, db.get(Chemical, chemical_id))
    db.commit()
    return {"project_id": project_id, "chemical_id": chemical_id, "assessment_profile": _profile_dict(profile)}

@app.get("/api/projects/{project_id}/chemicals")
def list_project_chemicals(project_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Chemical)
        .join(ProjectChemical, Chemical.id == ProjectChemical.chemical_id)
        .where(ProjectChemical.project_id == project_id)
    )
    rows = list(db.scalars(stmt).all())
    return [{
        "id": x.id, "preferred_name": x.preferred_name,
        "cas_number": x.cas_number, "molecular_formula": x.molecular_formula,
        "molecular_weight_g_mol": x.molecular_weight_g_mol,
        "review_status": x.review_status,
    } for x in rows]

@app.post("/api/evidence", status_code=201)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Project not found")
    if db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Chemical not found")

    source = Source(**payload.source.model_dump())
    db.add(source)
    db.flush()

    row = EvidenceRecord(
        chemical_id=payload.chemical_id,
        source_id=source.id,
        property_code=payload.property_code,
        evidence_type=payload.evidence_type,
        original_value=payload.original_value,
        original_unit=payload.original_unit,
        soil_type=payload.soil_type,
        soil_texture=payload.soil_texture,
        soil_ph=payload.soil_ph,
        organic_carbon_percent=payload.organic_carbon_percent,
        temperature_c=payload.temperature_c,
        moisture_percent_whc=payload.moisture_percent_whc,
        kinetic_model=payload.kinetic_model,
        endpoint_kind=payload.endpoint_kind,
        test_guideline=payload.test_guideline,
        reliability_score=payload.reliability_score,
        representative_group_key=payload.representative_group_key,
        include_by_default=payload.include_by_default,
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    audit(
        db, payload.project_id, "evidence", row.id, "created",
        {"chemical_id": payload.chemical_id, "source_id": source.id,
         "property_code": payload.property_code}
    )
    db.commit()
    return {"id": row.id, "source_id": source.id}

@app.get("/api/projects/{project_id}/chemicals/{chemical_id}/evidence")
def list_evidence(
    project_id: int,
    chemical_id: int,
    property_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if db.get(ProjectChemical, {"project_id": project_id, "chemical_id": chemical_id}) is None:
        raise HTTPException(404, "Chemical is not attached to the selected project")
    conditions = [EvidenceRecord.chemical_id == chemical_id]
    if property_code:
        conditions.append(EvidenceRecord.property_code == property_code)
    stmt = (
        select(EvidenceRecord)
        .where(*conditions)
        .order_by(EvidenceRecord.property_code, EvidenceRecord.id)
    )
    rows = list(db.scalars(stmt).all())
    out = []
    for x in rows:
        provenance_payload = {
            "chemical_id": x.chemical_id,
            "source": {
                "title": x.source.title,
                "organisation": x.source.organisation,
                "publication_year": x.source.publication_year,
                "identifier": x.source.identifier,
                "url": x.source.url,
            },
            "property_code": x.property_code,
            "evidence_type": x.evidence_type,
            "original_value": x.original_value,
            "original_unit": x.original_unit,
            "endpoint_kind": x.endpoint_kind,
            "test_guideline": x.test_guideline,
            "reliability_score": x.reliability_score,
            "representative_group_key": x.representative_group_key,
            "notes": x.notes,
        }
        out.append({
            "id": x.id,
            "source": {
                "id": x.source.id,
                "title": x.source.title,
                "organisation": x.source.organisation,
                "publication_year": x.source.publication_year,
                "identifier": x.source.identifier,
                "url": x.source.url,
            },
            "property_code": x.property_code,
            "evidence_type": x.evidence_type,
            "original_value": x.original_value,
            "original_unit": x.original_unit,
            "soil_type": x.soil_type,
            "soil_texture": x.soil_texture,
            "soil_ph": x.soil_ph,
            "organic_carbon_percent": x.organic_carbon_percent,
            "temperature_c": x.temperature_c,
            "moisture_percent_whc": x.moisture_percent_whc,
            "kinetic_model": x.kinetic_model,
            "endpoint_kind": x.endpoint_kind,
            "test_guideline": x.test_guideline,
            "reliability_score": x.reliability_score,
            "representative_group_key": x.representative_group_key,
            "include_by_default": x.include_by_default,
            "notes": x.notes,
            "provenance_hash": sha256(json.dumps(
                provenance_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")).hexdigest(),
        })
    return out

@app.post("/api/evidence/demo/{project_id}/{chemical_id}")
def add_demo_evidence(project_id: int, chemical_id: int, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(EvidenceRecord.id).where(EvidenceRecord.chemical_id == chemical_id).limit(1)
    )
    if existing is not None:
        return {"created": 0, "message": "Evidence already exists"}

    demo = [
        ("Demonstration soil study A", "DEMO-A", 12, "sandy loam", 10, 1, "soil-A"),
        ("Demonstration soil study B", "DEMO-B", 43, "loam", 20, 1, "soil-B"),
        ("Demonstration soil study C", "DEMO-C", 80, "clay loam", 25, 2, "soil-C"),
        ("Demonstration soil study D", "DEMO-D", 110, "silt loam", 15, 2, "soil-D"),
    ]
    for title, ident, value, soil, temp, reliability, group in demo:
        source = Source(
            source_type="test_report",
            title=title,
            organisation="Prototype demonstration only",
            publication_year=2026,
            identifier=ident,
            access_date="2026-07-29",
        )
        db.add(source)
        db.flush()
        db.add(EvidenceRecord(
            chemical_id=chemical_id,
            source_id=source.id,
            property_code="FATE.SOIL_DT50",
            evidence_type="measured",
            original_value=value,
            original_unit="days",
            soil_type=soil,
            soil_texture=soil,
            temperature_c=temp,
            moisture_percent_whc=50,
            kinetic_model="SFO",
            endpoint_kind="DegT50",
            test_guideline="OECD 307",
            reliability_score=reliability,
            representative_group_key=group,
            include_by_default=True,
            notes="Demonstration record only. Replace with genuine curated evidence.",
        ))
    audit(db, project_id, "evidence_batch", chemical_id, "demo_created", {"count": 4})
    db.commit()
    return {"created": 4}

@app.post("/api/selections/calculate")
def calculate(payload: SelectionCalculate, db: Session = Depends(get_db)):
    stmt = select(EvidenceRecord).where(
        EvidenceRecord.chemical_id == payload.chemical_id,
        EvidenceRecord.property_code == "FATE.SOIL_DT50",
    )
    evidence = list(db.scalars(stmt).all())
    result = calculate_selection(
        evidence,
        payload.target_temperature_c,
        payload.activation_energy_kj_mol,
        payload.max_reliability_score,
    )

    row = SelectionSet(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        target_temperature_c=payload.target_temperature_c,
        activation_energy_kj_mol=payload.activation_energy_kj_mol,
        max_reliability_score=payload.max_reliability_score,
        selected_value_days=result["selected_value_days"],
        rationale=result["reason"],
        statistics_json=json.dumps(result["statistics"], sort_keys=True),
    )
    db.add(row)
    db.flush()

    for m in result["members"]:
        db.add(SelectionMember(
            selection_set_id=row.id,
            evidence_id=m["evidence_id"],
            decision=m["decision"],
            reason=m["reason"],
            normalised_value_days=m["normalised_value_days"],
            representative_value_days=m["representative_value_days"],
            transformations_json=json.dumps(m["transformations"], sort_keys=True),
        ))
    audit(db, payload.project_id, "selection_set", row.id, "calculated", result)
    db.commit()
    result["selection_set_id"] = row.id
    return result

@app.post("/api/selections/lock")
def lock_selection(payload: SelectionLock, db: Session = Depends(get_db)):
    row = db.get(SelectionSet, payload.selection_set_id)
    if row is None:
        raise HTTPException(404, "Selection set not found")
    if row.selected_value_days is None:
        raise HTTPException(422, "Selection has no selected value")

    members = list(row.members)
    hash_payload = {
        "selection_set_id": row.id,
        "project_id": row.project_id,
        "chemical_id": row.chemical_id,
        "property_code": row.property_code,
        "ruleset_version": row.ruleset_version,
        "target_temperature_c": row.target_temperature_c,
        "activation_energy_kj_mol": row.activation_energy_kj_mol,
        "max_reliability_score": row.max_reliability_score,
        "selected_value_days": row.selected_value_days,
        "members": [{
            "evidence_id": x.evidence_id,
            "decision": x.decision,
            "reason": x.reason,
            "normalised_value_days": x.normalised_value_days,
            "representative_value_days": x.representative_value_days,
            "transformations_json": x.transformations_json,
        } for x in sorted(members, key=lambda x: x.evidence_id)],
    }
    row.evidence_hash = evidence_hash(hash_payload)
    row.status = "locked"
    row.rationale = payload.rationale
    row.locked_at = datetime.now(timezone.utc)
    audit(
        db, row.project_id, "selection_set", row.id, "locked",
        {"evidence_hash": row.evidence_hash, "rationale": payload.rationale}
    )
    db.commit()
    return {
        "selection_set_id": row.id,
        "status": row.status,
        "selected_value_days": row.selected_value_days,
        "evidence_hash": row.evidence_hash,
        "rationale": row.rationale,
    }

@app.get("/api/projects/{project_id}/selections")
def list_selections(project_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(SelectionSet)
        .where(SelectionSet.project_id == project_id)
        .order_by(SelectionSet.id.desc())
    ).all())
    return [{
        "id": x.id,
        "chemical_id": x.chemical_id,
        "property_code": x.property_code,
        "status": x.status,
        "selected_value_days": x.selected_value_days,
        "evidence_hash": x.evidence_hash,
        "rationale": x.rationale,
        "statistics": json.loads(x.statistics_json) if x.statistics_json else {},
        "created_at": x.created_at.isoformat(),
    } for x in rows]


@app.post("/api/model-runs/sorption")
def create_sorption_run(payload: SorptionRunCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Project not found")
    if db.get(Chemical, payload.chemical_id) is None:
        raise HTTPException(404, "Chemical not found")
    profile = _validated_run_profile(db, payload.assessment_profile_id, payload.project_id, payload.chemical_id)
    if profile is not None:
        mismatches = []
        if payload.mode != profile.ionisation_class:
            mismatches.append("ionisation_class")
        if profile.log_kow is None or abs(payload.log_kow - profile.log_kow) > 1e-10:
            mismatches.append("log_kow")
        if profile.ionisation_class == "acid" and (payload.pkaa is None or profile.pkaa is None or abs(payload.pkaa - profile.pkaa) > 1e-10):
            mismatches.append("pkaa")
        if profile.ionisation_class == "base" and (payload.pkab is None or profile.pkab is None or abs(payload.pkab - profile.pkab) > 1e-10):
            mismatches.append("pkab")
        if mismatches:
            raise HTTPException(422, "Sorption inputs differ from the reviewed assessment profile: " + ", ".join(mismatches))
    try:
        output = run_sorption_model(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    assumptions = (
        output["selected"].get("assumptions", [])
        + output.get("global_warnings", [])
    )
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_SORPTION",
        model_version="0.2.0",
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(assumptions),
        evidence_hash=_profile_hash(profile) if profile is not None else None,
    )
    db.add(row)
    db.flush()
    audit(
        db, payload.project_id, "model_run", row.id, "sorption_completed",
        {
            "model_key": row.model_key,
            "ionisation_class": output["ionisation_class"],
            "selected_model": output["selected"]["model_key"],
            "koc_l_kg": output["selected"]["koc_l_kg"],
            "kd_l_kg": output["selected"]["kd_l_kg"],
        },
    )
    db.commit()
    return {"model_run_id": row.id, "outputs": output}




@app.get("/api/pharmaceutical-consumption/oecd-2025")
def pharmaceutical_consumption_oecd_2025():
    """Return the reviewed static snapshot transcribed from OECD Health at a Glance 2025 Figure 9.6."""
    return oecd_2025_registry()


@app.get("/api/pharmaceutical-consumption/oecd-2025/lookup")
def pharmaceutical_consumption_oecd_2025_lookup(
    class_key: str = Query(..., min_length=2),
    country: str = Query(..., min_length=2),
):
    try:
        return oecd_2025_lookup(class_key, country)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/pharmaceutical-consumption/oecd-live")
def pharmaceutical_consumption_oecd_live(
    atc_code: str = Query(..., min_length=1, max_length=12),
    year: int | None = Query(default=None, ge=1990, le=2100),
    fetch: bool = Query(default=False),
):
    """Build or, when explicitly requested, execute an auditable OECD SDMX query.

    The network result is returned as unselected evidence; EnviroChem never silently
    promotes a live OECD row to a modelling input.
    """
    try:
        if not fetch:
            return {
                "atc_code": atc_code.upper(),
                "requested_year": year,
                "query_url": oecd_live_query_url(atc_code, year),
                "status": "query_prepared_not_fetched",
                "selection_status": "unselected",
            }
        result = fetch_oecd_live(atc_code, year)
        result["selection_status"] = "unselected"
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/model-runs/emission")
def create_emission_run(
    payload: PharmaceuticalEmissionRunCreate,
    db: Session = Depends(get_db),
):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Project not found")
    chemical = db.get(Chemical, payload.chemical_id)
    if chemical is None:
        raise HTTPException(404, "Chemical not found")
    if db.get(ProjectChemical, {"project_id": payload.project_id, "chemical_id": payload.chemical_id}) is None:
        raise HTTPException(422, "Chemical is not attached to the selected project")
    normalise = lambda value: "".join(character for character in str(value or "").casefold() if character.isalnum())
    if normalise(payload.parent_name) != normalise(chemical.preferred_name):
        raise HTTPException(422, "Emission parent name does not match the selected chemical identity")
    if chemical.molecular_weight_g_mol is not None:
        tolerance = max(0.01, abs(chemical.molecular_weight_g_mol) * 0.001)
        if abs(payload.parent_molecular_weight_g_mol - chemical.molecular_weight_g_mol) > tolerance:
            raise HTTPException(422, "Emission parent molecular weight does not match the selected chemical identity")
    try:
        output = run_pharmaceutical_emission(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_PHARMACEUTICAL_EMISSION",
        model_version="2.0.0",
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(output["assumptions"]),
        evidence_hash=None,
    )
    db.add(row)
    db.flush()
    audit(
        db, payload.project_id, "model_run", row.id, "emission_completed",
        {
            "model_key": row.model_key,
            "mode": output["emission_mode"],
            "population": output["population"],
            "flow_m3_day": output["wastewater_flow_m3_day"],
            "species_count": len(output["species"]),
            "parent_influent_ug_l": output["species"][0]["influent_concentration_ug_l"],
        },
    )
    db.commit()
    return {"model_run_id": row.id, "outputs": output}


@app.get("/api/projects/{project_id}/emission-runs")
def list_emission_runs(project_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(ModelRun)
        .where(
            ModelRun.project_id == project_id,
            ModelRun.model_key == "ENVIROCHEM_PHARMACEUTICAL_EMISSION",
        )
        .order_by(ModelRun.id.desc())
    ).all())
    return [{
        "model_run_id": row.id,
        "chemical_id": row.chemical_id,
        "scenario_name": row.scenario_name,
        "outputs": json.loads(row.output_json),
        "created_at": row.created_at.isoformat(),
    } for row in rows]


@app.post("/api/model-runs/activity-simpletreat")
def create_activity_simpletreat_run(
    payload: ActivitySimpleTreatRunCreate,
    db: Session = Depends(get_db),
):
    emission_run = db.get(ModelRun, payload.emission_model_run_id)
    if emission_run is None or emission_run.model_key != "ENVIROCHEM_PHARMACEUTICAL_EMISSION":
        raise HTTPException(404, "Emission & Metabolism run not found")
    if emission_run.project_id != payload.project_id or emission_run.chemical_id != payload.chemical_id:
        raise HTTPException(422, "Emission run does not belong to the selected project and chemical")
    chemical = db.get(Chemical, payload.chemical_id)
    if chemical is None:
        raise HTTPException(404, "Chemical not found")
    profile = _validated_run_profile(
        db,
        payload.assessment_profile_id,
        payload.project_id,
        payload.chemical_id,
    )
    if profile is not None:
        expected_mode = (
            "supplied_workbook_9box_preset"
            if profile.profile_origin == "protected_carbamazepine_benchmark"
            and chemical.cas_number == "298-46-4"
            and chemical.substance_form == "parent"
            else "custom_screening"
        )
        if payload.model_mode != expected_mode:
            raise HTTPException(
                422,
                f"WWTP model mode differs from the reviewed assessment profile; expected {expected_mode}",
            )
        fraction_fields = {
            "biodegradation_fraction": profile.wwtp_biodegradation_fraction,
            "primary_sludge_fraction": profile.wwtp_primary_sludge_fraction,
            "secondary_sludge_fraction": profile.wwtp_secondary_sludge_fraction,
            "volatilisation_fraction": profile.wwtp_volatilisation_fraction,
        }
        mismatches = [
            name
            for name, expected in fraction_fields.items()
            if expected is None
            or abs(float(getattr(payload, name)) - float(expected))
            > max(1e-12, abs(float(expected)) * 1e-10)
        ]
        if mismatches:
            raise HTTPException(
                422,
                "WWTP inputs differ from the reviewed assessment profile: " + ", ".join(mismatches),
            )

    emission_output = json.loads(emission_run.output_json)
    species = next(
        (x for x in emission_output["species"] if x["species_key"] == payload.species_key),
        None,
    )
    if species is None:
        raise HTTPException(422, f"Species key not found in emission run: {payload.species_key}")

    service_payload = payload.model_dump()
    service_payload.update({
        "influent_mass_kg_day": species["mass_kg_day"],
        "wastewater_flow_m3_day": emission_output["wastewater_flow_m3_day"],
        "emitting_days_per_year": emission_output["administered"]["mass_kg_year"] / (
            emission_output["administered"]["mass_g_day"] / 1000.0
        ) if emission_output["administered"]["mass_g_day"] > 0 else 365,
        "species_name": species["name"],
        "chemical_name": chemical.preferred_name,
        "chemical_cas_number": chemical.cas_number,
        "chemical_inchikey": chemical.inchikey,
    })
    # Use the exact days saved in the emission input rather than deriving where possible.
    emission_input = json.loads(emission_run.input_json)
    service_payload["emitting_days_per_year"] = emission_input["emitting_days_per_year"]

    try:
        output = run_activity_simpletreat(service_payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    latest_locked = db.scalar(
        select(SelectionSet)
        .where(
            SelectionSet.project_id == payload.project_id,
            SelectionSet.chemical_id == payload.chemical_id,
            SelectionSet.status == "locked",
        )
        .order_by(SelectionSet.id.desc())
        .limit(1)
    )

    assumptions = output.pop("assumptions")
    limitations = output.get("limitations", [])
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_ACTIVITY_SIMPLETREAT",
        model_version="1.0.0",
        scenario_name=payload.scenario_name,
        input_json=json.dumps({
            **payload.model_dump(),
            "emission_model_run_id": emission_run.id,
            "species_snapshot": species,
            "wastewater_flow_m3_day": emission_output["wastewater_flow_m3_day"],
        }, sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(assumptions + limitations),
        evidence_hash=(
            _profile_hash(profile)
            if profile is not None
            else latest_locked.evidence_hash if latest_locked else None
        ),
    )
    db.add(row)
    db.flush()

    aq_rq = output.get("aquatic_rq")
    soil_rq = output.get("soil_rq")
    conclusion_parts = []
    if aq_rq is None:
        conclusion_parts.append("Aquatic risk could not be characterised because no aquatic PNEC was supplied.")
    else:
        conclusion_parts.append(
            f"Aquatic RQ = {aq_rq:.3g} ({output['aquatic_risk_band']} concern)."
        )
    if soil_rq is None:
        conclusion_parts.append("Soil risk could not be characterised because no soil PNEC was supplied.")
    else:
        conclusion_parts.append(
            f"Soil RQ = {soil_rq:.3g} ({output['soil_risk_band']} concern)."
        )
    conclusion_parts.append(
        "The emission mass was calculated before treatment and linked to this model run."
    )
    conclusion_parts.append("This is a screening result, not a regulatory conclusion.")

    risk = RiskAssessment(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_run_id=row.id,
        aquatic_pnec_ug_l=payload.aquatic_pnec_ug_l,
        soil_pnec_ug_kg=payload.soil_pnec_ug_kg,
        aquatic_rq=aq_rq,
        soil_rq=soil_rq,
        conclusion=" ".join(conclusion_parts),
    )
    db.add(risk)
    audit(
        db, payload.project_id, "model_run", row.id, "activity_simpletreat_completed",
        {
            "model_key": row.model_key,
            "model_mode": output["model_mode"],
            "emission_model_run_id": emission_run.id,
            "species_key": species["species_key"],
            "influent_mass_kg_day": species["mass_kg_day"],
            "mass_balance_closure": output["mass_balance_closure_fraction"],
            "evidence_hash": row.evidence_hash,
            "assessment_profile_id": profile.id if profile is not None else None,
        },
    )
    db.commit()
    return {
        "model_run_id": row.id,
        "risk_assessment_id": risk.id,
        "emission_model_run_id": emission_run.id,
        "outputs": output,
        "assumptions": assumptions,
        "limitations": limitations,
        "evidence_hash": row.evidence_hash,
        "conclusion": risk.conclusion,
    }



@app.get("/api/projects/{project_id}/activity-simpletreat-runs")
def list_activity_simpletreat_runs(project_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(ModelRun)
        .where(
            ModelRun.project_id == project_id,
            ModelRun.model_key == "ENVIROCHEM_ACTIVITY_SIMPLETREAT",
        )
        .order_by(ModelRun.id.desc())
    ).all())
    return [{
        "model_run_id": row.id,
        "chemical_id": row.chemical_id,
        "scenario_name": row.scenario_name,
        "outputs": json.loads(row.output_json),
        "created_at": row.created_at.isoformat(),
    } for row in rows]


@app.post("/api/model-runs/wastewater-irrigation-comparison")
def create_wastewater_irrigation_comparison(
    payload: WastewaterIrrigationComparisonCreate,
    db: Session = Depends(get_db),
):
    project = db.get(Project, payload.project_id)
    chemical = db.get(Chemical, payload.chemical_id)
    if project is None or chemical is None:
        raise HTTPException(404, "Project or chemical not found")
    if db.get(ProjectChemical, {"project_id": payload.project_id, "chemical_id": payload.chemical_id}) is None:
        raise HTTPException(422, "Chemical is not attached to the selected project")
    profile = _validated_run_profile(
        db, payload.assessment_profile_id, payload.project_id, payload.chemical_id,
    )
    if profile is not None:
        normalise = lambda value: "".join(character for character in str(value or "").casefold() if character.isalnum())
        mismatches = []
        if normalise(payload.chemical_name) != normalise(chemical.preferred_name):
            mismatches.append("chemical_name")
        if chemical.cas_number and payload.cas_number != chemical.cas_number:
            mismatches.append("cas_number")
        numeric_pairs = {
            "soil_dt50_days": (payload.soil_dt50_days, profile.soil_dt50_days),
            "water_solubility_mg_l": (payload.water_solubility_mg_l, profile.water_solubility_mg_l),
            "vapour_pressure_pa": (payload.vapour_pressure_pa, profile.vapour_pressure_pa),
        }
        for name, (actual, expected) in numeric_pairs.items():
            if actual is None and expected is None:
                continue
            if actual is None or expected is None or abs(actual - expected) > max(1e-12, abs(expected) * 1e-10):
                mismatches.append(name)
        if mismatches:
            raise HTTPException(
                422,
                "Irrigation inputs differ from the reviewed assessment profile or identity: " + ", ".join(mismatches),
            )
    if payload.sorption_model_run_id is not None:
        sorption_run = db.get(ModelRun, payload.sorption_model_run_id)
        if sorption_run is None or sorption_run.model_key != "ENVIROCHEM_SORPTION":
            raise HTTPException(404, "Sorption model run not found")
        if sorption_run.project_id != payload.project_id or sorption_run.chemical_id != payload.chemical_id:
            raise HTTPException(422, "Sorption run does not belong to the selected project and chemical")
        expected_kd = json.loads(sorption_run.output_json).get("selected", {}).get("kd_l_kg")
        if expected_kd is None or abs(payload.kd_l_kg - expected_kd) > max(1e-12, abs(expected_kd) * 1e-10):
            raise HTTPException(422, "Irrigation Kd differs from the linked sorption run")

    service_payload = payload.model_dump()
    linked_run = None
    if payload.activity_simpletreat_model_run_id is not None:
        linked_run = db.get(ModelRun, payload.activity_simpletreat_model_run_id)
        if linked_run is None or linked_run.model_key != "ENVIROCHEM_ACTIVITY_SIMPLETREAT":
            raise HTTPException(404, "Activity SimpleTreat model run not found")
        if linked_run.project_id != payload.project_id or linked_run.chemical_id != payload.chemical_id:
            raise HTTPException(422, "Activity SimpleTreat run does not belong to the selected project and chemical")
        linked_output = json.loads(linked_run.output_json)
        effluent = linked_output.get("effluent_concentration_ug_l")
        if effluent is None:
            raise HTTPException(422, "Linked Activity SimpleTreat run has no effluent concentration")
        service_payload["effluent_concentration_ug_l"] = effluent

    try:
        output = run_wastewater_irrigation_comparison(service_payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    assumptions = output.get("warnings", []) + output.get("source_workbook_checks", [])
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_key="ENVIROCHEM_DUAL_WASTEWATER_IRRIGATION",
        model_version=output["model_version"],
        scenario_name=payload.scenario_name,
        input_json=json.dumps({
            **payload.model_dump(),
            "resolved_effluent_concentration_ug_l": service_payload["effluent_concentration_ug_l"],
            "linked_activity_simpletreat_model_run_id": linked_run.id if linked_run else None,
        }, sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(assumptions, sort_keys=True),
        evidence_hash=(
            _profile_hash(profile)
            if profile is not None
            else linked_run.evidence_hash if linked_run else None
        ),
    )
    db.add(row)
    db.flush()

    workflow_ids: dict[str, list[int]] = {"EU": [], "US": []}
    jurisdiction_by_model = {
        "PEARL": "EU", "PELMO": "EU", "MACRO": "EU", "TOXSWA": "EU",
        "PWC": "US", "PRZM": "US", "EXAMS": "US",
    }
    for model_key, input_data in output["adapter_payloads"].items():
        model = next((x for x in MODELS if x["key"] == model_key), None)
        if model is None:
            continue
        jurisdiction = jurisdiction_by_model[model_key]
        workflow_payload = {
            "project_id": payload.project_id,
            "chemical_id": payload.chemical_id,
            "model_key": model_key,
            "jurisdiction": jurisdiction,
            "tier": 2,
            "scenario_name": f"{payload.scenario_name} — {jurisdiction} {model_key}",
            "input_data": input_data,
            "executable_path": None,
        }
        manifest = prepare_workflow_manifest(workflow_payload, model)
        workflow = ModelWorkflow(
            project_id=payload.project_id,
            chemical_id=payload.chemical_id,
            model_key=model_key,
            jurisdiction=jurisdiction,
            tier=2,
            scenario_name=workflow_payload["scenario_name"],
            implementation=model["implementation"],
            status="prepared" if not manifest["missing_inputs"] else "inputs_required",
            executable_path=None,
            input_manifest_json=json.dumps(manifest, sort_keys=True),
            expected_outputs_json=json.dumps(manifest["expected_outputs"], sort_keys=True),
            input_hash=manifest["input_hash"],
        )
        db.add(workflow)
        db.flush()
        workflow_ids[jurisdiction].append(workflow.id)
        audit(db, payload.project_id, "model_workflow", workflow.id, "prepared_from_dual_irrigation", {
            "parent_model_run_id": row.id,
            "model_key": model_key,
            "jurisdiction": jurisdiction,
            "status": workflow.status,
            "missing_inputs": manifest["missing_inputs"],
            "input_hash": workflow.input_hash,
        })

    audit(db, payload.project_id, "model_run", row.id, "dual_irrigation_completed", {
        "model_key": row.model_key,
        "linked_activity_simpletreat_model_run_id": linked_run.id if linked_run else None,
        "effluent_concentration_ug_l": output["native_screen"]["effluent_concentration_ug_l"],
        "soil_concentration_ug_kg": output["native_screen"]["soil_concentration_at_duration_ug_kg"],
        "workflow_ids": workflow_ids,
        "evidence_hash": row.evidence_hash,
    })
    db.commit()
    db.refresh(row)
    return {
        "model_run_id": row.id,
        "linked_activity_simpletreat_model_run_id": linked_run.id if linked_run else None,
        "workflow_ids": workflow_ids,
        "outputs": output,
        "evidence_hash": row.evidence_hash,
    }


@app.post("/api/model-runs/wwtp")
def create_wwtp_run(payload: WWTPRunCreate, db: Session = Depends(get_db)):
    latest_locked = db.scalar(
        select(SelectionSet)
        .where(
            SelectionSet.project_id == payload.project_id,
            SelectionSet.chemical_id == payload.chemical_id,
            SelectionSet.status == "locked",
        )
        .order_by(SelectionSet.id.desc())
        .limit(1)
    )
    try:
        output = run_wwtp(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    assumptions = output.pop("assumptions")
    row = ModelRun(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        scenario_name=payload.scenario_name,
        input_json=json.dumps(payload.model_dump(), sort_keys=True),
        output_json=json.dumps(output, sort_keys=True),
        assumptions_json=json.dumps(assumptions),
        evidence_hash=latest_locked.evidence_hash if latest_locked else None,
    )
    db.add(row)
    db.flush()

    aq_rq = output.get("aquatic_rq")
    soil_rq = output.get("soil_rq")
    conclusion_parts = []
    if aq_rq is None:
        conclusion_parts.append("Aquatic risk could not be characterised because no aquatic PNEC was supplied.")
    else:
        conclusion_parts.append(
            f"Aquatic RQ = {aq_rq:.3g} ({output['aquatic_risk_band']} concern)."
        )
    if soil_rq is None:
        conclusion_parts.append("Soil risk could not be characterised because no soil PNEC was supplied.")
    else:
        conclusion_parts.append(
            f"Soil RQ = {soil_rq:.3g} ({output['soil_risk_band']} concern)."
        )
    conclusion_parts.append("This is a screening result, not a regulatory conclusion.")
    risk = RiskAssessment(
        project_id=payload.project_id,
        chemical_id=payload.chemical_id,
        model_run_id=row.id,
        aquatic_pnec_ug_l=payload.aquatic_pnec_ug_l,
        soil_pnec_ug_kg=payload.soil_pnec_ug_kg,
        aquatic_rq=aq_rq,
        soil_rq=soil_rq,
        conclusion=" ".join(conclusion_parts),
    )
    db.add(risk)
    audit(
        db, payload.project_id, "model_run", row.id, "completed",
        {"model_key": row.model_key, "evidence_hash": row.evidence_hash}
    )
    db.commit()
    return {
        "model_run_id": row.id,
        "risk_assessment_id": risk.id,
        "outputs": output,
        "assumptions": assumptions,
        "evidence_hash": row.evidence_hash,
        "conclusion": risk.conclusion,
    }

@app.get("/api/projects/{project_id}/audit")
def list_audit(project_id: int, db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(AuditEvent)
        .where(AuditEvent.project_id == project_id)
        .order_by(AuditEvent.created_at.desc())
    ).all())
    return [{
        "id": x.id,
        "entity_type": x.entity_type,
        "entity_id": x.entity_id,
        "action": x.action,
        "payload": json.loads(x.payload_json),
        "created_at": x.created_at.isoformat(),
    } for x in rows]
