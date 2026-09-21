from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import (
    String, Float, Integer, ForeignKey, Text, Boolean, DateTime, UniqueConstraint,
    event, select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship
from .database import Base
from .exceptions import ChemicalIdentityError

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    jurisdiction: Mapped[str] = mapped_column(String(100), default="UK/EU screening")
    purpose: Mapped[str] = mapped_column(Text, default="Environmental risk screening")
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    chemicals: Mapped[list["ProjectChemical"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

class Chemical(Base):
    __tablename__ = "chemicals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preferred_name: Mapped[str] = mapped_column(String(200), index=True)
    cas_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    molecular_formula: Mapped[str | None] = mapped_column(String(100))
    molecular_weight_g_mol: Mapped[float | None] = mapped_column(Float)
    smiles: Mapped[str | None] = mapped_column(Text)
    inchikey: Mapped[str | None] = mapped_column(String(100))
    substance_form: Mapped[str] = mapped_column(String(100), default="parent")
    review_status: Mapped[str] = mapped_column(String(50), default="identity_seed")
    projects: Mapped[list["ProjectChemical"]] = relationship(back_populates="chemical")
    evidence: Mapped[list["EvidenceRecord"]] = relationship(
        back_populates="chemical", cascade="all, delete-orphan"
    )

class ProjectChemical(Base):
    __tablename__ = "project_chemicals"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(100), default="assessment_substance")
    project: Mapped[Project] = relationship(back_populates="chemicals")
    chemical: Mapped[Chemical] = relationship(back_populates="projects")


class ChemicalIdentitySnapshot(Base):
    """Immutable provenance for a user-confirmed substance identity."""

    __tablename__ = "chemical_identity_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), unique=True, index=True)
    source_key: Mapped[str] = mapped_column(String(100))
    source_record_id: Mapped[str | None] = mapped_column(String(250))
    source_url: Mapped[str | None] = mapped_column(Text)
    query_text: Mapped[str | None] = mapped_column(String(500))
    query_mode: Mapped[str | None] = mapped_column(String(50))
    identity_hash: Mapped[str] = mapped_column(String(64), unique=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChemicalAssessmentProfile(Base):
    """Reviewed values selected for one chemical within one assessment project.

    Evidence discovery remains separate.  This profile is the explicit bridge between
    candidate data and guided calculations, so one chemical can never inherit another
    chemical's values merely because it is the active UI record.
    """

    __tablename__ = "chemical_assessment_profiles"
    __table_args__ = (
        UniqueConstraint("project_id", "chemical_id", name="uq_profile_project_chemical"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    profile_origin: Mapped[str] = mapped_column(String(80), default="draft")
    review_status: Mapped[str] = mapped_column(String(50), default="draft")
    ionisation_class: Mapped[str | None] = mapped_column(String(30))
    log_kow: Mapped[float | None] = mapped_column(Float)
    pkaa: Mapped[float | None] = mapped_column(Float)
    pkab: Mapped[float | None] = mapped_column(Float)
    water_solubility_mg_l: Mapped[float | None] = mapped_column(Float)
    vapour_pressure_pa: Mapped[float | None] = mapped_column(Float)
    soil_dt50_days: Mapped[float | None] = mapped_column(Float)
    wwtp_biodegradation_fraction: Mapped[float | None] = mapped_column(Float)
    wwtp_primary_sludge_fraction: Mapped[float | None] = mapped_column(Float)
    wwtp_secondary_sludge_fraction: Mapped[float | None] = mapped_column(Float)
    wwtp_volatilisation_fraction: Mapped[float | None] = mapped_column(Float)
    source_summary: Mapped[str | None] = mapped_column(Text)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    reviewer_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(100), default="journal_article")
    title: Mapped[str] = mapped_column(String(500))
    organisation: Mapped[str | None] = mapped_column(String(200))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    identifier: Mapped[str | None] = mapped_column(String(250))
    url: Mapped[str | None] = mapped_column(Text)
    access_date: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    property_code: Mapped[str] = mapped_column(String(100), index=True)
    evidence_type: Mapped[str] = mapped_column(String(50), default="measured")
    original_value: Mapped[float] = mapped_column(Float)
    original_unit: Mapped[str] = mapped_column(String(50), default="days")
    soil_type: Mapped[str | None] = mapped_column(String(100))
    soil_texture: Mapped[str | None] = mapped_column(String(100))
    soil_ph: Mapped[float | None] = mapped_column(Float)
    organic_carbon_percent: Mapped[float | None] = mapped_column(Float)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    moisture_percent_whc: Mapped[float | None] = mapped_column(Float)
    kinetic_model: Mapped[str | None] = mapped_column(String(50))
    endpoint_kind: Mapped[str | None] = mapped_column(String(100))
    test_guideline: Mapped[str | None] = mapped_column(String(100))
    reliability_score: Mapped[int | None] = mapped_column(Integer)
    representative_group_key: Mapped[str] = mapped_column(String(200))
    include_by_default: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    chemical: Mapped[Chemical] = relationship(back_populates="evidence")
    source: Mapped[Source] = relationship()

class SelectionSet(Base):
    __tablename__ = "selection_sets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    property_code: Mapped[str] = mapped_column(String(100), default="FATE.SOIL_DT50")
    ruleset_version: Mapped[str] = mapped_column(String(50), default="EU_SOIL_DT50_PILOT_0.1")
    target_temperature_c: Mapped[float] = mapped_column(Float, default=20.0)
    activation_energy_kj_mol: Mapped[float] = mapped_column(Float, default=65.4)
    max_reliability_score: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    selected_value_days: Mapped[float | None] = mapped_column(Float)
    evidence_hash: Mapped[str | None] = mapped_column(String(64))
    rationale: Mapped[str | None] = mapped_column(Text)
    statistics_json: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    members: Mapped[list["SelectionMember"]] = relationship(
        back_populates="selection_set", cascade="all, delete-orphan"
    )

class SelectionMember(Base):
    __tablename__ = "selection_members"
    selection_set_id: Mapped[int] = mapped_column(
        ForeignKey("selection_sets.id"), primary_key=True
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id"), primary_key=True
    )
    decision: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    normalised_value_days: Mapped[float | None] = mapped_column(Float)
    representative_value_days: Mapped[float | None] = mapped_column(Float)
    transformations_json: Mapped[str | None] = mapped_column(Text)
    selection_set: Mapped[SelectionSet] = relationship(back_populates="members")
    evidence: Mapped[EvidenceRecord] = relationship()

class ModelRun(Base):
    __tablename__ = "model_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    model_key: Mapped[str] = mapped_column(String(100), default="ENVIROCHEM_WWTP")
    model_version: Mapped[str] = mapped_column(String(50), default="0.1.0")
    scenario_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="completed")
    input_json: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str] = mapped_column(Text)
    assumptions_json: Mapped[str] = mapped_column(Text)
    evidence_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    identity_binding: Mapped["ModelRunIdentityBinding"] = relationship(
        back_populates="model_run", uselist=False, cascade="all, delete-orphan"
    )


class ModelRunIdentityBinding(Base):
    """Immutable chemical identity copied into a model run at persistence time.

    Keeping this as a separate one-to-one record avoids altering historical
    ``model_runs`` tables in existing local SQLite installations. New and
    backfilled runs retain the exact confirmed identity hash and JSON snapshot
    even if a display name is corrected later.
    """

    __tablename__ = "model_run_identity_bindings"
    __table_args__ = (
        UniqueConstraint("model_run_id", name="uq_model_run_identity_binding"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    identity_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("chemical_identity_snapshots.id"), index=True
    )
    identity_hash: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    model_run: Mapped[ModelRun] = relationship(back_populates="identity_binding")
    identity_snapshot: Mapped[ChemicalIdentitySnapshot] = relationship()


@event.listens_for(Session, "before_flush")
def bind_new_model_runs_to_identity(session: Session, _flush_context, _instances) -> None:
    """Fail closed unless every newly persisted model run has an identity snapshot."""

    pending_snapshots = {
        row.chemical_id: row
        for row in session.new
        if isinstance(row, ChemicalIdentitySnapshot)
    }
    for row in tuple(session.new):
        if not isinstance(row, ModelRun) or row.identity_binding is not None:
            continue
        snapshot = pending_snapshots.get(row.chemical_id)
        if snapshot is None:
            snapshot = session.scalar(
                select(ChemicalIdentitySnapshot).where(
                    ChemicalIdentitySnapshot.chemical_id == row.chemical_id
                )
            )
        if snapshot is None:
            raise ChemicalIdentityError(
                "A confirmed immutable chemical identity snapshot is required before a model run can be saved",
                details={"chemical_id": row.chemical_id, "project_id": row.project_id},
            )
        row.identity_binding = ModelRunIdentityBinding(
            project_id=row.project_id,
            chemical_id=row.chemical_id,
            identity_snapshot=snapshot,
            identity_hash=snapshot.identity_hash,
            snapshot_json=snapshot.snapshot_json,
        )

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id"))
    aquatic_pnec_ug_l: Mapped[float | None] = mapped_column(Float)
    soil_pnec_ug_kg: Mapped[float | None] = mapped_column(Float)
    aquatic_rq: Mapped[float | None] = mapped_column(Float)
    soil_rq: Mapped[float | None] = mapped_column(Float)
    conclusion: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ModelWorkflow(Base):
    __tablename__ = "model_workflows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    model_key: Mapped[str] = mapped_column(String(100), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True)
    tier: Mapped[int] = mapped_column(Integer)
    scenario_name: Mapped[str] = mapped_column(String(250))
    implementation: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="prepared")
    executable_path: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(100))
    executable_version: Mapped[str | None] = mapped_column(String(100))
    input_manifest_json: Mapped[str] = mapped_column(Text)
    expected_outputs_json: Mapped[str] = mapped_column(Text)
    output_record_json: Mapped[str | None] = mapped_column(Text)
    input_hash: Mapped[str] = mapped_column(String(64))
    output_hash: Mapped[str | None] = mapped_column(String(64))
    review_decision: Mapped[str | None] = mapped_column(String(50))
    reviewer: Mapped[str | None] = mapped_column(String(200))
    review_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OrchestratedAssessmentRecord(Base):
    """Immutable snapshot of one cross-model assessment decision state.

    Refinement and finalisation create a successor row rather than rewriting a
    scientific record.  The exact canonical JSON is content-addressed and bound
    to the confirmed chemical identity used when it was created.
    """

    __tablename__ = "orchestrated_assessment_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int] = mapped_column(ForeignKey("chemicals.id"), index=True)
    identity_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("chemical_identity_snapshots.id"), index=True
    )
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("orchestrated_assessment_records.id"), index=True
    )
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True)
    contaminant_group: Mapped[str] = mapped_column(String(100), index=True)
    scenario: Mapped[str] = mapped_column(String(100), index=True)
    current_tier: Mapped[int] = mapped_column(Integer)
    maximum_tier: Mapped[int] = mapped_column(Integer)
    assessment_mode: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="assessment_snapshot")
    record_json: Mapped[str] = mapped_column(Text)
    record_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    reviewer: Mapped[str | None] = mapped_column(String(200))
    review_decision: Mapped[str | None] = mapped_column(String(50))
    review_rationale: Mapped[str | None] = mapped_column(Text)
    stated_purpose: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


@event.listens_for(Session, "before_flush")
def prevent_orchestrated_assessment_mutation(
    session: Session, _flush_context, _instances
) -> None:
    """Scientific assessment snapshots are append-only at the ORM boundary."""

    for row in tuple(session.dirty):
        if isinstance(row, OrchestratedAssessmentRecord) and session.is_modified(
            row, include_collections=False
        ):
            raise ValueError(
                "Orchestrated assessment records are immutable; create a successor record"
            )


class MSRawEvidenceFile(Base):
    """One imported mzML file: content-hashed, parsed once at import time.

    project_id/chemical_id are nullable -- a raw file may be uploaded before
    the parent/metabolite relationship is known or confirmed. There is no
    update route for this table: a re-import creates a new row rather than
    editing a prior one, so the sha256 stays a stable pointer to exactly the
    bytes that were reviewed. Reviewer input (confidence_level,
    reviewer_note) lives on MSFeature below and is the one thing a reviewer
    can change -- everything derived from the file itself cannot be.
    """

    __tablename__ = "ms_raw_evidence_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    chemical_id: Mapped[int | None] = mapped_column(ForeignKey("chemicals.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    format: Mapped[str] = mapped_column(String(20), default="mzml")
    ionisation_mode: Mapped[str | None] = mapped_column(String(20))
    ms1_scan_count: Mapped[int] = mapped_column(Integer, default=0)
    ms2_scan_count: Mapped[int] = mapped_column(Integer, default=0)
    tic_json: Mapped[str] = mapped_column(Text, default="[]")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    features: Mapped[list["MSFeature"]] = relationship(
        back_populates="raw_file", cascade="all, delete-orphan"
    )


class MSFeature(Base):
    """One MS2-triggered precursor event: retention time, precursor, product
    ions and its own extracted-ion chromatogram (XIC).

    This is a direct-from-instrument candidate list -- every DDA
    fragmentation event the file already recorded -- not an aligned,
    deduplicated feature-detection result; see ms_evidence.py's module
    docstring for the deliberate scope boundary. confidence_level defaults
    to "feature_of_interest" (Schymanski's own starting point: an accurate
    mass with no structural claim yet) and a reviewer may move it forward by
    hand via the review endpoint. This module never assigns a formula or
    structure and never sets a level beyond what a human reviewer records --
    there is no automatic promotion path.
    """

    __tablename__ = "ms_features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_file_id: Mapped[int] = mapped_column(ForeignKey("ms_raw_evidence_files.id"), index=True)
    feature_index: Mapped[int] = mapped_column(Integer)
    retention_time_min: Mapped[float] = mapped_column(Float)
    precursor_mz: Mapped[float] = mapped_column(Float)
    precursor_charge: Mapped[int | None] = mapped_column(Integer)
    collision_energy: Mapped[float | None] = mapped_column(Float)
    scan_id: Mapped[str | None] = mapped_column(String(100))
    base_peak_mz: Mapped[float | None] = mapped_column(Float)
    product_ion_count: Mapped[int] = mapped_column(Integer, default=0)
    product_ions_json: Mapped[str] = mapped_column(Text, default="[]")
    xic_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence_level: Mapped[str] = mapped_column(String(40), default="feature_of_interest")
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    raw_file: Mapped[MSRawEvidenceFile] = relationship(back_populates="features")


class SiteModelRecord(Base):
    """A validated contaminated-land conceptual site model saved against a project.

    Only models that pass conceptual_site_model.model_from_dict() are ever stored, so a saved model is
    always structurally valid. Measured-data flags are derived at assessment time from the project's
    MetalMeasurementRecord rows in addition to any flags stored in the model JSON itself.
    """

    __tablename__ = "site_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    jurisdiction: Mapped[str] = mapped_column(String(20))
    model_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MetalMeasurementRecord(Base):
    """One metal/metalloid concentration on its original basis, with provenance (see services/metals.py)."""

    __tablename__ = "metal_measurements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    element: Mapped[str] = mapped_column(String(4))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    basis: Mapped[str] = mapped_column(String(20))
    medium: Mapped[str] = mapped_column(String(20))
    weight_basis: Mapped[str | None] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(20), default="measured")
    oxidation_state: Mapped[str | None] = mapped_column(String(40))
    species: Mapped[str | None] = mapped_column(String(100))
    method: Mapped[str | None] = mapped_column(Text)
    measured_date: Mapped[str | None] = mapped_column(String(40))
    jurisdiction: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[str | None] = mapped_column(String(100))
    applicability: Mapped[str | None] = mapped_column(Text)
    assumptions_json: Mapped[str] = mapped_column(Text, default="[]")
    # Which site-model medium this sample represents (soil, groundwater, surface_water, ...). "water" alone is
    # ambiguous, so a measurement only feeds a site model's measured-data flags when this is set.
    site_medium: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
