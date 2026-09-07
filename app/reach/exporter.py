"""Build and verify EnviroChem REACH review bundles.

The archive is an auditable hand-off package.  It is not an IUCLID ``.i6z``
archive, a REACH-IT submission, or a replacement for regulatory review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from io import BytesIO
import json
from pathlib import PurePosixPath
from typing import Any
import zipfile
from xml.etree import ElementTree as ET

from .signing import (
    RSAPSSSigner,
    SigningError,
    public_key_fingerprint,
    verify_rsa_pss,
)


REVIEW_SCHEMA = "urn:envirochem:reach-review:1"
MANIFEST_SCHEMA = "urn:envirochem:reach-review-manifest:1"
MAX_BUNDLE_BYTES = 25 * 1024 * 1024
MAX_MEMBER_BYTES = 10 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 40 * 1024 * 1024
MAX_MEMBERS = 20
REQUIRED_PAYLOAD_FILES = {
    "README.txt",
    "reach-review.json",
    "reach-review.xml",
    "csr-review.html",
}


class BundleVerificationError(ValueError):
    """Raised when an archive is malformed or unsafe to inspect."""


@dataclass(frozen=True)
class BundleBuildResult:
    data: bytes
    manifest_sha256: str
    bundle_sha256: str
    signing_mode: str
    key_fingerprint_sha256: str | None


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _utc_iso(value: datetime | None = None) -> str:
    moment = value or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _xml_text(parent: ET.Element, name: str, value: object | None) -> ET.Element:
    child = ET.SubElement(parent, name)
    child.text = "" if value is None else str(value)
    return child


def _review_xml(record: dict[str, Any]) -> bytes:
    namespace = REVIEW_SCHEMA
    ET.register_namespace("ecr", namespace)
    q = lambda name: f"{{{namespace}}}{name}"
    root = ET.Element(q("ReachReviewRecord"), {"schemaVersion": "1.0"})
    scope = ET.SubElement(root, q("Scope"))
    _xml_text(scope, q("SubmissionReady"), "false")
    _xml_text(scope, q("IUCLIDFormat"), "false")
    _xml_text(scope, q("Purpose"), "regulatory preparation and reviewer hand-off")

    project_data = record["project"]
    project = ET.SubElement(root, q("Project"))
    _xml_text(project, q("Id"), project_data.get("id"))
    _xml_text(project, q("Name"), project_data.get("name"))
    _xml_text(project, q("Jurisdiction"), project_data.get("jurisdiction"))

    chemical_data = record["chemical"]
    chemical = ET.SubElement(root, q("ChemicalIdentity"))
    for key, label in (
        ("id", "Id"),
        ("preferred_name", "PreferredName"),
        ("cas_number", "CASNumber"),
        ("molecular_formula", "MolecularFormula"),
        ("molecular_weight_g_mol", "MolecularWeightGMol"),
        ("smiles", "SMILES"),
        ("inchikey", "InChIKey"),
        ("identity_hash", "IdentityHash"),
    ):
        _xml_text(chemical, q(label), chemical_data.get(key))

    pnec_data = record["pnec_derivation"]
    critical = pnec_data["critical_endpoint"]
    pnec = ET.SubElement(root, q("PNECDerivation"))
    _xml_text(pnec, q("TargetCompartment"), pnec_data["target_compartment"])
    _xml_text(pnec, q("CriticalEvidenceId"), critical.get("evidence_id"))
    _xml_text(pnec, q("EndpointType"), critical["endpoint_type"])
    _xml_text(pnec, q("EndpointValue"), critical["value"])
    _xml_text(pnec, q("EndpointUnit"), critical["unit"])
    _xml_text(pnec, q("AssessmentFactor"), pnec_data["assessment_factor"])
    _xml_text(pnec, q("AssessmentFactorRationale"), pnec_data["assessment_factor_rationale"])
    _xml_text(pnec, q("GuidanceReference"), pnec_data["guidance_reference"])
    _xml_text(pnec, q("PNECValue"), pnec_data["pnec"]["value"])
    _xml_text(pnec, q("PNECUnit"), pnec_data["pnec"]["unit"])

    evidence = ET.SubElement(root, q("EvidenceSnapshot"))
    for item in record.get("evidence", []):
        row = ET.SubElement(evidence, q("EvidenceRecord"), {"id": str(item["id"])})
        _xml_text(row, q("PropertyCode"), item.get("property_code"))
        _xml_text(row, q("EndpointKind"), item.get("endpoint_kind"))
        _xml_text(row, q("OriginalValue"), item.get("original_value"))
        _xml_text(row, q("OriginalUnit"), item.get("original_unit"))
        _xml_text(row, q("SourceTitle"), item.get("source", {}).get("title"))
        _xml_text(row, q("SourceIdentifier"), item.get("source", {}).get("identifier"))

    review_data = record["review"]
    review = ET.SubElement(root, q("ReviewConfirmation"))
    _xml_text(review, q("ReviewerName"), review_data.get("reviewer_name"))
    _xml_text(review, q("ReviewerRole"), review_data.get("reviewer_role"))
    _xml_text(review, q("ConfirmedAt"), review_data.get("confirmed_at"))
    _xml_text(review, q("Statement"), review_data.get("statement"))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _html_value(value: object | None) -> str:
    return escape("—" if value in {None, ""} else str(value), quote=True)


def _review_html(record: dict[str, Any]) -> bytes:
    chemical = record["chemical"]
    profile = record["assessment_profile"]
    derivation = record["pnec_derivation"]
    critical = derivation["critical_endpoint"]
    evidence_rows = "".join(
        "<tr>"
        f"<td>{_html_value(item['id'])}</td>"
        f"<td>{_html_value(item.get('property_code'))}</td>"
        f"<td>{_html_value(item.get('original_value'))} {_html_value(item.get('original_unit'))}</td>"
        f"<td>{_html_value(item.get('source', {}).get('title'))}</td>"
        f"<td>{_html_value(item.get('reliability_score'))}</td>"
        "</tr>"
        for item in record.get("evidence", [])
    )
    model_rows = "".join(
        "<tr>"
        f"<td>{_html_value(item['id'])}</td>"
        f"<td>{_html_value(item.get('model_key'))}</td>"
        f"<td>{_html_value(item.get('model_version'))}</td>"
        f"<td>{_html_value(item.get('scenario_name'))}</td>"
        "</tr>"
        for item in record.get("model_runs", [])
    ) or '<tr><td colspan="4">No model runs selected.</td></tr>'
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>REACH review summary — {_html_value(chemical.get('preferred_name'))}</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1040px;margin:32px auto;padding:0 24px;color:#18312d}}
.boundary{{border:2px solid #9b2c2c;background:#fff5f5;padding:14px;margin:16px 0;font-weight:700}}
table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}th,td{{border:1px solid #ccd9d5;padding:8px;text-align:left;vertical-align:top}}
th{{background:#eef5f2}}code{{overflow-wrap:anywhere}}h1,h2{{color:#0d5c50}}
</style></head><body>
<h1>EnviroChem REACH review summary</h1>
<div class="boundary">Preparation/review artefact only. This is not an IUCLID dossier, not an .i6z archive, and not submission-ready.</div>
<h2>Identity</h2><table>
<tr><th>Name</th><td>{_html_value(chemical.get('preferred_name'))}</td><th>CAS</th><td>{_html_value(chemical.get('cas_number'))}</td></tr>
<tr><th>Formula</th><td>{_html_value(chemical.get('molecular_formula'))}</td><th>MW</th><td>{_html_value(chemical.get('molecular_weight_g_mol'))} g/mol</td></tr>
<tr><th>InChIKey</th><td colspan="3"><code>{_html_value(chemical.get('inchikey'))}</code></td></tr>
<tr><th>Identity hash</th><td colspan="3"><code>{_html_value(chemical.get('identity_hash'))}</code></td></tr>
</table>
<h2>Reviewed profile</h2><table>
<tr><th>Status</th><td>{_html_value(profile.get('review_status'))}</td><th>Profile hash</th><td><code>{_html_value(profile.get('profile_hash'))}</code></td></tr>
<tr><th>Log K<sub>ow</sub></th><td>{_html_value(profile.get('log_kow'))}</td><th>Soil DT50</th><td>{_html_value(profile.get('soil_dt50_days'))} days</td></tr>
</table>
<h2>Freshwater PNEC arithmetic</h2><table>
<tr><th>Critical evidence</th><td>#{_html_value(critical.get('evidence_id'))} · {_html_value(critical.get('endpoint_type'))}</td></tr>
<tr><th>Endpoint</th><td>{_html_value(critical.get('value'))} {_html_value(critical.get('unit'))} = {_html_value(critical.get('normalised_value'))} {_html_value(critical.get('normalised_unit'))}</td></tr>
<tr><th>Assessment factor</th><td>{_html_value(derivation.get('assessment_factor'))}</td></tr>
<tr><th>Rationale</th><td>{_html_value(derivation.get('assessment_factor_rationale'))}</td></tr>
<tr><th>Guidance/reference</th><td>{_html_value(derivation.get('guidance_reference'))}</td></tr>
<tr><th>Calculated PNEC</th><td><strong>{_html_value(derivation['pnec']['value'])} {_html_value(derivation['pnec']['unit'])}</strong></td></tr>
</table>
<h2>Selected evidence</h2><table><thead><tr><th>ID</th><th>Property</th><th>Value</th><th>Source</th><th>Reliability</th></tr></thead><tbody>{evidence_rows}</tbody></table>
<h2>Selected model runs</h2><table><thead><tr><th>ID</th><th>Model</th><th>Version</th><th>Scenario</th></tr></thead><tbody>{model_rows}</tbody></table>
<h2>Review confirmation</h2><p>{_html_value(record['review'].get('statement'))}</p>
<p><strong>Reviewer:</strong> {_html_value(record['review'].get('reviewer_name'))} · {_html_value(record['review'].get('reviewer_role'))}<br>
<strong>Confirmed:</strong> {_html_value(record['review'].get('confirmed_at'))}</p>
</body></html>"""
    return html.encode("utf-8")


def _readme() -> bytes:
    return (
        "EnviroChem REACH review bundle\n"
        "================================\n\n"
        "PURPOSE: regulatory preparation, evidence review and controlled hand-off.\n"
        "BOUNDARY: this archive is NOT an IUCLID dossier, NOT an .i6z archive, and\n"
        "NOT submission-ready. It must not be renamed or submitted to REACH-IT.\n\n"
        "reach-review.json is the canonical review record. reach-review.xml is an\n"
        "EnviroChem-native interchange view using the urn:envirochem namespace.\n"
        "csr-review.html is a human-readable summary. manifest.json records exact\n"
        "file hashes. If present, manifest.sig signs the exact manifest.json bytes.\n"
        "A valid signature proves integrity relative to a key; independently verify\n"
        "the key fingerprint before treating signer identity as trusted.\n"
    ).encode("utf-8")


def _zip_write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def build_review_bundle(
    record: dict[str, Any],
    *,
    exporter_version: str,
    signing_mode: str = "unsigned",
    private_key_pem: bytes | None = None,
    created_at: datetime | None = None,
) -> BundleBuildResult:
    if record.get("schema") != REVIEW_SCHEMA:
        raise ValueError(f"Review record schema must be {REVIEW_SCHEMA}")
    if record.get("scope", {}).get("submission_ready") is not False:
        raise ValueError("Review record must explicitly declare submission_ready=false")
    if signing_mode not in {"unsigned", "rsa"}:
        raise ValueError("Signing mode must be unsigned or rsa")

    record_bytes = canonical_json_bytes(record)
    if len(record_bytes) > MAX_MEMBER_BYTES:
        raise ValueError("Review record exceeds the bundle size limit")
    files = {
        "README.txt": _readme(),
        "reach-review.json": record_bytes,
        "reach-review.xml": _review_xml(record),
        "csr-review.html": _review_html(record),
    }
    manifest_files = [
        {
            "path": path,
            "size_bytes": len(data),
            "sha256": sha256(data).hexdigest(),
        }
        for path, data in sorted(files.items())
    ]

    signer = None
    if signing_mode == "rsa":
        if not private_key_pem:
            raise SigningError("RSA signing was requested but no private key was provided")
        signer = RSAPSSSigner.from_private_pem(private_key_pem)
        signature_metadata: dict[str, object] = signer.metadata()
    else:
        signature_metadata = {
            "mode": "unsigned",
            "reason": "Unsigned export was explicitly requested.",
        }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "bundle_format": "envirochem-reach-review",
        "bundle_format_version": "1.0",
        "created_at": _utc_iso(created_at),
        "exporter": {"name": "EnviroChem Studio", "version": exporter_version},
        "submission_status": "NOT_IUCLID_NOT_SUBMISSION_READY",
        "manifest_scope": "All payload files; excludes manifest.json and detached manifest.sig.",
        "chemical_identity_hash": record["chemical"].get("identity_hash"),
        "assessment_profile_hash": record["assessment_profile"].get("profile_hash"),
        "files": manifest_files,
        "signature": signature_metadata,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    signature = signer.sign(manifest_bytes) if signer is not None else None

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for path, data in sorted(files.items()):
            _zip_write(archive, path, data)
        _zip_write(archive, "manifest.json", manifest_bytes)
        if signature is not None:
            _zip_write(archive, "manifest.sig", signature)
    data = buffer.getvalue()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("Generated review bundle exceeds the size limit")
    return BundleBuildResult(
        data=data,
        manifest_sha256=sha256(manifest_bytes).hexdigest(),
        bundle_sha256=sha256(data).hexdigest(),
        signing_mode=signing_mode,
        key_fingerprint_sha256=(
            signer.public_key_fingerprint_sha256 if signer is not None else None
        ),
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BundleVerificationError(f"JSON object contains duplicate key {key!r}")
        result[key] = value
    return result


def _safe_member_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def _read_member(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        return archive.read(name)
    except (KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise BundleVerificationError(f"Could not safely read bundle member {name!r}") from exc


def verify_review_bundle(data: bytes, *, public_key_pem: bytes | None = None) -> dict[str, Any]:
    if not data or len(data) > MAX_BUNDLE_BYTES:
        raise BundleVerificationError("Bundle is empty or exceeds the 25 MiB verification limit")
    try:
        archive = zipfile.ZipFile(BytesIO(data), mode="r")
    except zipfile.BadZipFile as exc:
        raise BundleVerificationError("Bundle is not a valid ZIP archive") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise BundleVerificationError("Bundle contains too many files")
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise BundleVerificationError("Bundle contains duplicate file paths")
        if any(not _safe_member_name(name) for name in names):
            raise BundleVerificationError("Bundle contains an unsafe file path")
        if any(item.flag_bits & 0x1 for item in infos):
            raise BundleVerificationError("Encrypted ZIP members are not supported")
        if any(item.file_size > MAX_MEMBER_BYTES for item in infos):
            raise BundleVerificationError("A bundle member exceeds the 10 MiB limit")
        if sum(item.file_size for item in infos) > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise BundleVerificationError("Bundle exceeds the uncompressed size limit")
        for item in infos:
            if item.file_size > 1024 * 1024 and item.compress_size > 0:
                if item.file_size / item.compress_size > 200:
                    raise BundleVerificationError("Bundle contains a suspicious compression ratio")
        if "manifest.json" not in names:
            raise BundleVerificationError("Bundle does not contain manifest.json")

        manifest_bytes = _read_member(archive, "manifest.json")
        try:
            manifest = json.loads(manifest_bytes, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BundleVerificationError("manifest.json is not valid UTF-8 JSON") from exc
        if not isinstance(manifest, dict):
            raise BundleVerificationError("manifest.json must contain a JSON object")
        if manifest.get("schema") != MANIFEST_SCHEMA:
            raise BundleVerificationError("Unsupported review-bundle manifest schema")
        if manifest.get("submission_status") != "NOT_IUCLID_NOT_SUBMISSION_READY":
            raise BundleVerificationError("Manifest is missing the non-submission boundary")
        listed_files = manifest.get("files")
        if not isinstance(listed_files, list):
            raise BundleVerificationError("Manifest files must be a list")

        entries: dict[str, dict[str, object]] = {}
        for item in listed_files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise BundleVerificationError("Manifest contains an invalid file entry")
            path = item["path"]
            if path in entries or not _safe_member_name(path):
                raise BundleVerificationError("Manifest contains a duplicate or unsafe file path")
            entries[path] = item
        if not REQUIRED_PAYLOAD_FILES.issubset(entries):
            raise BundleVerificationError("Manifest omits a required review-bundle file")

        signature_meta = manifest.get("signature")
        if not isinstance(signature_meta, dict):
            raise BundleVerificationError("Manifest signature metadata is invalid")
        signature_mode = signature_meta.get("mode")
        allowed_extras = {"manifest.json"}
        if signature_mode == "rsa":
            if signature_meta.get("algorithm") != "rsa-pss-sha256":
                raise BundleVerificationError("Unsupported RSA signature algorithm")
            if signature_meta.get("signature_file") != "manifest.sig":
                raise BundleVerificationError("Detached signature filename is invalid")
            allowed_extras.add("manifest.sig")
            if "manifest.sig" not in names:
                raise BundleVerificationError("Signed bundle does not contain manifest.sig")
        elif signature_mode == "unsigned":
            if "manifest.sig" in names:
                raise BundleVerificationError("Unsigned bundle unexpectedly contains manifest.sig")
        else:
            raise BundleVerificationError("Unsupported signature mode")

        actual_payloads = set(names) - allowed_extras
        if actual_payloads != set(entries):
            raise BundleVerificationError("Archive payload files do not exactly match the manifest")
        issues: list[str] = []
        for path, item in entries.items():
            payload = _read_member(archive, path)
            if item.get("size_bytes") != len(payload):
                issues.append(f"size mismatch: {path}")
            if item.get("sha256") != sha256(payload).hexdigest():
                issues.append(f"sha256 mismatch: {path}")

        try:
            review_record = json.loads(
                _read_member(archive, "reach-review.json"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BundleVerificationError("reach-review.json is not valid UTF-8 JSON") from exc
        if not isinstance(review_record, dict):
            raise BundleVerificationError("reach-review.json must contain a JSON object")
        if review_record.get("schema") != REVIEW_SCHEMA:
            issues.append("unsupported reach-review.json schema")
        review_scope = review_record.get("scope")
        if not isinstance(review_scope, dict) or review_scope.get("submission_ready") is not False:
            issues.append("reach-review.json is missing submission_ready=false")

        signature_verified = False
        if signature_mode == "rsa" and public_key_pem is not None:
            expected_fingerprint = signature_meta.get("key_fingerprint_sha256")
            actual_fingerprint = public_key_fingerprint(public_key_pem)
            if expected_fingerprint != actual_fingerprint:
                issues.append("public key fingerprint does not match the manifest")
            else:
                signature_verified = verify_rsa_pss(
                    manifest_bytes,
                    _read_member(archive, "manifest.sig"),
                    public_key_pem,
                )
                if not signature_verified:
                    issues.append("manifest signature verification failed")

        integrity_valid = not issues
        verification_complete = signature_mode == "unsigned" or public_key_pem is not None
        valid = integrity_valid and (signature_mode == "unsigned" or signature_verified)
        return {
            "valid": valid,
            "integrity_valid": integrity_valid,
            "verification_complete": verification_complete,
            "signature_mode": signature_mode,
            "signature_verified": signature_verified,
            "signature_status": (
                "verified"
                if signature_verified
                else "public_key_required"
                if signature_mode == "rsa" and public_key_pem is None
                else "unsigned"
                if signature_mode == "unsigned"
                else "invalid"
            ),
            "manifest_sha256": sha256(manifest_bytes).hexdigest(),
            "bundle_sha256": sha256(data).hexdigest(),
            "files_checked": len(entries),
            "issues": issues,
            "boundary": "NOT_IUCLID_NOT_SUBMISSION_READY",
        }
