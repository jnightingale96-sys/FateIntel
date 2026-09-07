# EnviroChem Studio canonical baseline audit

Audit date: 2 September 2026  
Canonical input: `EnviroChem_Studio_v2_22_1_TRANSFORMATION_PATHWAYS_STARTUP_HOTFIX (1) (1).zip`  
Input SHA-256: `4b4f903ac23fbba94108579702c5f51243908a1bee9b3d2cac7360ce0fb080f8`

## Evidence boundary

The supplied archive declares `APP_VERSION = 2.22.1-beta` and build ID
`envirochem-studio-v2.22.1-startup-hotfix-2026-08-17`. It contains 168 archive
members, expands to 2,141,010 bytes and contains no Git history. The uploaded
ZIP is therefore the immutable canonical input for this increment; no claim is
made that an unavailable v2.22.2 source tree was inspected.

The archive passed path-traversal, absolute-path, symlink, expanded-size and ZIP
integrity checks before extraction. The uploaded bytes were not modified.

## Baseline validation before edits

- Python test result: **186 passed, 2 failed, 5 skipped**.
- Four skips were the documented optional native-RDKit backend; browser/WASM is
  the primary EnviroDesign route.
- One skip was optional RSA signing because `cryptography` was not installed.
- Both failures were stale UI assertions. They inspected the short wrapper
  `START_ENVIROCHEM.bat` for logic that the v2.22.1 hotfix deliberately moved to
  the visible `START_ENVIROCHEM_CONSOLE.cmd`. No scientific calculation failed.
- Python compilation and JavaScript syntax passed after the implementation.

## Capability classification at the baseline

| Area | Classification | Audited interpretation |
| --- | --- | --- |
| Identity resolution and immutable confirmation | Working, with UI default defect | PubChem/local candidates require confirmation, but guided startup automatically selected Carbamazepine. |
| Chemical-specific assessment profiles and evidence | Working | Project/chemical keys and reviewed-profile gates exist; evidence import checks identity. |
| Pharmaceutical source terms, WWTP, biosolids and irrigation | Working screening calculations | Transparent native calculations with tested scientific boundaries; not official SimpleTreat/EUSES executions. |
| Sorption, plant uptake, multimedia and river-network calculations | Working or research screen | Native screens exist with explicit limitations and model keys. |
| FOCUS PEARL/TOXSWA and other external models | Partial | Native screens, manifests, hand-offs and selected output imports exist; adapter presence is not proof of official end-to-end execution. |
| Transformation pathways | Working provisional provider path | BioTransformer ENVMICRO response is normalised to a provider-neutral graph. Products remain predictions; kinetics and concentration are absent. |
| REACH | Partial review/export support | Evidence-bound review ZIP and optional signing exist; it is not an IUCLID dossier or Chesar replacement. |
| Laboratory and consumer exposure | Qualitative/partial | COSHH and Home Use summaries do not provide complete quantitative exposure assessment. |
| Industrial manufacture/processing | Missing end-to-end workflow | No complete use descriptor, source term, worker exposure, release and risk chain. |
| Waste, landfill and incineration | Missing | No coherent landfill leachate/gas, incineration or recycling calculator chain. |
| US TSCA/FIFRA/FDA model workflows | Mostly missing | Framework labels and selected adapter metadata exist, but not validated executable assessment chains. |

## Licensing decisions carried forward

1. BioTransformer ENVMICRO remains an interim academic/development provider.
   Staging and production fail closed unless an operator with written permission
   explicitly confirms commercial rights.
2. The internal pathway graph stays provider-neutral. No technical workaround is
   treated as a licensing solution.
3. AERU VSDB/PPDB, PREMIER and other permission-gated evidence sources are not
   scraped or redistributed.
4. External regulatory executables and datasets remain locally installed,
   version-controlled hand-offs subject to their own terms.

## Smallest safe v2.23 implementation slice

The first slice implements Steps 1 and 2 of the approved workplan:

- preserve and hash the exact canonical archive;
- correct stale launcher tests without reverting the visible-console hotfix;
- remove automatic Carbamazepine/project/profile selection from normal startup;
- require an exact `project_id` plus `chemical_id` link to restore a workspace;
- refuse ambiguous multi-chemical project selection rather than choosing a first row;
- strengthen CAS/InChIKey/formula/molecular-weight/substance-form conflicts;
- bind each saved model run to copied immutable identity JSON and its SHA-256;
- backfill historical runs only where a complete confirmed identity exists; and
- test 20 successive chemically varied identities, profile isolation, evidence
  isolation, deliberate identifier conflict and model-run identity binding.

## Deferred by design

Typed dimensional quantities, `UseScenario`/`ReleaseEvent`, parent/TP mass and
molar ledgers, the formal model/licence registry, industrial/lab/consumer source
terms, landfill chains and US model runners remain subsequent v2.23 increments.
They were not mixed into the identity repair because that would make the first
regression gate harder to audit and roll back.

## Alpha 2 implementation

The second increment implements the first US exposure foundation without
altering the canonical-input record above. It adds typed release events,
media/waste routing, worker inhalation and dermal screening, a 60-record EPA
scenario catalogue, a 15-domain completeness control, and managed external
contracts for ChemSTEER, CEM and E-FAST.

The scientific and rights boundary is fail-visible: the native calculation is
not EPA-equivalent; only 12 published ESDs are enabled by default; draft records
remain reference-only; E-FAST remains legacy; and no EPA executable is bundled,
modified or redistributed. Landfill is currently a mass destination rather than
a leachate/gas fate model, while consumer exposure remains a CEM adapter
contract rather than a native quantitative model.

## Alpha 1.1 startup correction

The first Alpha 1 Windows package exposed a file-handle collision at launch:
the background browser-readiness helper and foreground Uvicorn process both
redirected output to `STARTUP_LOG.txt`. Windows denied the second open while
the helper held the file. Alpha 1.1 redirects the silent helper to `NUL`, leaves
Uvicorn as the sole long-running log writer and adds a launcher regression test.

## Release-gate result

The v2.23.0 Alpha 2 tree completed with **202 tests passed, 0 failed and 4
skipped**. The remaining skips are the documented optional native-RDKit backend;
the primary browser/WASM EnviroDesign path remains covered. Python compilation,
guided JavaScript, expert JavaScript and service-worker syntax checks passed.
