# EnviroChem Studio v2.23.0 Alpha 3

Build ID:  
`envirochem-studio-v2.23.0-alpha3-epa-execution-bridge-2026-09-05`

## Implemented

- Added a controlled local-execution bridge for PWC, ChemSTEER, CEM and E-FAST.
- Kept execution disabled by default and restricted it to server-configured
  executable paths, fixed argument templates and relative output patterns.
- Added executable SHA-256 acknowledgement, no-shell process launch, isolated
  run directories, timeouts, output/log capture and per-file hashes.
- Added a handoff ZIP for manual/GUI official runs. It includes the input
  manifest, expected-output map, structured-output template, run checklist and
  checksums; it contains no EPA software or database.
- Replaced pasted-text import for the four EPA tools with original-file upload,
  retained file hashes, operator/version metadata and genuine/authorised-run
  confirmations.
- Blocked scientific acceptance until genuine execution provenance exists and
  all recommended tool-specific outputs are mapped.
- Added PWC to the external integration catalogue with current 3.003 version
  context and pesticide-only applicability.
- Added a transparent US industrial soil-to-groundwater screen using explicit
  source-zone partitioning, retardation and first-order transformation.
- Restricted the US industrial source-term workbench to US + Industrial +
  Manufacturing/processing.
- Repositioned the native EU water–sediment screen at Tier 2+ and removed the
  misleading TOXSWA label. Official FOCUS_TOXSWA is pesticide-only at Tier 3–4.

## Deliberate boundary

- No EPA executable, source code, equation set or data package is included.
- No undocumented command-line capability is asserted. GUI tools remain manual
  handoff workflows unless an administrator validates and configures a genuine
  unattended contract.
- The new groundwater calculation is an EnviroChem screen, not PWC/PRZM.
- This is not yet a complete TSCA or FIFRA risk assessment implementation.
  Hazard/dose-response integration, ecological and susceptible-population
  pathways, dietary/residential pesticide models and programme-specific
  decision logic remain separate work.

## Verification

- Python compilation completed.
- Guided and Expert JavaScript syntax checks completed.
- Targeted bridge/routing/groundwater suite: 50 passed.
- Full suite: 225 passed; five optional tests skipped (four native-RDKit and one
  RSA test because the optional packages were unavailable).

