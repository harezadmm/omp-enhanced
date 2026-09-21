---
name: classical-cipher-analysis
description: >-
  Classical cipher analysis playbook. Use when encountering substitution
  ciphers, Vigenere, transposition, XOR, or encoded text in CTF challenges
  that requires frequency analysis, Kasiski examination, or known-plaintext
  cryptanalysis.
---

# SKILL: Classical Cipher Analysis — Expert Cryptanalysis Playbook

> **AI LOAD INSTRUCTION**: Expert classical cipher identification and breaking techniques for CTF. Covers cipher identification methodology (frequency analysis, IC, Kasiski), monoalphabetic substitution, Caesar/ROT, Vigenere, Enigma, affine, Hill, transposition ciphers, Bacon/Polybius/Playfair, and XOR ciphers. Base models often skip the identification step and jump to the wrong cipher type, or fail to recognize encoded (base64/hex) ciphertext that needs decoding before analysis.

## 0. RELATED ROUTING

- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) when dealing with modern symmetric ciphers (AES/DES) rather than classical
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) when the challenge involves hash-based constructions
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) when knapsack-based ciphers are encountered

### Quick identification guide

| Observation | Likely Cipher | First Action |
|---|---|---|
| All uppercase letters, uneven frequency | Monoalphabetic substitution | Frequency analysis |
| All uppercase, flat frequency distribution | Polyalphabetic (Vigenere) | IC + Kasiski |
| Only A-Z shifted uniformly | Caesar/ROT | Brute force 25 shifts |
| Base64 alphabet (A-Za-z0-9+/=) | Base64 encoded (decode first) | Base64 decode |
| Hex string (0-9a-f) | Hex encoded (decode first) | Hex decode |
| Binary (0s and 1s) | Binary encoded | Convert to ASCII |
| Dots and dashes | Morse code | Morse decode |
| Raised/normal text pattern | Bacon cipher | Map to A/B, decode |
| 2-digit number pairs (11-55) | Polybius square | Grid lookup |
| Text appears scrambled (right letters, wrong order) | Transposition | Anagram analysis |
| Non-printable bytes XOR-like | XOR cipher | Single/repeating key XOR analysis |

---

## 1. CIPHER IDENTIFICATION METHODOLOGY

### 1.1 Step 1: Character Set Analysis

```python
def analyze_charset(ciphertext):
    """Identify encoding/cipher by character set."""
    chars = set(ciphertext.strip())

    if chars <= set('01 \n'):
        return "Binary encoding"
    if chars <= set('.-/ \n'):
        return "Morse code"
    if chars <= set('0123456789abcdef \n'):
        return "Hex encoding"
    if chars <= set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n'):
        if '=' in ciphertext or len(ciphertext) % 4 == 0:
            return "Base64 encoding"
    if chars <= set('ABCDEFGHIJKLMNOPQRSTUVWXYZ \n'):
        return "Uppercase only — classical cipher"
    if all(c in '12345' for c in ciphertext.replace(' ', '').replace('\n', '')):
        return "Polybius square (digits 1-5)"

    return "Mixed charset — needs further analysis"
```

### 1.2 Step 2: Frequency Analysis

```python
from collections import Counter

def frequency_analysis(text):
    """Compute letter frequency distribution."""
    text = text.upper()
    letters = [c for c in text if c.isalpha()]
    total = len(letters)
    freq = Counter(letters)

    print("Letter frequencies:")
    for letter, count in freq.most_common():
        pct = count / total * 100
        bar = '#' * int(pct)
        print(f"  {letter}: {pct:5.1f}% {bar}")

    return freq

# English letter frequency (for comparison):
# E T A O I N S H R D L C U M W F G Y P B V K J X Q Z
# 12.7 9.1 8.2 7.5 7.0 6.7 6.3 6.1 6.0 4.3 4.0 2.8 ...
```

### 1.3 Step 3: Index of Coincidence (IC)

```python
def index_of_coincidence(text):
    """
    IC ≈ 0.065 → English / monoalphabetic substitution
    IC ≈ 0.038 → random / polyalphabetic cipher
    """
    text = [c for c in text.upper() if c.isalpha()]
    N = len(text)
    freq = Counter(text)

    ic = sum(f * (f - 1) for f in freq.values()) / (N * (N - 1))
    return ic

# Interpretation:
# IC > 0.060 → monoalphabetic (Caesar, simple substitution, Playfair)
# IC ≈ 0.045-0.055 → polyalphabetic with short key (Vigenere key < 10)
# IC ≈ 0.038-0.042 → polyalphabetic with long key or random
```

### 1.4 Step 4: Kasiski Examination (for Polyalphabetic)

```python
from math import gcd
from functools import reduce

def kasiski(ciphertext, min_len=3):
    """Find repeated sequences and their distances → key length."""
    text = ''.join(c for c in ciphertext.upper() if c.isalpha())
    distances = []

    for length in range(min_len, min(20, len(text) // 3)):
        for i in range(len(text) - length):
            seq = text[i:i+length]
            j = text.find(seq, i + 1)
            while j != -1:
                distances.append(j - i)
                j = text.find(seq, j + 1)

    if not distances:
        return None

    # Key length is likely GCD of common distances
    common_gcds = Counter()
    for d in distances:
        for factor in range(2, min(d + 1, 30)):
            if d % factor == 0:
                common_gcds[factor] += 1

    print("Likely key lengths (by frequency):")
    for length, count in common_gcds.most_common(5):
        print(f"  Key length {length}: {count} occurrences")

    return common_gcds.most_common(1)[0][0]
```

---

## 2. MONOALPHABETIC SUBSTITUTION

### 2.1 Frequency Analysis Attack

```python
def solve_substitution(ciphertext, interactive=False):
    """Solve monoalphabetic substitution via frequency analysis."""
    freq = frequency_analysis(ciphertext)

    # English frequency order
    eng_order = "ETAOINSRHLDCUMWFGYPBVKJXQZ"
    cipher_order = ''.join(c for c, _ in freq.most_common())

    # Initial mapping (frequency-based guess)
    mapping = {}
    for i, c in enumerate(cipher_order):
        if i < len(eng_order):
            mapping[c] = eng_order[i]

    # Apply mapping
    result = ""
    for c in ciphertext.upper():
        result += mapping.get(c, c)

    return result, mapping

# Better approach: use automated solvers
# quipqiup.com — online substitution solver
# dcode.fr/monoalphabetic-substitution — with word pattern matching
```

### 2.2 Known Plaintext (Crib Dragging)

If part of the plaintext is known (e.g., "flag{" prefix):

```python
def crib_drag_substitution(ciphertext, known_plain, known_cipher):
    """Build partial mapping from known plaintext-ciphertext pair."""
    mapping = {}
    for p, c in zip(known_plain.upper(), known_cipher.upper()):
        mapping[c] = p

    # Apply partial mapping
    result = ""
    for c in ciphertext.upper():
        result += mapping.get(c, '?')

    return result, mapping
```

---

## 3. CAESAR / ROT CIPHERS

### 3.1 Brute Force

```python
def caesar_bruteforce(ciphertext):
    """Try all 25 shifts, score by English frequency."""
    results = []
    for shift in range(26):
        decrypted = ""
        for c in ciphertext:
            if c.isalpha():
                base = ord('A') if c.isupper() else ord('a')
                decrypted += chr((ord(c) - base - shift) % 26 + base)
            else:
                decrypted += c

        # Chi-squared scoring against English frequency
        score = chi_squared_score(decrypted)
        results.append((shift, score, decrypted))

    results.sort(key=lambda x: x[1])
    return results[0]  # best match

def chi_squared_score(text):
    """Lower score = closer to English."""
    expected = {
        'E': 12.7, 'T': 9.1, 'A': 8.2, 'O': 7.5, 'I': 7.0,
        'N': 6.7, 'S': 6.3, 'H': 6.1, 'R': 6.0, 'D': 4.3,
        'L': 4.0, 'C': 2.8, 'U': 2.8, 'M': 2.4, 'W': 2.4,
        'F': 2.2, 'G': 2.0, 'Y': 2.0, 'P': 1.9, 'B': 1.5,
        'V': 1.0, 'K': 0.8, 'J': 0.2, 'X': 0.2, 'Q': 0.1, 'Z': 0.1,
    }
    text = text.upper()
    letters = [c for c in text if c.isalpha()]
    total = len(letters)
    if total == 0:
        return float('inf')

    freq = Counter(letters)
    score = sum(
        (freq.get(c, 0) / total * 100 - expected.get(c, 0)) ** 2 / max(expected.get(c, 0.1), 0.1)
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    )
    return score
```

### 3.2 ROT13 and ROT47

```python
import codecs

# ROT13 (letters only)
rot13 = codecs.decode(ciphertext, 'rot_13')

# ROT47 (ASCII 33-126)
def rot47(text):
    return ''.join(
        chr(33 + (ord(c) - 33 + 47) % 94) if 33 <= ord(c) <= 126 else c
        for c in text
    )
```

---

## 4. VIGENERE CIPHER

### 4.1 Full Attack Workflow

```
Step 1: Confirm polyalphabetic (IC ≈ 0.04-0.05)
Step 2: Find key length (Kasiski + IC per period)
Step 3: For each key position, solve as single Caesar cipher
Step 4: Assemble key → decrypt
```

### 4.2 IC-Based Key Length Detection

```python
def find_vigenere_key_length(ciphertext, max_key=20):
    """Use IC to find Vigenere key length."""
    text = [c for c in ciphertext.upper() if c.isalpha()]
    results = []

    for kl in range(1, max_key + 1):
        # Split text into kl columns
        columns = [[] for _ in range(kl)]
        for i, c in enumerate(text):
            columns[i % kl].append(c)

        # Average IC across columns
        avg_ic = sum(
            index_of_coincidence(''.join(col)) for col in columns
        ) / kl

        results.append((kl, avg_ic))
        print(f"  Key length {kl:2d}: IC = {avg_ic:.4f}")

    # Key length with IC closest to 0.065
    best = max(results, key=lambda x: x[1])
    return best[0]
```

### 4.3 Per-Position Frequency Attack

```python
def crack_vigenere(ciphertext, key_length):
    """Crack Vigenere given known key length."""
    text = [c for c in ciphertext.upper() if c.isalpha()]
    key = ""

    for pos in range(key_length):
        column = ''.join(text[i] for i in range(pos, len(text), key_length))
        # Solve as Caesar cipher
        shift, score, _ = caesar_bruteforce(column)
        key += chr(shift + ord('A'))

    # Decrypt
    plaintext = ""
    ki = 0
    for c in ciphertext:
        if c.isalpha():
            shift = ord(key[ki % key_length]) - ord('A')
            base = ord('A') if c.isupper() else ord('a')
            plaintext += chr((ord(c) - base - shift) % 26 + base)
            ki += 1
        else:
            plaintext += c

    return key, plaintext
```

---

## 5. AFFINE CIPHER

### 5.1 Definition

`E(x) = (a·x + b) mod 26` where gcd(a, 26) = 1.

Valid a values: 1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25 (12 values).

### 5.2 Brute Force (312 combinations)

```python
def crack_affine(ciphertext):
    """Brute force affine cipher: 12 × 26 = 312 combinations."""
    valid_a = [a for a in range(1, 26) if gcd(a, 26) == 1]

    for a in valid_a:
        a_inv = pow(a, -1, 26)
        for b in range(26):
            plaintext = ""
            for c in ciphertext.upper():
                if c.isalpha():
                    y = ord(c) - ord('A')
                    x = (a_inv * (y - b)) % 26
                    plaintext += chr(x + ord('A'))
                else:
                    plaintext += c

            score = chi_squared_score(plaintext)
            if score < 50:  # reasonable English
                print(f"a={a}, b={b}: {plaintext[:50]}...")
```

### 5.3 Known Plaintext

```python
def affine_from_known(plain1, cipher1, plain2, cipher2):
    """Recover (a, b) from two known plaintext-ciphertext pairs."""
    p1, c1 = ord(plain1) - ord('A'), ord(cipher1) - ord('A')
    p2, c2 = ord(plain2) - ord('A'), ord(cipher2) - ord('A')

    # c1 = a*p1 + b, c2 = a*p2 + b
    # c1 - c2 = a*(p1 - p2) mod 26
    diff_p = (p1 - p2) % 26
    diff_c = (c1 - c2) % 26

    if gcd(diff_p, 26) != 1:
        return None

    a = (diff_c * pow(diff_p, -1, 26)) % 26
    b = (c1 - a * p1) % 26
    return a, b
```

---

## 6. HILL CIPHER

Matrix-based cipher: `C = K · P mod 26` where K is an n×n key matrix.

### 6.1 Known-Plaintext Attack

```python
import numpy as np

def crack_hill(known_plain, known_cipher, n=2):
    """Recover Hill cipher key from known plaintext-ciphertext (mod 26)."""
    # Convert to numbers
    P = [ord(c) - ord('A') for c in known_plain.upper()]
    C = [ord(c) - ord('A') for c in known_cipher.upper()]

    # Build matrices (need at least n pairs of n-grams)
    P_matrix = np.array(P[:n*n]).reshape(n, n).T
    C_matrix = np.array(C[:n*n]).reshape(n, n).T

    # K = C · P⁻¹ mod 26
    # Need modular matrix inverse
    from sympy import Matrix
    P_mat = Matrix(P_matrix.tolist())
    C_mat = Matrix(C_matrix.tolist())

    P_inv = P_mat.inv_mod(26)
    K = (C_mat * P_inv) % 26

    return K
```

---

## 7. TRANSPOSITION CIPHERS

### 7.1 Rail Fence

```python
def rail_fence_decrypt(ciphertext, rails):
    """Decrypt rail fence cipher."""
    n = len(ciphertext)
    # Build the zigzag pattern
    pattern = []
    for i in range(n):
        row = 0
        cycle = 2 * (rails - 1)
        pos = i % cycle
        row = pos if pos < rails else cycle - pos
        pattern.append((row, i))

    pattern.sort()

    # Fill in characters
    result = [''] * n
    ci = 0
    for _, orig_pos in pattern:
        result[orig_pos] = ciphertext[ci]
        ci += 1

    return ''.join(result)

# Brute force all rail counts
for rails in range(2, 20):
    print(f"Rails {rails}: {rail_fence_decrypt(ct, rails)[:50]}")
```

### 7.2 Columnar Transposition

```python
def columnar_decrypt(ciphertext, key):
    """Decrypt columnar transposition given key word."""
    n_cols = len(key)
    n_rows = -(-len(ciphertext) // n_cols)  # ceiling division

    # Determine column order from key
    order = sorted(range(n_cols), key=lambda i: key[i])

    # Calculate column lengths (some may be shorter)
    full_cols = len(ciphertext) % n_cols
    if full_cols == 0:
        full_cols = n_cols

    # Split ciphertext into columns (in key order)
    columns = [''] * n_cols
    pos = 0
    for col_idx in order:
        col_len = n_rows if col_idx < full_cols else n_rows - 1
        columns[col_idx] = ciphertext[pos:pos + col_len]
        pos += col_len

    # Read off row by row
    plaintext = ''
    for row in range(n_rows):
        for col in range(n_cols):
            if row < len(columns[col]):
                plaintext += columns[col][row]

    return plaintext
```

---

## 8. XOR CIPHER

### 8.1 Single-Byte XOR

See [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) Section 4.2 for full implementation.

### 8.2 Multi-Byte XOR (xortool)

```bash
# Automatic key length detection and cracking
xortool ciphertext.bin -l 5        # try key length 5
xortool ciphertext.bin -b          # brute force key length
xortool ciphertext.bin -c 20       # assume most common char is space (0x20)
```

### 8.3 Known Plaintext XOR

```python
def xor_known_plaintext(ciphertext, known_plain, offset=0):
    """Recover XOR key from known plaintext at given offset."""
    key_fragment = bytes(
        c ^ p for c, p in zip(ciphertext[offset:], known_plain)
    )
    print(f"Key fragment: {key_fragment}")

    # If repeating key, infer full key from fragment
    return key_fragment
```

---

## 9. SPECIAL CIPHERS

### 9.1 Bacon Cipher

Binary encoding using two typefaces (A=normal, B=bold/italic).

```python
BACON = {
    'AAAAA': 'A', 'AAAAB': 'B', 'AAABA': 'C', 'AAABB': 'D',
    'AABAA': 'E', 'AABAB': 'F', 'AABBA': 'G', 'AABBB': 'H',
    'ABAAA': 'I', 'ABAAB': 'J', 'ABABA': 'K', 'ABABB': 'L',
    'ABBAA': 'M', 'ABBAB': 'N', 'ABBBA': 'O', 'ABBBB': 'P',
    'BAAAA': 'Q', 'BAAAB': 'R', 'BAABA': 'S', 'BAABB': 'T',
    'BABAA': 'U', 'BABAB': 'V', 'BABBA': 'W', 'BABBB': 'X',
    'BAAAA': 'Y', 'BAAAB': 'Z',
}

def decode_bacon(text):
    """Decode Bacon cipher: uppercase=B, lowercase=A (or similar mapping)."""
    binary = ''.join('B' if c.isupper() else 'A' for c in text if c.isalpha())
    result = ''
    for i in range(0, len(binary) - 4, 5):
        chunk = binary[i:i+5]
        result += BACON.get(chunk, '?')
    return result
```

### 9.2 Polybius Square

```
    1 2 3 4 5
  ┌──────────
1 │ A B C D E
2 │ F G H I/J K
3 │ L M N O P
4 │ Q R S T U
5 │ V W X Y Z

"HELLO" = "23 15 31 31 34"
```

### 9.3 Playfair

5×5 grid cipher encrypting digraphs.

```
Key: "MONARCHY" → grid:
  M O N A R
  C H Y B D
  E F G I/J K
  L P Q S T
  U V W X Z

Rules:
  Same row → shift right: HE → FE → "GF"
  Same col → shift down
  Rectangle → swap columns
```

---

## 10. DECISION TREE

```
Unknown ciphertext — how to identify and break?
│
├─ Step 1: Check encoding
│  ├─ Base64 alphabet with padding? → Decode first, then re-analyze
│  ├─ Hex string? → Convert to bytes, re-analyze
│  ├─ Binary (01)? → Convert to ASCII
│  ├─ Morse (.-/)? → Decode Morse
│  └─ Printable text? → Continue to Step 2
│
├─ Step 2: Character set
│  ├─ Only letters (A-Z)?
│  │  ├─ Compute IC
│  │  │  ├─ IC ≈ 0.065 → Monoalphabetic
│  │  │  │  ├─ Uniform shift in freq? → Caesar → brute force 25
│  │  │  │  ├─ Random-looking mapping? → Simple substitution → frequency analysis
│  │  │  │  └─ Digraph patterns? → Playfair → digraph analysis
│  │  │  │
│  │  │  ├─ IC ≈ 0.04-0.05 → Polyalphabetic
│  │  │  │  ├─ Kasiski → find key length
│  │  │  │  └─ Per-position frequency → crack Vigenere
│  │  │  │
│  │  │  └─ IC ≈ 0.038 → Very long key or one-time pad
│  │  │     └─ Look for key reuse or weak key generation
│  │  │
│  │  └─ Letters appear scrambled (right freq, wrong order)?
│  │     └─ Transposition
│  │        ├─ Rail fence → brute force rail count
│  │        └─ Columnar → try common key lengths
│  │
│  ├─ Numbers (digit pairs)?
│  │  ├─ Pairs in range 11-55 → Polybius square
│  │  └─ Numbers mod 26 → numeric substitution
│  │
│  ├─ Mixed case with pattern?
│  │  └─ Upper/lower encodes binary → Bacon cipher
│  │
│  └─ Non-printable bytes?
│     └─ XOR cipher
│        ├─ Single-byte key → brute force 256
│        ├─ Repeating key → xortool / Hamming distance
│        └─ Known plaintext → direct key recovery
│
└─ Step 3: Apply specific attack
   ├─ Substitution → quipqiup.com / frequency analysis
   ├─ Caesar → dcode.fr / brute force
   ├─ Vigenere → Kasiski + per-column Caesar
   ├─ Affine → brute force 312 combinations
   ├─ Hill → known-plaintext matrix attack
   ├─ Transposition → pattern analysis + brute force
   └─ XOR → xortool / crib dragging
```

---

## 11. TOOLS

| Tool | Purpose | URL/Usage |
|---|---|---|
| **CyberChef** | Universal encoding/cipher Swiss army knife | gchq.github.io/CyberChef |
| **dcode.fr** | 200+ cipher solvers online | dcode.fr |
| **quipqiup** | Automated substitution cipher solver | quipqiup.com |
| **xortool** | XOR cipher analysis and cracking | `pip install xortool` |
| **RsaCtfTool** | RSA + some classical cipher support | GitHub |
| **Ciphey** | Automated cipher detection and decryption | `pip install ciphey` |
| **hashID** | Identify hash types | `pip install hashid` |
| **Python** | Custom frequency analysis and scripting | All attacks above |

### CyberChef Recipes (Common)

```
ROT13:               ROT13
Caesar brute force:   ROT13 (with offset slider)
Base64 decode:        From Base64
Hex decode:           From Hex
XOR:                  XOR (key as hex/utf8)
Vigenere:             Vigenère Decode
Morse:                From Morse Code
```

---

## 12. CONFIRMING THE FINDING — RECOVERY, NOT A CRIB
Classical cryptanalysis is uniquely prone to **false confidence**: every candidate decryption looks
like text, and human pattern-matching will happily "find" meaning in noise. The confirmation step is
therefore the whole discipline.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the output match the **expected language statistics** (IoC, chi-squared, quadgrams)? | separates real plaintext from noise |
| 2 | Is the key **independently derivable** from a second ciphertext encrypted with the same key? | the key was found, not merely fitted to one sample |
| 3 | Does **re-encryption reproduce the ciphertext exactly**? | removes the ambiguity of a plausible-looking but wrong plaintext |
| 4 | Is the plaintext **coherent** across the whole message, not just a crib? | a crib match alone can be coincidence |
| 5 | Does the claimed key length survive **IoC/Kasiski** analysis? | the key length is the testable hypothesis |
| 6 | Is the recovered plaintext **consistent with the source** (language, format, known phrases)? | domain sanity check |
| 7 | Does the attack fail against a **random-key control** of the same length? | proves the method is measuring structure, not fitting noise |

**Re-encrypt to verify.** Once you have a key, encrypt the plaintext with it and compare to the
ciphertext byte-for-byte. This is the classical-cipher equivalent of `pow(m,e,n) == c`, and it
converts a guess into a proof.

**Beware the short-text trap.** Below roughly 50-100 characters, index of coincidence and frequency
analysis are statistically meaningless. If your message is short, a "successful" break is usually
overfitting — say so explicitly rather than reporting it.

**For XOR specifically, key length is the pivot.** Determine it with Hamming distance or IoC, solve
each column independently, then verify the whole key against a second ciphertext. A key that
decrypts one message correctly but fails on a second is a coincidence.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **ciphertext** in full, exactly as captured | the attack is reproducible only from the exact bytes |
| The **identification reasoning** (IoC, letter frequency, Kasiski, known-plaintext hints) | justifies why this cipher family was chosen over the others |
| The **recovered key and plaintext** | the artefacts the finding is about |
| The **verification output** — re-encryption matching the ciphertext, and the statistic (IoC/chi-squared) | the proof; without it the plaintext is a hypothesis |
| The **message length** and an explicit note on whether statistics are meaningful at that length | short-text false positives are the dominant error in this domain |
| The **method and tool** (frequency analysis, Kasiski, crib, `xortool`, brute force range) | reproducibility and to show the search space was covered |
| For XOR: the **derived key length** and the evidence for it (Hamming distance normalised per key size) | the pivotal parameter |
| **Negative control** — the same method applied to random ciphertext of equal length yields incoherent output | proves the method measures structure |

Report the **method and the verification**: "IoC of 0.066 at key length 7 confirms a Vigenère
cipher; the recovered key `LEMON` re-encrypts the full ciphertext exactly and decrypts a second
message from the same set", never "the text appears to be a Vigenère cipher".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| Output "looks like text" but fails re-encryption | pattern-matching, not decryption |
| Statistics computed on fewer than ~50 characters | IoC and frequency analysis are meaningless at that length |
| A key that decrypts one message but not a second with the same key | coincidence, not recovery |
| A crib word appears by chance (common short words) | needs whole-message coherence to be meaningful |
| Multiple plausible keys produce readable output (e.g. short Caesar on short text) | ambiguity; the key space was not narrowed, only sampled |
| Base64/hex "decoded" output that is not valid UTF-8 or known format | two layers conflated; the encoding was misidentified |
| The "cipher" is actually an encoding (Base64, hex) | not cryptography; no key exists |
| Key recovered from a **challenge with a known answer** rather than the real target | tests the tool, not the target |

**Re-encryption is mandatory.** Without it, the output is an unverified guess.

---

## 14. REMEDIATION REFERENCE

*Classical ciphers appear in modern systems as obfuscation, in CTF/puzzle contexts, and in legacy
code. The remediation below is framed for the case where a classical construction is actually used
to protect something.*

1. **Do not use classical ciphers for confidentiality** — substitution, Vigenère, transposition, and single-byte XOR provide no meaningful security against a motivated analyst; they are puzzles, not protection. Replace the mechanism.
2. **Replace XOR "encryption" with authenticated encryption** — a repeating XOR key is recoverable from ciphertext alone via known-plaintext, crib-dragging, or key-length analysis; use AES-GCM or ChaCha20-Poly1305, and never reuse a keystream.
3. **Never reuse a key across messages without a nonce/IV** — the same Vigenère key or XOR key across multiple ciphertexts enables key recovery by statistical and algebraic combination; uniqueness per message is the essential property.
4. **Do not rely on obscurity of the algorithm** — classical strength often rests on the attacker not knowing the scheme; assume they do, and assume they hold a known-plaintext pair, which is the realistic case for web traffic.
5. **Introduce a proper key with sufficient entropy** — short keys (single-byte or short-word XOR, small Caesar shifts) are exhaustively enumerable; key length must make brute force infeasible, not merely inconvenient.
6. **Authenticate, do not just encrypt** — classical constructions give no integrity; an attacker can modify ciphertext undetectably. Use a MAC or AEAD so tampering is caught.
7. **Migrate legacy code that encodes data with these primitives** — audit for `XOR` loops, custom `substitution` tables, and `rot13` used as access control, and replace them with vetted library calls.
8. **Do not use classical ciphers to store secrets at rest** — data encrypted with a substitution or XOR scheme should be treated as plaintext on compromise; rotate every secret that passed through one.
9. **Keep key material in a KMS/HSM, not in code or config** — the common failure in legacy crypto is a hardcoded key; even a strong algorithm is defeated by a leaked key, and a test/backup copy is enough.
10. **Add a CI check for banned primitives** — fail builds that introduce `XOR`-as-encryption, `rot13`, or custom substitution helpers used in a security context, so these patterns cannot creep back in.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) · [hash-attack-techniques](../hash-attack-techniques/SKILL.md) — the modern-primitive counterparts
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) · [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) — public-key attacks for layered challenges
- [defi-attack-patterns](../defi-attack-patterns/SKILL.md) — protocol-level logic where weak crypto is sometimes the root cause
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) — hardcoded keys and legacy crypto recovered from repositories

---

---

## 16. EXECUTION PRIMITIVES — RECOVERY TOOLKIT

Classical cryptanalysis is proven by **recovering the plaintext and confirming it reads as the target's
content**. Every block ends at a decoded message, and every block begins with a calibration on a
plaintext you already know.

### 16.1 Calibration - the index of coincidence and the frequency baselines

```python
import collections, math, string

def ic(text):
    """Index of coincidence: ~0.0667 English monoalphabetic, ~0.038 random."""
    t = [c for c in text.upper() if c.isalpha()]
    n = len(t)
    if n < 2: return 0.0
    counts = collections.Counter(t)
    return sum(v * (v - 1) for v in counts.values()) / (n * (n - 1))

def chi2(text, freq):
    """Chi-squared against an expected frequency distribution."""
    t = [c for c in text.upper() if c.isalpha()]
    n = len(t); counts = collections.Counter(t)
    return sum((counts.get(c, 0) - freq.get(c, 0) * n) ** 2 / (freq.get(c, 0) * n)
               for c in string.ascii_uppercase if freq.get(c, 0) > 0)

ENGLISH = {c: v for c, v in zip(string.ascii_uppercase,
           [0.0817,0.0149,0.0278,0.0425,0.1270,0.0223,0.0202,0.0609,0.0697,0.0015,0.0077,0.0403,
            0.0241,0.0675,0.0751,0.0193,0.0009,0.0599,0.0633,0.0906,0.0276,0.0098,0.0236,0.0015,
            0.0197,0.0007])}

# CALIBRATION: the same measurements on text whose answer we know
known = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG " * 4
print("control IC (known English):", round(ic(known), 4), "   expected ~0.0667")
print("control IC (random letters):", round(ic("".join(__import__('random').choice(string.ascii_uppercase) for _ in range(200))), 4),
      "  expected ~0.038")
print("RULE: if the calibration does not separate, the text is too short - collect more ciphertext.")
```

**Calibrate the statistics before applying them.** A text under about 60 characters cannot be
distinguished from random by IC, and reporting a "Vigenere" solution on 40 characters is a guess.

### 16.2 Cipher identification, the ordered decision

```python
import collections, string

def identify(ct):
    """The ordered test. Each branch is falsifiable, and the order matters."""
    letters = [c for c in ct.upper() if c.isalpha()]
    symbols = [c for c in ct if not c.isalnum() and not c.isspace()]
    printable = all(32 <= ord(c) < 127 for c in ct)

    out = []
    if letters and len(letters) == len(ct.strip()):
        i = ic(letters)
        out.append(f"IC={i:.4f}")
        if i > 0.060:
            out.append("-> monoalphabetic (substitution, Caesar, affine)")
        elif i > 0.045:
            out.append("-> polyalphabetic OR transposition (check IC per period)")
        else:
            out.append("-> polyalphabetic with a long key, or a transposition of short blocks")
    if any(c in ct for c in "=+/") and printable:
        out.append("-> base64 or a similar encoding; decode first and re-test")
    if symbols and len(set(symbols)) < 10:
        out.append("-> a symbol substitution or a homophonic cipher")
    if len(ct) % 2 == 0 and ct.count(" ") and not letters:
        out.append("-> hex or a grouped numeric encoding")
    return out

print("\n".join(identify("WKLV LV D WHVW PHVVDJH")))
print()
print("RULE: try the cheapest test first. IC, then per-period IC, then word patterns, then frequency.")
print("State the identification evidence in the report - the reader must be able to re-derive it.")
```

**The ordered test is the technique.** A report that says "it is a Vigenere cipher" without the IC
figure and the period finding is an assertion.

### 16.3 Caesar and affine - brute force with a scoring function

```python
import string, collections

def score(text):
    """Quadgram-free approximation: sum of English letter frequencies, minus a rare-letter penalty."""
    t = [c.upper() for c in text if c.isalpha()]
    if not t: return -1e9
    return sum(ENGLISH.get(c, -0.05) for c in t) / len(t)

def caesar_bruteforce(ct):
    results = []
    for k in range(26):
        pt = "".join(chr((ord(c.upper()) - 65 - k) % 26 + 65) if c.isalpha() else c for c in ct)
        results.append((score(pt), k, pt))
    results.sort(reverse=True)
    return results

def affine_bruteforce(ct):
    inv = lambda a: next(x for x in range(26) if (a * x) % 26 == 1)
    results = []
    for a in [1,3,5,7,9,11,15,17,19,21,23,25]:
        for b in range(26):
            pt = "".join(chr((inv(a) * (ord(c.upper()) - 65 - b)) % 26 + 65) if c.isalpha() else c for c in ct)
            results.append((score(pt), a, b, pt))
    results.sort(reverse=True)
    return results

# CALIBRATION: encrypt a known sentence and confirm the top-scoring candidate is the original
KNOWN = "ATTACK AT DAWN ON THE EASTERN RIDGE"
enc = "".join(chr((ord(c) - 65 + 7) % 26 + 65) if c.isalpha() else c for c in KNOWN)
top = caesar_bruteforce(enc)[0]
print("calibration plaintext recovered:", top[2] == KNOWN, "| shift", top[1])
print()
print("CONTROL: the top candidate's score must exceed the runner-up's by a visible margin.")
print("If the top five scores are within 1%, the message is too short for frequency scoring.")
for s, k, pt in caesar_bruteforce(enc)[:3]:
    print(f"  shift={k:2d} score={s:.4f} {pt[:40]}")
```

**The calibration recovers a sentence you encrypted yourself.** Only then is the top-ranked candidate
on the target worth reporting.

### 16.4 Vigenere - period recovery, then key recovery

```python
import collections, string

def kasiski(ct, minlen=3):
    """Repeated sequences and their spacing - the factors of the spacings suggest the period."""
    ct = "".join(c for c in ct.upper() if c.isalpha())
    seen = {}
    for L in range(minlen, 6):
        for i in range(len(ct) - L):
            seq = ct[i:i+L]
            seen.setdefault(seq, []).append(i)
    gaps = collections.Counter()
    for seq, pos in seen.items():
        for a, b in zip(pos, pos[1:]):
            d = b - a
            for f in range(2, 21):
                if d % f == 0: gaps[f] += 1
    return gaps.most_common(8)

def ic_by_period(ct, period):
    ct = "".join(c for c in ct.upper() if c.isalpha())
    cols = [ct[i::period] for i in range(period)]
    return sum(ic(c) for c in cols) / period

def best_period(ct, lo=1, hi=20):
    scores = [(ic_by_period(ct, p), p) for p in range(lo, hi + 1)]
    return sorted(scores, reverse=True)

def vigenere_recover(ct, period):
    ct = "".join(c for c in ct.upper() if c.isalpha())
    key = ""
    for i in range(period):
        col = ct[i::period]
        best = max(range(26), key=lambda k: score("".join(
            chr((ord(c) - 65 - k) % 26 + 65) for c in col)))
        key += chr(best + 65)
    return key

# CALIBRATION
KNOWN = ("THE VIGENERE CIPHER IS A POLYALPHABETIC SUBSTITUTION THAT RESISTS FREQUENCY ANALYSIS "
         "BECAUSE THE SAME PLAINTEXT LETTER MAPS TO DIFFERENT CIPHERTEXT LETTERS") * 3
KEY = "SECRET"
enc = "".join(chr((ord(p) - 65 + ord(KEY[i % len(KEY)]) - 65) % 26 + 65)
              if p.isalpha() else p for i, p in enumerate(KNOWN))
print("calibration: best periods", [ (round(s,4), p) for s, p in best_period(enc)[:4] ])
print("calibration: recovered key   ", vigenere_recover(enc, len(KEY)), " expected", KEY)
print()
print("CONTROL: at the WRONG period the per-column IC stays near 0.038 (random).")
for p in [1, 3, len(KEY), len(KEY)+1, 12]:
    print(f"  period {p:2d}  mean-column IC {ic_by_period(enc, p):.4f}")
```

**The period must be confirmed by the IC rising to about 0.066 in each column.** A Kasiski coincidence
alone produces a wrong period and a recovered key that decrypts to gibberish - check the columns.

### 16.5 Transposition - anagramming and the column search

```python
def columnar_decrypt(ct, key_order):
    """Split into columns by the key order, then read row-wise."""
    n = len(ct); cols = len(key_order); rows = n // cols
    table = ["" for _ in range(cols)]
    idx = 0
    for pos in sorted(key_order):
        table[pos] = ct[idx:idx+rows]; idx += rows
    return "".join("".join(table[c][r] for c in range(cols)) for r in range(rows))

def try_periods(ct, hi=12):
    out = []
    for cols in range(2, hi + 1):
        d = columnar_decrypt(ct, list(range(cols)))
        out.append((score(d), cols, d))
    return sorted(out, reverse=True)

# CALIBRATION with a known plaintext, then the control that random permutations score badly
KNOWN = "THIS MESSAGE WAS TRANSPOSED BY REFLECTION AT NINE OCLOCK" * 2
print("calibration control: the correct column count must score above every wrong one.")
print("and the anagramming pass must improve the score monotonically, or the period is wrong.")
```

**A transposition solution must read as language.** The score is the check: a correct solution scores
near English letter frequency, and a wrong column count does not.

### 16.6 XOR and single-byte keys, with the key-reuse test

```python
def xor_single_bruteforce(ct):
    out = []
    for k in range(256):
        pt = bytes(b ^ k for b in ct)
        try: s = score(pt.decode("latin-1"))
        except Exception: s = -1e9
        # printable ratio is a second, independent signal
        pr = sum(32 <= b < 127 for b in pt) / max(1, len(pt))
        out.append((s + pr, k, pt))
    return sorted(out, reverse=True)

def detect_key_reuse(c1, c2):
    """Two ciphertexts under the same keystream: XOR them and the result is a plaintext XOR."""
    x = bytes(a ^ b for a, b in zip(c1, c2))
    return x, sum(32 <= b < 127 for b in x) / max(1, len(x))

# CALIBRATION
KNOWN = b"THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
enc = bytes(b ^ 0x42 for b in KNOWN)
s, k, pt = xor_single_bruteforce(enc)[0]
print("calibration key recovered:", hex(k), "| plaintext correct:", pt == KNOWN)
print()
print("CONTROL: with a random keystream the printable ratio collapses; with a reused key it stays high.")
print("A ratio near 1.0 for the XOR of two ciphertexts is the key-reuse finding.")
```

**Key reuse is proven by the printable ratio of the XOR.** Two ciphertexts under the same keystream XOR
to a plaintext XOR, which is overwhelmingly printable; independent keys give noise.

### 16.7 The end-to-end workflow

```bash
python3 - <<'PY'
print("STEP 0 - collect enough ciphertext. Under ~60 characters, IC cannot distinguish; stop.")
print()
print("STEP 1 - CALIBRATE the statistics on text whose answer is known (IC 0.066 vs 0.038).")
print()
print("STEP 2 - IDENTIFY the family with the ordered test, and RECORD the evidence for each branch")
print("     IC, per-period IC, symbol set, encoding test, word patterns")
print()
print("STEP 3 - APPLY the family attack, sweeping the single unknown (shift, period, key byte)")
print()
print("STEP 4 - VERIFY: the recovered plaintext must read as the target's content, and the")
print("     re-encryption with the recovered key must reproduce the ciphertext exactly")
print()
print("STEP 5 - CONTROL: the wrong shift / wrong period / wrong key byte must score measurably worse")
print()
print("STEP 6 - REPORT: the cipher identified, the recovered key, the plaintext (redacted as needed),")
print("     the re-encryption round trip, and the calibration figures")
PY
```

**The re-encryption round trip is the verification.** A classical recovery that does not re-encrypt to
the observed ciphertext is a plausible-looking string, not a solution.

---

## 17. EVIDENCE STANDARD — CLASSICAL RECOVERY

| Item | Why |
|---|---|
| The **ciphertext and its source** | reproducibility |
| The **calibration figures** (IC on known English and on random) | the statistics are meaningful at this length |
| The **identification evidence** for each branch of the ordered test | the family choice is justified |
| The **single unknown swept** (shift, period, key byte) and its resolution | the attack is complete |
| The **re-encryption round trip** to the observed ciphertext | the recovery is exact |
| The **score separation** between the answer and the runner-up | it is not a coin flip |
| The **recovered key**, where the cipher is keyed | the mechanism, and the severity |
| The **plaintext as readable content** | impact |
| The **control** on the wrong parameter | proves the identification |
| Whether the target is a **production system with a real secret** | a CTF exercise is not a finding |

Report the **recovery and the round trip**: "the target's session cookie decodes to a 96-character
alphabetic string; its index of coincidence is 0.0412 (random is 0.038, English monoalphabetic is
0.0667, calibrated on control texts of the same length), and the mean per-column IC peaks at period 6
where it rises to 0.0712 - the other periods stay below 0.045. Column-wise frequency analysis recovered
the key `SECRET`, and decrypting gives `user=alice&exp=1735689600&admin=false`. Re-encrypting that
plaintext with the recovered key reproduces the observed cookie exactly, so the identification is
confirmed", never "the cookie uses a weak cipher".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A "solution" on **fewer than ~60 characters** | IC cannot distinguish at that length |
| A recovered plaintext that does **not re-encrypt** to the ciphertext | a plausible string, not a solution |
| A top-scoring candidate **within noise of the runner-up** | not a recovery |
| A Kasiski period with **no per-column IC confirmation** | a repetition coincidence |
| An "obfuscated" value that is **only base64-encoded** | an encoding, not a cipher - decode and re-test |
| A classical cipher **in your own test fixture** | tests your own environment |
| A trivially-readable ROT13 in a **training exercise** | not a production finding |
| A key recovered where the **plaintext was already known** | the tool working, nothing recovered |
| A "weak cipher" claim with **no key or plaintext recovered** | an assertion |
| The plaintext reproduced in full where a redacted excerpt suffices | a disclosure |
| A cipher used for **non-security purposes** (a puzzle, a game identifier) | not a finding |

**Recover it and re-encrypt it, or it is a guess.** Classical cryptanalysis write-ups fail on exactly
this point, and the round trip is the one check that catches every false solution.

---

## 18. REMEDIATION REFERENCE — CIPHER HARDENING

1. **Replace any classical cipher in a security role with a modern AEAD construction (AES-GCM, ChaCha20-Poly1305)** - these ciphers are broken by inspection and were never meant for confidential data.
2. **Never use a substitution or transposition cipher to obfuscate a security token, an identifier, or a licence key** - it is obfuscation, not protection, and it is recoverable in minutes.
3. **Use a CSPRNG for every key, and a key of at least 128 bits** - the short keys in this document are recoverable by the statistics above.
4. **Never encrypt without authentication; use AEAD so a modified ciphertext is rejected** - classical ciphers have no integrity and every bit flip is an attacker-controlled plaintext change.
5. **Use a per-message random nonce and never reuse a keystream** - the XOR key-reuse attack is a direct consequence of reuse and it is a one-line design fix.
6. **Avoid home-made encodings for anything a user can observe, and treat any reversible encoding as public** - base64, ROT13, and custom alphabets are all recoverable without a key.
7. **Apply the real control on the server, never in a client-side encoded value** - an encoded `admin=false` is not an access control, and this document shows why.
8. **Rotate any key that has been used in a classical construction, and invalidate the artefacts produced with it** - the recovery is permanent.
9. **Use a vetted library for all cryptography, and remove custom cipher code from the codebase entirely** - the classes in this document exist only where bespoke cryptography was written.
10. **Educate developers on the difference between encoding, obfuscation, and encryption** - most findings in this document come from that distinction being blurred in a design.
11. **Test any token or identifier you ship by attempting exactly the analyses in this document** - it is a thirty-minute exercise and it catches the whole class before release.

---

## 19. RELATED SIBLINGS — ANALYSIS CROSS-REFERENCE

- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) - the modern block-cipher attacks that replaced these, with the same verification discipline
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) - the frequency and known-plaintext discipline applied to digests and MACs
- [rsa-attack-techniques](../rsa-attack-techniques/SKILL.md) - the asymmetric side of the same recovery-and-verify pattern
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) - the statistical-recovery mindset taken to its mathematical limit
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - where an obfuscated rather than signed token shows up in practice

---

## 20. EXECUTION PRIMITIVES — CONTROLLED RECOVERY

Classical cipher work is proven by **a recovered plaintext whose key was derived from the ciphertext
alone, with an unrelated-cipher control that fails the same test**. A "looks like English" judgement on a
short string is not a recovery.

### 20.1 The identification gate, with a negative control

```python
# identify the cipher BEFORE attempting a key. The control is a KNOWN PLAINTEXT you encrypt
# yourself: if the identifier cannot name the cipher it produced, it cannot name the target's.
import re, collections, string, math

def ic(t):
    """Index of coincidence. ~0.0667 English, ~0.038 random. A real discriminator, not a guess."""
    t = re.sub(r'[^A-Za-z]', '', t).upper()
    if len(t) < 2: return 0.0
    n = len(t); f = collections.Counter(t)
    return sum(v * (v - 1) for v in f.values()) / (n * (n - 1))

def freq(t):
    t = re.sub(r'[^A-Za-z]', '', t).upper()
    return collections.Counter(t)

def ctrl():
    """NEGATIVE CONTROL: encrypt a known sentence and see whether the identifiers fire correctly."""
    import random
    pt = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG AND THEN THE DOG SLEEPS ALL AFTERNOON IN THE SUN"
    # 1) monoalphabetic: IC stays English-like
    k = "QWERTYUIOPASDFGHJKLZXCVBNM"
    mono = pt.translate(str.maketrans(string.ascii_uppercase, k))
    # 2) vigenere: IC drops toward random
    key = "LEMON"
    vig = "".join(chr((ord(c) - 65 + ord(key[i % len(key)]) - 65) % 26 + 65)
                  for i, c in enumerate(pt))
    # 3) transposition: IC stays English, frequency stays English
    import math as _m
    cols = 8; rows = _m.ceil(len(pt) / cols)
    grid = [pt[i*cols:(i+1)*cols].ljust(cols) for i in range(rows)]
    trans = "".join(grid[r][c] for c in range(cols) for r in range(rows)).replace(" ", "")
    return {"known-plaintext": pt, "monoalphabetic": mono, "vigenere": vig, "transposition": trans}

print("%-18s %-9s %s" % ("control case", "IC", "what the IC means"))
for name, ct in ctrl().items():
    v = ic(ct)
    meaning = ("English-like -> monoalphabetic or transposition" if v > 0.060 else
               "random-like  -> polyalphabetic or XOR" if v < 0.045 else "ambiguous - get more text")
    print("%-18s %-9.4f %s" % (name, v, meaning))

def identify(ct):
    v = ic(ct); f = freq(ct); L = re.sub(r'[^A-Za-z]', '', ct)
    print()
    print("target IC: %.4f  length: %d" % (v, len(L)))
    print("top letters:", f.most_common(6))
    if v > 0.060:
        print("-> monoalphabetic substitution OR transposition. Distinguish by frequency:")
        print("   a shifted but ordered frequency profile -> Caesar/affine")
        print("   a scrambled frequency profile          -> general substitution")
        print("   an intact profile but scrambled words   -> transposition")
    elif v < 0.045:
        print("-> polyalphabetic or XOR. Estimate the key length via Kasiski or the IC-by-shift,")
        print("   then split into columns and solve each as a Caesar.")
    else:
        print("-> AMBIGUOUS. This is the most common false lead: with under ~100 letters the IC")
        print("   cannot separate these families. Get more ciphertext before naming the cipher.")
    return v

# the CONTROL test that matters: identify() must name the cipher of a KNOWN case correctly
for name, ct in ctrl().items():
    if name == "known-plaintext": continue
    print("### control:", name)
    identify(ct)
```

**The control is a ciphertext whose answer you already know.** If the identifier cannot name the cipher it
produced itself, any claim about the target is unfounded, and the short-text ambiguity is the most common
false lead in this family.

### 20.2 Frequency analysis, with a random-text control

```python
# the standard scoring functions, plus the control that proves the score discriminates
import re, string, collections, math

EN = {"E":12.70,"T":9.06,"A":8.17,"O":7.51,"I":6.97,"N":6.75,"S":6.33,"H":6.09,"R":5.99,"D":4.25,
      "L":4.03,"C":2.78,"U":2.76,"M":2.41,"W":2.36,"F":2.23,"G":2.02,"Y":1.97,"P":1.93,"B":1.29,
      "V":0.98,"K":0.77,"J":0.15,"X":0.15,"Q":0.10,"Z":0.07}

def chi2(t):
    """Chi-squared against English. LOWER is more English-like. The workhorse scorer."""
    t = re.sub(r'[^A-Za-z]', '', t).upper(); n = len(t)
    if n < 2: return 1e9
    obs = collections.Counter(t)
    return sum((obs.get(c, 0) - EN[c] * n / 100) ** 2 / (EN[c] * n / 100) for c in string.ascii_uppercase)

def bigram(t):
    """A coarse bigram score. Useful when chi2 is close between two candidates."""
    GOOD = {"TH","HE","IN","ER","AN","RE","ON","AT","EN","ND","TI","ES","OR","TE","OF","ED","IS","IT",
            "AL","AR","ST","TO","NT","NG","SE","HA","AS","OU","IO","LE","VE","CO","ME","DE","HI","RI"}
    t = re.sub(r'[^A-Za-z]', '', t).upper()
    return sum(1 for i in range(len(t) - 1) if t[i:i+2] in GOOD) / max(1, len(t) - 1)

def ctrl_scores():
    """CONTROL: English, random letters, and a Caesar of English. The scorer must ORDER them."""
    import random
    random.seed(0)
    eng = ("THE COMMITTEE MET AT DAWN AND THE MEMBERS AGREED THAT THE PROPOSAL SHOULD BE "
           "CONSIDERED AT THE NEXT MEETING OF THE ASSEMBLY IN THE GREAT HALL")
    rnd = "".join(random.choice(string.ascii_uppercase) for _ in range(len(eng)))
    caesar = "".join(chr((ord(c) - 65 + 13) % 26 + 65) if c.isalpha() else c for c in eng.upper())
    return {"English": eng, "random": rnd, "Caesar(English)": caesar}

print("%-18s %-12s %-10s %s" % ("control case", "chi2", "bigram", "expected order"))
rows = {k: (chi2(v), bigram(v)) for k, v in ctrl_scores().items()}
for k, (c, b) in rows.items():
    print("%-18s %-12.1f %-10.4f" % (k, c, b))
print()
print("CHECK: 'English' and 'Caesar(English)' must score FAR better than 'random'.")
print("       if 'random' scores as well as English, the scorer does not discriminate and the")
print("       analysis below is worthless - extend the sample or change the scorer.")
print()
print("CAESAR BRUTE FORCE with the scorer, which is the canonical application:")
for s in range(26):
    dec = "".join(chr((ord(c) - 65 - s) % 26 + 65) if c.isalpha() else c
                  for c in "GUR PENML XRL VF ZL ZRFFNTR".upper())
    print("  shift %2d chi2=%8.1f  %.50s" % (s, chi2(dec), dec))
print("  -> the minimum chi2 is the candidate; confirm it reads as the language before reporting")
```

**The random-text control is what makes the score meaningful.** A scorer that rates random letters as
highly as English has no discriminating power, and every recovery built on it is unfounded.

### 20.3 Monoalphabetic solving, with the convergence check

```python
# a hill-climbing solver must CONVERGE from several random starts before its answer is trusted
import random, string, re
random.seed(1)

def decrypt(ct, key):
    return ct.translate(str.maketrans(string.ascii_uppercase + string.ascii_lowercase,
                                      key.upper() + key.lower()))

def score(t):
    return -chi2(t)     # higher is better

def hillclimb(ct, iters=8000, restarts=5):
    """Return the best key AND the spread across restarts. A wide spread means do not trust it."""
    results = []
    for r in range(restarts):
        key = list(string.ascii_uppercase); random.shuffle(key); key = "".join(key)
        best = score(decrypt(ct, key))
        for _ in range(iters):
            i, j = random.sample(range(26), 2)
            k2 = list(key); k2[i], k2[j] = k2[j], k2[i]; k2 = "".join(k2)
            s2 = score(decrypt(ct, k2))
            if s2 > best: best, key = s2, k2
        results.append((best, key))
    results.sort(reverse=True)
    return results

CT = re.sub(r'[^A-Za-z]', '', "SAMPLE CIPHERTEXT HERE").upper()
if len(CT) < 60:
    print("REFUSING: under 60 letters, the solver's answer is noise. Get more ciphertext.")
else:
    res = hillclimb(CT)
    print("%-10s %s" % ("score", "key prefix"))
    for s, k in res: print("%-10.1f %s" % (s, k[:12]))
    spread = res[0][0] - res[-1][0]
    print()
    print("top key   :", res[0][1])
    print("plaintext :", decrypt(CT, res[0][1])[:120])
    print("spread    :", round(spread, 1))
    print()
    print("CONVERGENCE RULE: if three or more independent restarts produce the SAME key, the")
    print("recovery is reliable. If the restarts disagree, the ciphertext is too short, the")
    print("cipher is not monoalphabetic, or the sample is contaminated. Say which, do not guess.")
```

**Convergence across restarts is the reliability test.** One lucky hill-climb is not a recovery, and the
spread is what tells you whether to trust it.

### 20.4 The Vigenere key-length derivation, with the control

```python
# the key length is derived from the ciphertext, and the control is a known-length encryption
import re, collections, string

def ic_by_shift(t, shift):
    col = t[shift::1]
    return ic(col)

def kasiski(t, minlen=3, maxlen=12):
    """Repeated sequences and their spacing GCDs - the classical key-length signal."""
    t = re.sub(r'[^A-Za-z]', '', t).upper()
    gaps = collections.defaultdict(list)
    for L in range(minlen, maxlen + 1):
        seen = {}
        for i in range(len(t) - L):
            g = t[i:i+L]
            if g in seen: gaps[g].append(i - seen[g])
            seen[g] = i
    from math import gcd
    from functools import reduce
    out = collections.Counter()
    for g, ds in gaps.items():
        for d in ds:
            for k in range(2, 21):
                if d % k == 0: out[k] += 1
    return out

def ic_columns(t, keylen):
    """Average IC of the columns at a candidate key length. English columns -> IC ~= 0.066."""
    t = re.sub(r'[^A-Za-z]', '', t).upper()
    return sum(ic(t[i::keylen]) for i in range(keylen)) / keylen

def ctrl_keylen():
    """CONTROL: encrypt a known text with a KNOWN key length and see whether the method finds it."""
    import random
    random.seed(2)
    pt = ("THE ASSEMBLY MET AGAIN AND THE COMMITTEE REPORTED THAT THE PROPOSAL WOULD BE CONSIDERED "
          "AT THE NEXT MEETING WHERE THE MEMBERS WOULD VOTE ON THE MATTER OF THE NEW BUILDING") * 3
    klen = 6
    key = "SECRET"
    ct = "".join(chr((ord(c) - 65 + ord(key[i % klen]) - 65) % 26 + 65)
                 for i, c in enumerate(re.sub(r'[^A-Za-z]', '', pt).upper()))
    return ct, klen

ct, true_len = ctrl_keylen()
print("CONTROL key length is", true_len)
print()
print("kasiski GCD candidates:", kasiski(ct).most_common(6))
print()
print("%-8s %-10s %s" % ("keylen", "avg IC", "verdict"))
for k in range(1, 13):
    v = ic_columns(ct, k)
    print("%-8d %-10.4f %s" % (k, v, "SPIKE - likely a multiple of the key length" if v > 0.060 else ""))
print()
print("VERDICT RULE: the key length is the SMALLEST k with an IC spike, that also divides the")
print("other spikes. The kasiski GCDs must agree with it. If they do not agree, report the")
print("disagreement rather than picking one.")
print()
print("THE FALSE POSITIVE: every MULTIPLE of the true key length also spikes. Taking the largest")
print("spike instead of the smallest is the standard error in this family.")
```

**Every multiple of the true key length also spikes.** Taking the largest IC instead of the smallest is the
standard error, and the Kasiski GCDs must agree with the IC result.

### 20.5 The end-to-end harness

```bash
python3 - <<'PY'
import re, collections, string, math, random

def ic(t):
    t = re.sub(r'[^A-Za-z]', '', t).upper()
    n = len(t)
    if n < 2: return 0.0
    return sum(v*(v-1) for v in collections.Counter(t).values()) / (n*(n-1))

print("=== CLASSICAL RECOVERY ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the sample is long enough",
  "IC and frequency analysis need roughly 100+ letters; below that, the family cannot be named"),
 ("the cipher family is identified, not assumed",
  "IC and the frequency profile select the family, and an ambiguous result is stated as ambiguous"),
 ("a known-plaintext control was run",
  "you encrypted a test string with a known cipher and the identifier named it correctly"),
 ("a random-text control was run",
  "the scorer rates random letters far worse than English, or the scorer is not discriminating"),
 ("the key was derived from the ciphertext alone",
  "no crib, no known plaintext, and no external hint was used"),
 ("the solver converged",
  "three independent restarts produced the same key, or the disagreement is reported"),
 ("the plaintext reads as the language",
  "a human or a language model confirms it; a high score alone is not confirmation"),
 ("the recovered key re-encrypts to the original",
  "encrypting the recovered plaintext with the recovered key reproduces the ciphertext byte-for-byte"),
 ("the plaintext is significant",
  "a meaningful message, a flag, or a credential - not a plausible-looking string"),
 ("the method and parameters are recorded",
  "the family, the scorer, the key length, and the number of restarts"),
]
for n, how in CHECKS: print("  [ ] %-40s -> %s" % (n, how))
print()
print("=== THE ROUND-TRIP TEST, which every recovery must pass ===")
print("  encrypt(recovered_plaintext, recovered_key) == original_ciphertext")
print("  a recovery that fails this is a coincidence, whatever the language model says")
print()
print("=== THE CONTROL PAIR ===")
print("  take an UNRELATED ciphertext of the same length and run the SAME analysis.")
print("  the method will produce a key and a 'plaintext' for it too. If that output also looks")
print("  plausible, the method is producing noise, and the original result is not a finding.")
PY
```

**The round-trip test is what makes a recovery a recovery.** Re-encrypting the plaintext with the recovered
key must reproduce the ciphertext byte-for-byte, and the unrelated-cipher control must fail the same test.

---

## 21. RELATED SIBLINGS - REPORTING DISCIPLINE
1. **State the ciphertext length before anything else and refuse to name a cipher under roughly 100 letters** - the IC cannot separate the families below that, and the ambiguity is this family's most common false finding.
2. **Run a known-plaintext control by encrypting your own test string and confirming the identifier names it correctly** - an identifier that fails its own control cannot be used on the target.
3. **Run a random-letters control against every scorer and confirm random scores far worse than English** - a scorer without discriminating power makes every recovery built on it unfounded.
4. **Derive the key from the ciphertext alone, with no crib and no hint, and say so explicitly** - a hint-supplied key is not cryptanalysis.
5. **Require convergence from at least three independent random restarts before trusting a hill-climbed key, and report the spread** - a single lucky run is noise.
6. **Take the SMALLEST key length with an IC spike, cross-checked against the Kasiski GCDs, and report any disagreement** - every multiple of the true length also spikes, which is the standard error here.
7. **Always perform the round-trip test: encrypting the recovered plaintext with the recovered key must reproduce the ciphertext exactly** - it is the only cheap check that separates a recovery from a coincidence.
8. **Run the whole method against an unrelated ciphertext of the same length as the negative control** - if it also yields a plausible "plaintext", the method is generating noise.
9. **Require the recovered plaintext to be significant, not merely plausible** - a flag, a credential, or a meaningful message; "it looks like English" is the weakest possible claim.
10. **Use a language model as a confirmation aid, never as the proof** - it will find English in noise, and the score plus the round trip are the evidence.
11. **Record the family, the scorer, the key length, the restarts, and the round-trip result together** - a reader must be able to reproduce the exact recovery, not merely read its conclusion.

---

## 22. RELATED SIBLINGS - CONTROLLED RECOVERY REFERENCES

- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) - the sibling classical-to-modern family
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) - the modern block-cipher counterpart
- [steganography-techniques](../steganography-techniques/SKILL.md) - the carrier for an embedded ciphertext
- [ctf-no-preset-category](../attack-execution-atomic-tests/SKILL.md) - the CTF execution discipline this shares
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - recovering ciphertext from a capture
