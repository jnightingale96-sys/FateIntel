"""Command-line verification for an EnviroChem REACH review bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .exporter import BundleVerificationError, MAX_BUNDLE_BYTES, verify_review_bundle
from .signing import SigningError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Path to an EnviroChem REACH review ZIP")
    parser.add_argument("--public-key", type=Path, help="Trusted RSA public key PEM")
    parser.add_argument("--require-signature", action="store_true")
    args = parser.parse_args()
    try:
        if args.bundle.stat().st_size > MAX_BUNDLE_BYTES:
            raise BundleVerificationError("Bundle exceeds the 25 MiB verification limit")
        bundle = args.bundle.read_bytes()
        public_key = args.public_key.read_bytes() if args.public_key else None
        result = verify_review_bundle(bundle, public_key_pem=public_key)
        if args.require_signature and result["signature_mode"] != "rsa":
            result["valid"] = False
            result["issues"].append("a signature was required but the bundle is unsigned")
    except (OSError, BundleVerificationError, SigningError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
