# v2.21 proposal review and implementation record

Date: 2026-08-16

## Decision summary

The supplied material contained useful product-design ideas, a standalone React/Tailwind mock, and a proposed mobile calculation API. v2.21 adopts the ideas that strengthen the existing evidence-led workflow without introducing a second disconnected interface or unsupported exposure assumptions.

## Implemented

| Proposal | v2.21 implementation |
| --- | --- |
| Chemical profile with readiness and provenance | Native Expert Dashboard card bound to the current project, chemical, profile and evidence records |
| “Why this number?” interactions | Profile provenance dialog showing value, review status, profile origin, source summary and update time |
| Searchable Evidence Explorer | Text and endpoint filtering over live API records, plus record-level source and endpoint inspection |
| Provenance identifiers | Canonical SHA-256 hash over the returned evidence source/endpoint snapshot |
| Mobile/home-use bridge | Home App can bind confirmed identity and reviewed profile values from the selected workspace chemical |
| Consumer-friendly output | Qualitative route/fate explanation with explicit input basis and non-risk boundary |

## Not implemented

| Supplied idea | Reason |
| --- | --- |
| Parallel React/Vite/Tailwind prototype | It used mock data, duplicated the maintained vanilla interface, omitted a required Vite React dependency and was not bound to project/profile/evidence gates |
| Mock barcode-to-active database | A fabricated product registry can misidentify active ingredients; barcode remains a manual reference until a reviewed registry is available |
| Fixed 50% WWTP removal | No chemical-specific evidence or authoritative default was supplied |
| One household use divided through a 10,000-person plant | Population prevalence, use distribution and catchment mass are missing; the resulting concentration would be misleading |
| Implicit 1 g/mL density for volume inputs | Product density and active fraction must be explicit and evidenced before mass conversion |
| One-day effluent mass spread over 100 m² of soil | This is not a defensible land-application scenario |
| Fake IUCLID XML / typed-password signature | Review bundles remain explicitly non-IUCLID; cryptographic signing stays detached RSA-PSS with fail-closed capability checks |
| Simulated AI Copilot answers | The existing rule-based explainer remains source-bound; no ungrounded generated conclusions were added |

## Scientific boundary

The Home App calculates annual product use in the entered product unit and explains likely release pathways. It does not infer active-ingredient mass, product composition, wastewater removal, receiving-water PEC, PNEC or risk quotient. Quantitative exposure must continue through the reviewed emission, WWTP and receiving-environment workflows.
