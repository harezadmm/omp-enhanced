#!/usr/bin/env python3
"""
Standalone RevenueCat license injector for macOS apps.
No dependencies beyond Python 3 stdlib.

Usage:
    python3 inject_revenuecat.py \\
        --bundle-id com.example.app \\
        --product-id app_pro_yearly \\
        [--uid CUSTOM-UID] \\
        [--dry-run]

What it does:
    1. Finds the RevenueCat plist at ~/Library/Containers/BUNDLE_ID/Data/...
    2. Injects fake purchaserInfo with Pro lifetime (expires 2099)
    3. Locks plist with chflags uchg (immutable)
"""

import argparse
import json
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_uid() -> str:
    """Generate deterministic UID or use provided one."""
    return "6205D4A4-C0E1-7080-92D7-D912C6D94712"


def build_purchaser_info(product_id: str, uid: str) -> dict:
    return {
        "schema_version": "3",
        "first_seen": "2026-01-01T00:00:00Z",
        "original_app_user_id": uid,
        "original_source": "main",
        "entitlement_verification": 1,
        "request_date": "2026-01-01T00:00:00Z",
        "subscriber": {
            "first_seen": "2026-01-01T00:00:00Z",
            "management_url": None,
            "original_app_user_id": uid,
            "entitlements": {
                "pro": {
                    "product_identifier": product_id,
                    "purchase_date": "2026-01-01T00:00:00Z",
                    "original_purchase_date": "2026-01-01T00:00:00Z",
                    "expires_date": "2099-01-01T00:00:00Z",
                    "is_sandbox": False,
                    "ownership_type": "PURCHASED",
                    "store": "APP_STORE",
                    "is_active": True,
                    "will_renew": True,
                    "period_type": "NORMAL",
                    "latest_purchase_date": "2026-01-01T00:00:00Z",
                }
            },
            "subscriptions": {
                product_id: {
                    "product_identifier": product_id,
                    "purchase_date": "2026-01-01T00:00:00Z",
                    "original_purchase_date": "2026-01-01T00:00:00Z",
                    "expires_date": "2099-01-01T00:00:00Z",
                    "is_sandbox": False,
                    "ownership_type": "PURCHASED",
                    "store": "APP_STORE",
                    "is_active": True,
                    "will_renew": True,
                    "period_type": "NORMAL",
                    "latest_purchase_date": "2026-01-01T00:00:00Z",
                    "unsubscribe_detected_at": None,
                    "billing_issues_detected_at": None,
                }
            },
            "non_subscriptions": {},
        },
    }


def inject(bundle_id: str, product_id: str, uid: str, dry_run: bool = False) -> bool:
    plist_path = (
        Path.home()
        / "Library"
        / "Containers"
        / bundle_id
        / "Data"
        / "Library"
        / "Preferences"
        / "com.revenuecat.user_defaults.plist"
    )

    if not plist_path.parent.parent.parent.parent.exists():
        print(f"⚠ Container dir not found: {plist_path.parent.parent.parent.parent}")
        print("  Launch app once first to create it.")
        return False

    # Build the payload
    info = build_purchaser_info(product_id, uid)
    json_bytes = json.dumps(info, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    data_blob = plistlib.dumps(json_bytes, fmt=plistlib.FMT_BINARY)
    now = datetime(2026, 1, 1, 0, 0, 0)

    if dry_run:
        print(f"[DRY RUN] Would write to: {plist_path}")
        print(f"[DRY RUN] purchaserInfo size: {len(data_blob)} bytes")
        print(f"[DRY RUN] JSON payload:")
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return True

    # Remove existing immutability
    subprocess.run(["chflags", "nouchg", str(plist_path)], capture_output=True)

    # Create parent dirs
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing prefs (if any) to preserve other keys
    existing = {}
    if plist_path.exists():
        try:
            with open(plist_path, "rb") as f:
                existing = plistlib.load(f)
        except Exception:
            pass  # Start fresh

    # Merge our keys
    existing["com.revenuecat.userdefaults.appUserID.new"] = uid
    existing[f"com.revenuecat.userdefaults.purchaserInfo.{uid}"] = data_blob
    existing[f"com.revenuecat.userdefaults.purchaserInfoLastUpdated.{uid}"] = now

    # Write
    with open(plist_path, "wb") as f:
        plistlib.dump(existing, f, fmt=plistlib.FMT_BINARY)

    # Lock immutable
    result = subprocess.run(
        ["chflags", "uchg", str(plist_path)], capture_output=True
    )
    if result.returncode != 0:
        print("⚠ Could not set immutable flag (may need sudo)")
        return False

    print(f"✓ RevenueCat Pro license injected → {plist_path}")
    print(f"  Product: {product_id}")
    print(f"  Expires: 2099-01-01")
    print(f"  Locked:  uchg (immutable)")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Inject RevenueCat Pro license into macOS app"
    )
    parser.add_argument("--bundle-id", required=True, help="App bundle ID (e.g. com.example.app)")
    parser.add_argument("--product-id", required=True, help="RevenueCat product ID (e.g. app_pro_yearly)")
    parser.add_argument("--uid", help="Custom app user ID (UUID format)")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without writing")
    args = parser.parse_args()

    uid = args.uid or get_uid()
    success = inject(args.bundle_id, args.product_id, uid, args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()