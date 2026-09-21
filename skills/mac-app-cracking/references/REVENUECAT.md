# RevenueCat Plist Internals

Deep dive into how RevenueCat stores license data on macOS — and how to inject it.

## File Location

```
~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
```

Example: `~/Library/Containers/com.linearity.vn/Data/Library/Preferences/com.revenuecat.user_defaults.plist`

## Structure

The plist is **not** a simple key-value store. It's a **binary plist** containing these keys:

| Key | Type | Content |
|---|---|---|
| `com.revenuecat.userdefaults.appUserID.new` | String | UUID identifying this installation |
| `com.revenuecat.userdefaults.purchaserInfo.{UID}` | Data | **Binary plist of a JSON string** — the nested license blob |
| `com.revenuecat.userdefaults.purchaserInfoLastUpdated.{UID}` | Date | Last fetch timestamp |
| `com.revenuecat.userdefaults.etag.{UID}` | String | HTTP ETag for cache validation |

## The Double Encoding

This is the critical insight that makes RevenueCat different from simple UserDefaults injection:

```
Level 1: com.revenuecat.user_defaults.plist (binary plist)
  └── Key: "com.revenuecat.userdefaults.purchaserInfo.{UID}"
      └── Value: NSData (binary blob)
          └── Level 2: Binary plist of a UTF-8 JSON string
              └── Level 3: The actual purchaserInfo JSON
```

You **cannot** use `defaults write` for this. You must:

1. Build the JSON dictionary
2. Encode as UTF-8 JSON string
3. Wrap in `plistlib.dumps(json_bytes, fmt=FMT_BINARY)` — this creates the Level 2 binary plist
4. Put that blob inside the Level 1 plist

## purchaserInfo JSON Schema

```json
{
  "schema_version": "3",
  "first_seen": "2026-01-01T00:00:00Z",
  "original_app_user_id": "UUID",
  "original_source": "main",
  "entitlement_verification": 1,
  "request_date": "2026-01-01T00:00:00Z",
  "subscriber": {
    "first_seen": "2026-01-01T00:00:00Z",
    "management_url": null,
    "original_app_user_id": "UUID",
    "entitlements": {
      "pro": {
        "product_identifier": "app_pro_yearly",
        "purchase_date": "2026-01-01T00:00:00Z",
        "original_purchase_date": "2026-01-01T00:00:00Z",
        "expires_date": "2099-01-01T00:00:00Z",
        "is_sandbox": false,
        "ownership_type": "PURCHASED",
        "store": "APP_STORE",
        "is_active": true,
        "will_renew": true,
        "period_type": "NORMAL",
        "latest_purchase_date": "2026-01-01T00:00:00Z"
      }
    },
    "subscriptions": {
      "app_pro_yearly": {
        "product_identifier": "app_pro_yearly",
        "purchase_date": "2026-01-01T00:00:00Z",
        "original_purchase_date": "2026-01-01T00:00:00Z",
        "expires_date": "2099-01-01T00:00:00Z",
        "is_sandbox": false,
        "ownership_type": "PURCHASED",
        "store": "APP_STORE",
        "is_active": true,
        "will_renew": true,
        "period_type": "NORMAL",
        "latest_purchase_date": "2026-01-01T00:00:00Z",
        "unsubscribe_detected_at": null,
        "billing_issues_detected_at": null
      }
    },
    "non_subscriptions": {}
  }
}
```

## Key Fields That Matter

| Field | Value | Why |
|---|---|---|
| `entitlements.pro.is_active` | `true` | The app checks this to unlock Pro |
| `entitlements.pro.expires_date` | `"2099-01-01T00:00:00Z"` | Far future — never expires |
| `entitlements.pro.product_identifier` | Match the app's product ID | Must match what the app expects |
| `subscriptions.{id}.is_active` | `true` | Some apps check subscription status directly |
| `ownership_type` | `"PURCHASED"` | Not trial, not sandbox |

## Immutability Lock

RevenueCat's SDK will **overwrite** this plist on next launch — even with `chmod 444`. The SDK uses `NSFileHandle` write which bypasses POSIX permissions.

Solution: `chflags uchg` — the **system immutable flag**. This is a kernel-level flag that prevents any modification, even by the same user.

```bash
chflags uchg ~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
```

To remove:
```bash
chflags nouchg ~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
```

## App User ID (UID)

The UID is a UUID assigned per installation. It's stored in:
- `com.revenuecat.userdefaults.appUserID.new`
- Used as part of the key names: `purchaserInfo.{UID}`, `purchaserInfoLastUpdated.{UID}`

The UID format uses capital hex groups separated by dashes, but with a custom 4-4-4-4-8-6 split instead of the standard 8-4-4-4-12:
```
6205D4A4-C0E1-7080-92D7-D912C6D94712
```

If the UID in `appUserID.new` doesn't match the UID in the key names, RevenueCat will ignore the cached data and re-fetch from the server.

## Debugging

### Read the plist
```bash
plutil -p ~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
```

### Extract the inner purchaserInfo
```python
import plistlib, json
from pathlib import Path

p = Path.home() / "Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist"
with open(p, "rb") as f:
    prefs = plistlib.load(f)

for key, val in prefs.items():
    if "purchaserInfo" in key and not key.endswith("LastUpdated"):
        # val is a binary plist of a JSON string — double-decode:
        inner = plistlib.loads(val)
        print(json.dumps(json.loads(inner), indent=2))
```

### Check immutable flag
```bash
ls -lO ~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
# Look for "uchg" in the flags column
```

### Wipe and start fresh
```bash
chflags nouchg ~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
rm ~/Library/Containers/{BUNDLE_ID}/Data/Library/Preferences/com.revenuecat.user_defaults.plist
```

## Multi-Layer License Attacks

RevenueCat is often paired with Superwall and AppsFlyer. Each layer has its own checks:

| Layer | Framework | What to block |
|---|---|---|
| RevenueCat | `RevenueCat_RevenueCat.bundle` | `api.revenuecat.com` |
| Superwall | `SuperwallKit_SuperwallKit.bundle` | `subscriptions-api.superwall.com`, `.dev` |
| AppsFlyer | `AppsFlyerLib.framework` | Usually analytics-only, no license block needed |

Block all three in `/etc/hosts` and inject the RevenueCat plist — the app falls through Superwall's paywall because RevenueCat reports Pro active.

## References

- [RevenueCat iOS SDK — PurchaserInfo](https://github.com/RevenueCat/purchases-ios/blob/main/Sources/Purchasing/PurchaserInfo.swift)
- [RevenueCat Identity — App User ID](https://www.revenuecat.com/docs/customer-info#app-user-id)
- [macOS chflags manual](https://ss64.com/mac/chflags.html)