# Mac App Crack Sites — Canonical Source List

Comprehensive list of websites used for sourcing `.dmg`/`.app` files to test the mac-app-cracking pipeline. Updated 2026-09-14.

## Primary Sources (Direct Downloads)

|#|Site|Type|Notes|
|---|---|---|---|
|1|**cmacapps.com**|Direct|Clean App Store rips, fast mirrors, categorized|
|2|**appstorrent.ru**|Tracker|Russian torrent tracker, massive library (`.dmg` + `.pkg`), requires account|
|3|**nmac.to**|Direct|Categorized, searchable, updated daily|
|4|**macdrop.net**|Direct|Clean rips, minimal ads, fast CDN|
|5|**macbed.com**|Direct + Forum|Forum-based with direct downloads, English/Russian|
|6|**appked.com**|Direct|Scene release mirror site, fast updates, categorized|
|7|**xmac.app**|Direct|Clean App Store rips, minimal bloat|
|8|**haxmac.cc**|Direct|Some require referral/premium, good selection|

## Forum-Based Sources

|#|Site|Type|Notes|
|---|---|---|---|
|9|**macbb.org**|Forum|User uploads, requires account, largest community|
|10|**mac-torrent-download.net**|Forum + Torrent|Request section, both torrent and direct links|

## Torrent Trackers

|#|Site|Type|Notes|
|---|---|---|---|
|11|**torrentmac.net**|Torrent|Large archive, active seeders, pirate-focused|
|12|**macapp.org.ua**|Tracker|Ukrainian tracker, huge catalog, `.dmg` + `.pkg`|

## Alternative / Aggregators

|#|Site|Type|Notes|
|---|---|---|---|
|13|**macapps.link**|Package Manager|Homebrew-style install, quick reference only — not for cracking|

## Site Status & Reliability

|Site|Status (2026-09)|Uptime|Requires VPN?|
|---|---|---|---|
|cmacapps.com|🟢 Active|High|No|
|appstorrent.ru|🟢 Active|High|Sometimes (Russia-hosted)|
|nmac.to|🟢 Active|High|No|
|macdrop.net|🟡 Intermittent|Medium|No|
|macbed.com|🟢 Active|High|No|
|appked.com|🟢 Active|High|No|
|xmac.app|🟢 Active|Medium|No|
|haxmac.cc|🟡 Limited|Medium|No|
|macbb.org|🟢 Active|High|No|
|mac-torrent-download.net|🟡 Slowing|Low-Medium|No|
|torrentmac.net|🟢 Active|Medium|No|
|macapp.org.ua|🟡 Sporadic|Low-Medium|Sometimes|
|macapps.link|🟢 Active|High|No|

## Sourcing Workflow

```
1. Check cmacapps.com first (cleanest rips, fastest DL)
2. If not found → nmac.to (best search, updated daily)
3. If not found → appstorrent.ru (largest library, Russian mirror)
4. If not found → macbb.org (community uploads, newest apps)
5. If not found → torrentmac.net (archive depth)
6. If still not found → Google dork: "{app_name} mac dmg" or "{app_name} cmacapps"
```

## Red Flags — AVOID These

- **Any site requiring `.exe` download** — `.exe` on a Mac site = malware, leave immediately
- **Sites demanding payment for "premium access"** — all legitimate sites are free or account-only
- **Pop-up-ridden sites** — if a site throws 5 popups before you can click anything, it's compromised
- **Sites with "installer" DMGs** — legitimate cracked apps are the `.app` directly or a clean `.dmg`/`.pkg`, never a third-party "installer"
- **Sites requiring browser extensions** — immediate red flag, leave

## Verification Checklist (Before Using an App)

```bash
# 1. Mount the DMG
hdiutil attach AppName.dmg -mountpoint /tmp/verify -nobrowse

# 2. Check for suspicious files
find /tmp/verify -name "*.exe" -o -name "*.sh" -o -name "*.command" -o -name "*.pkg" -o -name "install*"

# 3. Check app structure
ls "/tmp/verify/AppName.app/Contents/MacOS/"

# 4. VirusTotal scan
# Upload the .app binary to virustotal.com before running

# 5. Check code signature
codesign -dv --verbose=4 "/tmp/verify/AppName.app"

# 6. Detach
hdiutil detach /tmp/verify -quiet
```

## Notes

- `.dmg` files are preferred over `.pkg` torrents — cleaner, easier to extract
- Sites come and go. If a site is down, try Wayback Machine or check macbb.org for mirrors
- Some sites geo-block. Use a US VPN if needed
- Not all apps on these sites are actually cracked. Some are just the vanilla app with a trial prompt. Test before packaging.

---

*LTX-QUASAR · CRACK_SITES.md · Updated 2026-09-14*