"""Cleanup data/envirochem.sqlite: remove accumulated test-fixture rows, keep real work.

Keep set (chosen after a fresh read-only survey 2026-10-01, superseding the stale 2026-09-21 keep set
which predated this session's real validation work):
  projects:  1, 197, 2324, 2326, 2327, 2329
  chemicals: 1 (Carbamazepine), 2 (Diclofenac), 1394 (Ibuprofen)

Project 2328 (an abandoned duplicate Ibuprofen validation attempt, 0 model runs, superseded same-day by
2329) is deliberately NOT kept -- real debris from this session, not useful data.

Runs as ONE transaction. Always does the dry run (rolled back) first and prints counts. Only commits for
real when called with --apply, and even then verifies PRAGMA foreign_key_check == 0 before committing.
Does not touch files on disk under data/model_workflows/ or data/external_runs/ (same scope limit as the
2026-09-21 survey).
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(r"C:\Users\jnigh\Downloads\EnviroChem_Studio_v2_23_0_ALPHA3_1\data\envirochem.sqlite")
KEEP_PROJECT_IDS = (1, 197, 2324, 2326, 2327, 2329)
KEEP_CHEMICAL_IDS = (1, 2, 1394)

APPLY = "--apply" in sys.argv


def qmarks(seq):
    return ",".join("?" * len(seq))


def main():
    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA foreign_keys = OFF")  # we enforce ordering ourselves, then verify at the end
    cur = con.cursor()

    counts = {}

    def run(label, sql, params=()):
        cur.execute(sql, params)
        counts[label] = cur.rowcount

    keep_p = KEEP_PROJECT_IDS
    keep_c = KEEP_CHEMICAL_IDS

    # 1. selection_members: depends on selection_sets / evidence_records, delete first.
    run("selection_members (by selection_sets)", f"""
        DELETE FROM selection_members WHERE selection_set_id IN (
            SELECT id FROM selection_sets WHERE project_id NOT IN ({qmarks(keep_p)}) OR chemical_id NOT IN ({qmarks(keep_c)})
        )
    """, (*keep_p, *keep_c))
    run("selection_sets", f"DELETE FROM selection_sets WHERE project_id NOT IN ({qmarks(keep_p)}) OR chemical_id NOT IN ({qmarks(keep_c)})", (*keep_p, *keep_c))

    run("model_run_identity_bindings", f"DELETE FROM model_run_identity_bindings WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("risk_assessments", f"DELETE FROM risk_assessments WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("orchestrated_assessment_records", f"DELETE FROM orchestrated_assessment_records WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("model_workflows", f"DELETE FROM model_workflows WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)

    run("ms_features (by raw file)", f"""
        DELETE FROM ms_features WHERE raw_file_id IN (
            SELECT id FROM ms_raw_evidence_files WHERE project_id NOT IN ({qmarks(keep_p)})
        )
    """, keep_p)
    run("ms_raw_evidence_files", f"DELETE FROM ms_raw_evidence_files WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)

    run("model_runs", f"DELETE FROM model_runs WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("chemical_assessment_profiles", f"DELETE FROM chemical_assessment_profiles WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("project_chemicals", f"DELETE FROM project_chemicals WHERE project_id NOT IN ({qmarks(keep_p)}) OR chemical_id NOT IN ({qmarks(keep_c)})", (*keep_p, *keep_c))
    run("metal_measurements", f"DELETE FROM metal_measurements WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("site_models", f"DELETE FROM site_models WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)
    run("audit_events", f"DELETE FROM audit_events WHERE project_id NOT IN ({qmarks(keep_p)})", keep_p)

    # Confirmed by a fresh read-only survey (2026-10-01): every evidence_records row for the KEPT chemicals too
    # (1: 74x identical FATE.SOIL_DT50=42.0d; 2: 406x identical EC50=1.0mg/L + 75x identical DT50=30.0d) is
    # synthetic test-fixture churn from the Sept 7-8 identity-isolation test batch -- zero varied/real values,
    # nothing from this session's real work. So this is an unconditional wipe, not chemical-scoped.
    run("evidence_records (all -- confirmed 100% test fixtures, see comment above)", "DELETE FROM evidence_records")
    run("sources (all -- same reason)", "DELETE FROM sources")
    run("chemical_identity_snapshots", f"DELETE FROM chemical_identity_snapshots WHERE chemical_id NOT IN ({qmarks(keep_c)})", keep_c)
    run("chemicals", f"DELETE FROM chemicals WHERE id NOT IN ({qmarks(keep_c)})", keep_c)
    run("projects", f"DELETE FROM projects WHERE id NOT IN ({qmarks(keep_p)})", keep_p)

    fk_problems = cur.execute("PRAGMA foreign_key_check").fetchall()

    print(f"=== {'APPLY' if APPLY else 'DRY RUN'} ===")
    for label, n in counts.items():
        print(f"  deleted from {label}: {n}")
    print(f"  foreign_key_check problems: {len(fk_problems)}")
    if fk_problems:
        for p in fk_problems[:20]:
            print("   ", p)

    if APPLY and not fk_problems:
        con.commit()
        print("COMMITTED.")
    else:
        con.rollback()
        print("ROLLED BACK." if not APPLY else "ROLLED BACK (fk_problems found, refused to commit).")

    # Post-check (only meaningful after a real commit; harmless to print on a rollback too).
    remaining_projects = cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    remaining_chemicals = cur.execute("SELECT COUNT(*) FROM chemicals").fetchone()[0]
    print(f"  projects now: {remaining_projects}, chemicals now: {remaining_chemicals}")

    con.close()


if __name__ == "__main__":
    main()
