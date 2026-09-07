import json

from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import (
    Chemical,
    ChemicalIdentitySnapshot,
    ModelRun,
    ModelRunIdentityBinding,
)
from .services.identity import core_identity_hash, identity_hash


def _local_snapshot_candidate(chemical: Chemical) -> dict:
    candidate = {
        "source_key": "local_verified_record",
        "source_record_id": f"chemical:{chemical.id}",
        "source_url": None,
        "query_text": chemical.cas_number or chemical.preferred_name,
        "query_mode": "cas" if chemical.cas_number else "iupac",
        "preferred_name": chemical.preferred_name,
        "cas_number": chemical.cas_number,
        "cas_candidates": [chemical.cas_number] if chemical.cas_number else [],
        "molecular_formula": chemical.molecular_formula,
        "molecular_weight_g_mol": chemical.molecular_weight_g_mol,
        "smiles": chemical.smiles,
        "inchikey": chemical.inchikey,
        "substance_form": chemical.substance_form,
        "warnings": [
            "Baseline snapshot generated from the previously reviewed local identity record."
        ],
    }
    candidate["identity_hash"] = identity_hash(candidate)
    candidate["core_identity_hash"] = core_identity_hash(candidate)
    return candidate

def seed(db: Session) -> None:
    existing = db.scalar(select(Chemical.id).limit(1))
    if existing is None:
        db.add(Chemical(
            preferred_name="Carbamazepine",
            cas_number="298-46-4",
            molecular_formula="C15H12N2O",
            molecular_weight_g_mol=236.27,
            smiles="NC(=O)N1c2ccccc2C=Cc2ccccc21",
            inchikey="FFGPTBGBLSHEPO-UHFFFAOYSA-N",
            substance_form="parent",
            review_status="identity_seed",
        ))
        db.flush()

    # Existing local installs predate immutable identity bindings. Create one
    # explicit baseline snapshot per complete stored identity; do not infer or
    # fill missing chemical properties.
    snapshots_by_chemical = {
        row.chemical_id: row
        for row in db.scalars(select(ChemicalIdentitySnapshot)).all()
    }
    for chemical in db.scalars(select(Chemical).order_by(Chemical.id)).all():
        if chemical.id in snapshots_by_chemical:
            continue
        if not all(
            (
                chemical.preferred_name,
                chemical.molecular_formula,
                chemical.molecular_weight_g_mol,
                chemical.smiles,
                chemical.inchikey,
            )
        ):
            continue
        candidate = _local_snapshot_candidate(chemical)
        snapshot = ChemicalIdentitySnapshot(
            chemical_id=chemical.id,
            source_key=candidate["source_key"],
            source_record_id=candidate["source_record_id"],
            source_url=None,
            query_text=candidate["query_text"],
            query_mode=candidate["query_mode"],
            identity_hash=candidate["identity_hash"],
            snapshot_json=json.dumps(candidate, sort_keys=True),
        )
        db.add(snapshot)
        db.flush()
        snapshots_by_chemical[chemical.id] = snapshot

    # Backfill historical runs where an immutable identity is available. The
    # copied JSON/hash preserves the identity actually bound at migration time.
    bound_run_ids = set(db.scalars(select(ModelRunIdentityBinding.model_run_id)).all())
    for run in db.scalars(select(ModelRun).order_by(ModelRun.id)).all():
        if run.id in bound_run_ids:
            continue
        snapshot = snapshots_by_chemical.get(run.chemical_id)
        if snapshot is None:
            continue
        db.add(ModelRunIdentityBinding(
            model_run_id=run.id,
            project_id=run.project_id,
            chemical_id=run.chemical_id,
            identity_snapshot_id=snapshot.id,
            identity_hash=snapshot.identity_hash,
            snapshot_json=snapshot.snapshot_json,
        ))
    db.commit()
