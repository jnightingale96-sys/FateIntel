# REACH review-bundle decision record — v2.20

## Outcome

The supplied follow-on patch was not applied verbatim. Its useful ideas were implemented as an evidence-bound **REACH preparation/review bundle**. The output is intentionally not named `iuclid.xml`, not given an `.i6z` extension and not described as submission-ready.

## Why the boundary matters

IUCLID chemical-information exchange uses a versioned, structured archive format. A single ad-hoc `<IUCLID_Dossier>` XML document is not equivalent to a valid IUCLID dossier. Current IUCLID formats, templates and validation rules must be sourced and tested through the official IUCLID workflow before EnviroChem can claim import or submission compatibility.

PNEC assessment-factor selection also cannot be inferred safely from a label such as “acute fish LC50” or “chronic fish NOEC”. The usable dataset, trophic-level coverage, study validity, compartment and other expert considerations affect the derivation. An ECHA substance-evaluation example applies different factors after rejecting part of a chronic dataset, illustrating why a small endpoint-type lookup is insufficient.

Primary references used for this decision:

- ECHA, *Guidance on information requirements and chemical safety assessment, Chapter R.10: Characterisation of dose [concentration]-response for environment*: https://echa.europa.eu/documents/10162/13632/information_requirements_r10_en.pdf
- ECHA substance-evaluation conclusion for trixylyl phosphate, including the aquatic dataset/assessment-factor reasoning in section 7.8.4: https://chem.echa.europa.eu/api-activity-list/v1/substanceEvaluation/documents?name=9aa5b8e1a03cc24227d1b87cdef1619a_SEV-246-677-8-1_conclusion_and_report_public.pdf
- Official IUCLID site and format resources: https://iuclid6.echa.europa.eu/

The ECHA guidance assists compliance but is not itself the legal text; regulatory decisions remain the responsibility of a qualified assessor.

## Supplied ideas implemented

| Supplied idea | v2.20 implementation |
| --- | --- |
| Concentration unit conversion | Strict decimal conversion for `ng/L`, `µg/L`, `mg/L` and `g/L`; ASCII `ug/L` and Greek mu aliases are accepted |
| PNEC calculation | Normalises the stored critical endpoint, divides by an explicit AF, and records endpoint, evidence ID, rationale, reference, formula and review status |
| Manifest | Canonical JSON with sorted payload entries, exact byte sizes and SHA-256 hashes |
| RSA signing | Optional detached RSA-PSS/SHA-256 signature over the exact `manifest.json` bytes; minimum 2048-bit key and SHA-256 public-key fingerprint |
| Human-readable summary | Dependency-free HTML with every dynamic value escaped |
| XML | EnviroChem-native `urn:envirochem:reach-review:1` interchange view, explicitly non-IUCLID |
| Verification | In-memory ZIP inspection with no extraction, path/duplicate/encryption/size/ratio controls, complete manifest reconciliation, hash checks, fingerprint check and signature verification |
| Browser integration | Expert Workspace form bound to the active project, confirmed chemical, reviewed profile and stored evidence |
| Audit | Manifest hash, bundle hash, selected record IDs, signing mode, key fingerprint and non-submission boundary are recorded |

## Deliberate differences from the supplied patch

- No built-in “ECHA-like” endpoint-to-factor table. The reviewer must supply and justify the AF; invalid or missing factors never silently receive a default.
- No HMAC signing. HMAC does not provide independent third-party verification because signer and verifier share the same secret.
- RSA-PSS is used for a new signature design instead of PKCS#1 v1.5.
- No fallback from failed RSA to HMAC or unsigned output. Requested signing either succeeds or the export fails.
- No arbitrary filesystem evidence paths, uploaded filenames or server output paths. Export content is built from database records already bound to the selected chemical/project.
- No missing-evidence warnings followed by export. Every selected record must exist and belong to the selected chemical; the critical endpoint must be a supported stored aquatic ecotoxicity record.
- No unescaped HTML and no naive ZIP extraction.
- No optional IUCLID XSD switch. The supplied custom XML could not become IUCLID-valid merely by pointing at an XSD. Official compatibility is a separate future adapter with controlled fixtures and conformance testing.
- No private key or placeholder secret in source control. Only an operator-configured key path is accepted.

## Bundle contents

| Path | Role |
| --- | --- |
| `README.txt` | Plain-language non-submission and trust boundary |
| `reach-review.json` | Canonical review record and primary machine-readable payload |
| `reach-review.xml` | EnviroChem-native XML view |
| `csr-review.html` | Escaped reviewer summary |
| `manifest.json` | Exact payload hashes, release, boundary and signing metadata |
| `manifest.sig` | Optional detached RSA-PSS signature |

`manifest.json` deliberately excludes itself and `manifest.sig` from its payload-file list; the scope is recorded in the manifest. The detached signature signs the exact manifest bytes.

## API surface

- `GET /api/reach/review-bundles/capabilities`
- `POST /api/reach/pnec/derive`
- `POST /api/reach/review-bundles`
- `POST /api/reach/review-bundles/verify`

The verifier returns `integrity_valid`, `verification_complete`, `signature_status` and `valid` separately. A signed bundle inspected without a public key may have valid payload hashes while remaining incomplete/untrusted.

## Remaining work before regulatory submission integration

1. Select an exact IUCLID release and applicable REACH dossier template.
2. Obtain and pin official format/schema/validation assets under a controlled update process.
3. Map every required IUCLID entity/document and cross-reference, with licensed example fixtures.
4. Validate imports in a matching IUCLID environment and run official validation/completeness checks.
5. Add organisation identity, certificate/trust-chain policy, protected key custody and signer authorization.
6. Add authentication, authorization, tenancy and immutable storage before any public or multi-user deployment.
7. Obtain regulatory and legal review of the complete submission workflow.
