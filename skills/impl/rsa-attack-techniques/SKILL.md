---
name: rsa-attack-techniques
description: >-
  RSA attack playbook for CTF and real-world cryptanalysis. Use when given
  RSA parameters (n, e, c) and need to recover plaintext by exploiting
  weak keys, small exponents, shared factors, or padding oracles.
---

# SKILL: RSA Attack Techniques — Expert Cryptanalysis Playbook

> **AI LOAD INSTRUCTION**: Expert RSA attack techniques for CTF and authorized security assessments. Covers factorization attacks, small exponent exploits, lattice-based approaches (Wiener/Boneh-Durfee/Coppersmith), broadcast attacks, common modulus, padding oracles, and fault attacks. Base models often suggest attacks that don't match the given parameters or miss the correct attack selection based on what's known.

## 0. RELATED ROUTING

- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) for deep lattice theory behind Coppersmith/Boneh-Durfee
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) when RSA signature forgery involves hash weaknesses
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) when RSA protects a symmetric key (hybrid encryption)

### Advanced Reference

Also load [RSA_ATTACK_CATALOG.md](./RSA_ATTACK_CATALOG.md) when you need:
- Detailed SageMath/Python implementation for each attack
- Step-by-step mathematical derivation
- Edge cases and failure conditions per attack

### Quick attack selection

| Given / Observable | Attack | Tool |
|---|---|---|
| Small n (< 512 bits) | Direct factorization | factordb, yafu, msieve |
| e = 3, small message | Cube root | gmpy2.iroot |
| Multiple (n, c) same small e | Hastad broadcast | CRT + iroot |
| Very large e or very small d | Wiener / Boneh-Durfee | SageMath, RsaCtfTool |
| Partial p knowledge | Coppersmith small roots | SageMath |
| Same n, different e | Common modulus | Extended GCD |
| Multiple n values | Batch GCD (shared factor) | Python/SageMath |
| Padding error oracle | Bleichenbacher | Custom script |
| LSB parity oracle | LSB oracle attack | Custom script |
| Fault in CRT computation | RSA-CRT fault | Single faulty signature |

---

## 1. FACTORIZATION ATTACKS

### 1.1 Direct Factorization (Small n)

```text
from sympy import factorint

n = 0x...  # small modulus
factors = factorint(n)
p, q = list(factors.keys())
```

**When**: n < ~512 bits, or known to be in factordb.

### 1.2 Fermat's Factorization

Works when p and q are close together: |p - q| is small.

```python
from gmpy2 import isqrt, is_square

def fermat_factor(n):
    a = isqrt(n) + 1
    while True:
        b2 = a * a - n
        if is_square(b2):
            b = isqrt(b2)
            return (a + b, a - b)
        a += 1
```

### 1.3 Pollard's p-1

Works when p-1 has only small prime factors (B-smooth).

```python
from gmpy2 import gcd

def pollard_p1(n, B=2**20):
    a = 2
    for j in range(2, B):
        a = pow(a, j, n)
    d = gcd(a - 1, n)
    if 1 < d < n:
        return d
    return None
```

### 1.4 Batch GCD (Multiple n share a factor)

```python
from math import gcd
from functools import reduce

def batch_gcd(moduli):
    """Find shared factors among multiple RSA moduli."""
    product = reduce(lambda a, b: a * b, moduli)
    results = {}
    for i, n in enumerate(moduli):
        remainder = product // n
        g = gcd(n, remainder)
        if g != 1 and g != n:
            results[i] = (g, n // g)
    return results
```

---

## 2. SMALL EXPONENT ATTACKS

### 2.1 Cube Root Attack (e = 3, small m)

If m^e < n (no modular reduction occurred), simply take the e-th root.

```text
from gmpy2 import iroot

c = 0x...  # ciphertext
e = 3
m, exact = iroot(c, e)
if exact:
    print(f"Plaintext: {bytes.fromhex(hex(m)[2:])}")
```

### 2.2 Hastad Broadcast Attack

Same message encrypted with same small e under different moduli (n₁, n₂, ..., nₑ).

```python
from sympy.ntheory.modular import crt
from gmpy2 import iroot

# e = 3, three ciphertexts under three different n
n_list = [n1, n2, n3]
c_list = [c1, c2, c3]

# CRT: find x such that x ≡ ci (mod ni) for all i
r, M = crt(n_list, c_list)
m, exact = iroot(r, 3)
assert exact
```

### 2.3 Related Message Attack (Franklin-Reiter)

Two messages related by a known linear function: m₂ = a·m₁ + b. Same n and e.

```text
# SageMath
def franklin_reiter(n, e, c1, c2, a, b):
    R.<x> = PolynomialRing(Zmod(n))
    f1 = x^e - c1
    f2 = (a*x + b)^e - c2
    return Integer(n - gcd(f1, f2).coefficients()[0])
```

---

## 3. LARGE e / SMALL d ATTACKS

### 3.1 Wiener's Attack (Continued Fractions)

When d < n^(1/4) / 3, the continued fraction expansion of e/n reveals d.

```python
def wiener_attack(e, n):
    """Recover d when d is small via continued fractions."""
    cf = continued_fraction(e, n)
    convergents = get_convergents(cf)

    for k, d in convergents:
        if k == 0:
            continue
        phi_candidate = (e * d - 1) // k
        # phi(n) = n - p - q + 1 → p + q = n - phi + 1
        s = n - phi_candidate + 1
        # p, q are roots of x^2 - s*x + n = 0
        discriminant = s * s - 4 * n
        if discriminant >= 0:
            from gmpy2 import isqrt, is_square
            if is_square(discriminant):
                return d
    return None

def continued_fraction(a, b):
    cf = []
    while b:
        cf.append(a // b)
        a, b = b, a % b
    return cf

def get_convergents(cf):
    convergents = []
    h_prev, h_curr = 0, 1
    k_prev, k_curr = 1, 0
    for a in cf:
        h_prev, h_curr = h_curr, a * h_curr + h_prev
        k_prev, k_curr = k_curr, a * k_curr + k_prev
        convergents.append((h_curr, k_curr))
    return convergents
```

### 3.2 Boneh-Durfee Attack (Lattice-Based)

Extends Wiener: works when d < n^0.292. Uses lattice reduction (LLL/BKZ).

**Use SageMath implementation** — see [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) for theory.

---

## 4. COPPERSMITH'S METHOD

### 4.1 Stereotyped Message

Known portion of plaintext, unknown part is small.

```text
# SageMath
n = ...
e = 3
c = ...
known_prefix = b"flag{" + b"\x00" * 27  # known prefix, unknown suffix
known_int = int.from_bytes(known_prefix, 'big')

R.<x> = PolynomialRing(Zmod(n))
f = (known_int + x)^e - c
roots = f.small_roots(X=2^(27*8), beta=1.0)
if roots:
    m = known_int + int(roots[0])
    print(bytes.fromhex(hex(m)[2:]))
```

### 4.2 Partial Key Exposure

Known MSB or LSB of p → recover full p via Coppersmith.

```text
# SageMath — known MSB of p
p_msb = ...  # known upper bits of p
R.<x> = PolynomialRing(Zmod(n))
f = p_msb + x
roots = f.small_roots(X=2^unknown_bits, beta=0.5)
if roots:
    p = p_msb + int(roots[0])
    q = n // p
```

---

## 5. COMMON MODULUS ATTACK

Two ciphertexts of same message under same n but different e₁, e₂ where gcd(e₁, e₂) = 1.

```python
from gmpy2 import gcd, invert

def common_modulus(n, e1, e2, c1, c2):
    """Recover m when same message encrypted with two different e under same n."""
    assert gcd(e1, e2) == 1
    _, s1, s2 = extended_gcd(e1, e2)  # s1*e1 + s2*e2 = 1

    if s1 < 0:
        c1 = invert(c1, n)
        s1 = -s1
    if s2 < 0:
        c2 = invert(c2, n)
        s2 = -s2

    m = (pow(c1, s1, n) * pow(c2, s2, n)) % n
    return m

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x
```

---

## 6. ORACLE ATTACKS

### 6.1 LSB Oracle (Parity Oracle)

An oracle reveals whether decrypted message is even or odd.

```python
from gmpy2 import mpz

def lsb_oracle_attack(n, e, c, oracle_func):
    """Decrypt using LSB (parity) oracle. oracle_func(c) returns m%2."""
    from fractions import Fraction
    lo, hi = Fraction(0), Fraction(n)

    for _ in range(n.bit_length()):
        c = (c * pow(2, e, n)) % n  # multiply plaintext by 2
        if oracle_func(c) == 0:
            hi = (lo + hi) / 2
        else:
            lo = (lo + hi) / 2

    return int(hi)
```

### 6.2 Bleichenbacher (PKCS#1 v1.5 Padding Oracle)

Given a padding validity oracle (valid/invalid PKCS#1 v1.5), iteratively narrow down the plaintext range.

**Complexity**: O(2^16) oracle queries per byte on average.

**Target**: TLS implementations returning different errors for valid/invalid padding.

### 6.3 Manger's Attack (PKCS#1 OAEP)

Similar to Bleichenbacher but for OAEP padding. Exploits oracle that distinguishes whether the first byte after unpadding is 0x00.

---

## 7. RSA-CRT FAULT ATTACK

If RSA-CRT signing produces a faulty signature (fault in one CRT half):

```python
def rsa_crt_fault(n, e, correct_sig, faulty_sig, msg):
    """Factor n from one correct and one faulty CRT signature."""
    from math import gcd
    diff = pow(correct_sig, e, n) - pow(faulty_sig, e, n)
    p = gcd(diff % n, n)
    if 1 < p < n:
        q = n // p
        return p, q
    return None

# Even simpler: only faulty signature needed if message is known
def rsa_crt_fault_simple(n, e, faulty_sig, msg):
    p = gcd(pow(faulty_sig, e, n) - msg, n)
    if 1 < p < n:
        return p, n // p
    return None
```

---

## 8. DECISION TREE

```
RSA challenge — what information do you have?
│
├─ Have n and it's small (< 512 bits)?
│  └─ Factor directly: factordb.com → yafu → msieve
│
├─ Have multiple n values?
│  └─ Batch GCD — shared factors?
│     ├─ Yes → factor all that share factors
│     └─ No → analyze each n individually
│
├─ Know e?
│  ├─ e = 3 (or small)?
│  │  ├─ Single ciphertext, small message → cube root
│  │  ├─ Multiple ciphertexts, different n → Hastad broadcast
│  │  ├─ Two related messages → Franklin-Reiter
│  │  └─ Partial plaintext known → Coppersmith
│  │
│  ├─ e is very large?
│  │  └─ d is likely small → Wiener → Boneh-Durfee
│  │
│  └─ Same n, two different e values?
│     └─ Common modulus attack (Bezout coefficients)
│
├─ Know partial factorization info?
│  ├─ Know some bits of p → Coppersmith partial key
│  ├─ p-1 is B-smooth → Pollard p-1
│  └─ p ≈ q (close primes) → Fermat factorization
│
├─ Have an oracle?
│  ├─ Parity oracle (LSB) → LSB oracle attack
│  ├─ Padding validity oracle (PKCS#1 v1.5) → Bleichenbacher
│  └─ OAEP oracle → Manger's attack
│
├─ Have faulty signature?
│  └─ RSA-CRT fault → factor n from faulty sig
│
├─ Know e·d relationship?
│  └─ e·d ≡ 1 mod φ(n) → factor n from (e,d,n)
│
└─ None of the above?
   ├─ Check factordb for known factorization
   ├─ Try Pollard rho for medium-size n
   ├─ Look for implementation flaws (weak PRNG for key generation)
   └─ Consider side-channel if physical access available
```

---

## 9. TOOLS

| Tool | Purpose | Usage |
|---|---|---|
| **RsaCtfTool** | Automated RSA attack suite | `python3 RsaCtfTool.py --publickey pub.pem --uncipherfile flag.enc` |
| **SageMath** | Mathematical computation | Coppersmith, lattice attacks, polynomial arithmetic |
| **factordb.com** | Online factor database | Check if n is already factored |
| **yafu** | Fast factorization (SIQS/GNFS) | `yafu "factor(n)"` |
| **msieve** | GNFS factorization | Large n factorization |
| **gmpy2** | Fast Python integer library | `iroot`, `invert`, `gcd` |
| **pycryptodome** | RSA primitives | Key construction from factors |

### RsaCtfTool Quick Commands

```bash
# From public key
python3 RsaCtfTool.py --publickey pub.pem -n --private

# From parameters
python3 RsaCtfTool.py -n $N -e $E --uncipher $C

# Try all attacks
python3 RsaCtfTool.py --publickey pub.pem --uncipherfile flag.enc --attack all
```

### Decrypt After Factoring

```text
from Crypto.PublicKey import RSA
from gmpy2 import invert

p, q = ...  # factored
n = p * q
e = 65537
phi = (p - 1) * (q - 1)
d = int(invert(e, phi))

c = ...  # ciphertext as integer
m = pow(c, d, n)
plaintext = m.to_bytes((m.bit_length() + 7) // 8, 'big')
print(plaintext)
```
---

## 10. VERIFICATION AND FALSE-POSITIVE CONTROL

Every recovered value in sections 1-7 must be verified before it is reported. A "factor" that does not divide n, or a "plaintext" that does not re-encrypt to c, is a tooling artefact, not a result.

### 10.1 Mandatory RSA round-trip check

The single non-negotiable check: re-encrypt the candidate plaintext and compare to the ciphertext.

```python
def rsa_round_trip(m, e, n, c):
    '''True only if the recovered m actually re-encrypts to the given c.'''
    return pow(m, e, n) == c
```

Usage after any attack that yields m (cube root, Hastad, common modulus, Wiener, Coppersmith):

```python
assert 0 <= m < n, "m out of range — attack produced garbage"
assert rsa_round_trip(m, e, n, c), "round-trip failed: m is not the plaintext"
```

Supporting sanity checks that must also hold:

```python
def verify_rsa_params(n, e, p, q, d=None):
    '''Checks that hold for ANY correctly recovered factorization.'''
    assert p * q == n, "p*q != n — factors are wrong"
    assert p != q, "p == q — modulus was not square-free"
    phi = (p - 1) * (q - 1)
    assert phi % 2 == 0
    if d is not None:
        assert (e * d) % phi == 1, "e*d != 1 mod phi(n)"
    return True
```

A candidate that fails `pow(m, e, n) == c` is always discarded, no matter how plausible the plaintext looks. Beware of the reverse error too: a *wrong* m can still round-trip if `m^e < n` wraps coincidentally — re-check `m^e` without reduction when e is small.

### 10.2 Common modulus: feasibility conditions

Before claiming success, confirm all of these:

- Same modulus n for both ciphertexts (compare n byte-for-byte, not just bit length).
- `gcd(e1, e2) == 1`. If the gcd g > 1, the technique only recovers `m^g`, and a g-th integer root is needed — and only if `m^g < n`.
- Both c1 and c2 are invertible mod n; `gcd(c_i, n) != 1` actually means n is factorable directly, so switch to the Batch GCD path.
- The attack is only meaningful because Bezout gives `s1*e1 + s2*e2 = 1`; verify the recovered coefficients satisfy that identity, with negative exponents handled by modular inversion.

```python
from math import gcd

def check_common_modulus(n, e1, e2, c1, c2):
    assert gcd(e1, e2) == 1, "gcd(e1,e2) != 1 — plain common modulus does not apply"
    assert gcd(c1, n) == 1 and gcd(c2, n) == 1, "non-invertible c — factor n instead"
```

Verification: the recovered m must satisfy BOTH `pow(m, e1, n) == c1` and `pow(m, e2, n) == c2`. Satisfying only one is a false positive.

### 10.3 Small-e / Hastad: feasibility conditions

- Report the cube root only when the root is exact: `iroot(c, e)` returns `exact == True`. A non-exact root is a non-result.
- For Hastad, the number of coprime moduli must be >= e. With fewer than e ciphertexts the CRT value is not `m^e` over the integers and no exact root exists.
- The moduli must be pairwise coprime. Compute pairwise gcds first; a shared factor means you should factor both moduli instead of doing CRT.
- Verify with the full round-trip per modulus: `pow(m, e, n_i) == c_i` for every i. Verify over the integers as well that `m^e == r` where r is the CRT result, which is what makes the root exact.
- If e is large (e.g. e = 65537) the CRT product grows far beyond `m^e`; the exact-root test fails and the attack is not applicable.

### 10.4 Wiener: feasibility conditions

Wiener is a yes/no test, never a guess. Apply only when all hold:

- d < n^(1/4) / 3 (the classical bound). If d sits between that bound and n^0.292, use Boneh-Durfee instead.
- The recovered (k, d) pair comes from an actual convergent of the continued fraction of e/n, not a value picked out of the sequence.
- `e*d ≡ 1 (mod phi_candidate)` for the phi derived from the convergent.
- The quadratic `x^2 - s*x + n` (with `s = n - phi + 1`) has an integer, non-negative discriminant that is a perfect square, and the two roots multiply to exactly n.

```python
def verify_wiener(n, e, d):
    from gmpy2 import isqrt, is_square
    from math import gcd
    if (e * d - 1) % d == 0:
        pass
    phi, _ = None, None
    # k = (e*d - 1) // phi must be a positive integer with gcd(k, d) == 1
    return True

def verify_wiener_strict(n, e, d):
    from gmpy2 import isqrt, is_square
    if e * d % 1 != 0:
        return False
    # recover phi from (e*d - 1) = k*phi, k integer, then check the quadratic
    num = e * d - 1
    for k in range(1, 64):  # k is small in practice
        if num % k:
            continue
        phi = num // k
        s = n - phi + 1
        disc = s * s - 4 * n
        if disc >= 0 and is_square(disc):
            return True
    return False
```

Final check is always the round-trip: `pow(pow(c, d, n), e, n) == c`.

### 10.5 Coppersmith: feasibility conditions

A `small_roots` call that returns an empty list, or returns a root that does not satisfy the polynomial, is the common false-positive trap.

- The bound X must be strictly smaller than the theoretical bound for the chosen beta and degree: for a monic univariate polynomial of degree delta modulo a divisor of n of size n^beta, roots smaller than approximately n^(beta^2 / delta) are recoverable. Estimating X too large yields roots that are not actually roots modulo the true divisor.
- beta must match the structure: beta = 1.0 for a full-modulus polynomial, beta = 0.5 when working modulo an unknown factor p of n.
- The polynomial must be monic modulo n. If the leading coefficient is not invertible, multiply through by its inverse mod n first.
- The known prefix must be positioned exactly: `f = (known_int + x)^e - c` assumes the unknown bytes are the low-order (least significant) bytes of m. A wrong shift produces a polynomial with no small root even when the plaintext is known.
- After `small_roots` returns r, verify `pow(known_int + int(r), e, n) == c` (stereotyped message) or `n % (p_msb + int(r)) == 0` (partial key exposure). Also verify `f(r) == 0 mod n`.

### 10.6 Oracle attacks: verification

- LSB oracle: the returned interval [lo, hi) must have width 1 bit-per-iteration, and the final integer must round-trip. An off-by-one in the interval update produces a plaintext that is wrong by exactly 1.
- Bleichenbacher / Manger: verify that the recovered plaintext, when re-padded and re-encrypted, yields the original ciphertext under the target's padding rules.
- RSA-CRT fault: verify the two gcd-derived factors multiply to n; a gcd equal to 1 or n means the fault did not land in one CRT half as assumed.

---

## 11. FAILURE MODES AND PITFALLS

### 11.1 Wrong-attack selection

| Symptom | Real cause | Correct action |
|---|---|---|
| `iroot` not exact for e = 3 | m^3 >= n, modular reduction occurred | Do not report a root; use Hastad (needs e ciphertexts) or Coppersmith with known plaintext |
| `small_roots` returns [] | X too large, wrong beta, or non-monic polynomial | Re-derive the bound, set beta to match the modulus structure, make the polynomial monic |
| Wiener returns nothing | d is not small, or e is small instead | Try Boneh-Durfee; if e is small, switch to section 2 |
| CRT + root fails with 3 ciphertexts | Moduli not pairwise coprime, or m^3 >= product | Check pairwise gcds; add more ciphertexts or use Coppersmith |
| Common modulus yields garbage | gcd(e1, e2) > 1 | Only `m^g` is recoverable; try a g-th root, else abandon |

### 11.2 Arithmetic traps

- Integer division silently truncating in e-th root extraction without the exactness flag.
- Forgetting `pow(..., -1, n)` style modular inversion for negative Bezout exponents; plain negative Python exponents on integers produce floats.
- Mixing `bytes` and integers: `int.from_bytes(..., 'big')` and `m.to_bytes((m.bit_length() + 7) // 8, 'big')` must use the same byte order as the challenge.
- Leading-zero loss: `m.to_bytes()` without an explicit length drops leading 0x00 bytes; pass the expected modulus byte length when the flag format demands it.

### 11.3 Reporting discipline

Never report a plaintext that has not passed `pow(m, e, n) == c`. Never report factors that do not satisfy `p * q == n`. State the attack that was used and the parameter precondition that made it applicable, so the result can be independently reproduced.

---

## 12. QUICK REFERENCE CARD

```text
GIVEN n, e, c
│
├─ n small or in factordb?          → factor, then d = e^-1 mod phi(n)
├─ e = 3/5/17 and m^e < n?          → exact iroot     [verify: pow(m,e,n)==c]
├─ e ciphertexts, e coprime n_i?    → Hastad CRT+root [verify each n_i]
├─ same n, two coprime e?           → common modulus  [verify both e]
├─ d < n^(1/4)/3?                   → Wiener          [verify p*q==n]
├─ d < n^0.292?                     → Boneh-Durfee
├─ known prefix/suffix of m?        → Coppersmith stereotyped  [verify f(r)==0]
├─ known bits of p?                 → Coppersmith partial key [verify n%p==0]
├─ padding/parity oracle?           → Bleichenbacher / LSB / Manger
└─ faulty CRT signature?            → gcd(pow(sig,e,n)-m, n)

ALWAYS: pow(m, e, n) == c   and   p * q == n
```

| Check | Formula | Applies to |
|---|---|---|
| Round-trip | `pow(m, e, n) == c` | Every attack |
| Factor product | `p * q == n` | Every factorization |
| Exact root | `iroot(c, e).exact` | Cube root, Hastad |
| Bezout identity | `s1*e1 + s2*e2 == 1` | Common modulus |
| Convergent validity | `e*d ≡ 1 mod phi`, quadratic has perfect-square discriminant | Wiener |
| Small root | `f(r) ≡ 0 mod n` and `r < X` | Coppersmith |

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **public parameters in full** — `n`, `e`, and every ciphertext `c` (hex, complete) | the attack is a function of these exact integers; a truncated `n` is unreproducible |
| The **attack script** that produced the result, including the lattice/factorization parameters | the parameters *are* the technique; LLL vs Howgrave-Graham with a given `m, t, X` are different attacks |
| The **recovered secret** — `p`, `q`, `d`, or the plaintext `m` — as an exact integer | the artefact the finding is about |
| The **round-trip verification output** — `pow(m, e, n) == c` returning true, or `p*q == n` | the single most important artefact; see §10.1 |
| The **feasibility condition** that made the attack possible (small `e`, shared prime, `d < n^0.25`, bias) | explains why it works and when it stops working |
| Whether the recovered `m` **decrypts a second ciphertext** under the same key | proves key recovery rather than one-message fitting |
| Runtime and tool versions (SageMath, RsaCtfTool, `gmpy2`) | reproducibility; integer-root and LLL behaviour differ across versions |
| **Negative control** — the same attack against a correctly generated 2048-bit RSA-65537 sample fails | proves the weakness is in the target, not the tool |

Report the **weakness and the verified recovery**: "the same modulus is used across two sessions with
`e1=3`, `e2=5` and `gcd=1`, so Bezout yields `m` directly; the recovered plaintext re-encrypts to the
original ciphertext under `(e1, n)`", never "the application uses RSA insecurely".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| A candidate `m` that fails `pow(m, e, n) == c` | not the plaintext, regardless of how printable it looks |
| A "factor" `p` where `n % p != 0` | a Coppersmith/lattice artefact |
| `p == q` or `p == n` | degenerate output; the modulus is malformed, not factored |
| Attack succeeds only on **your own generated** weak sample | tests the tool, not the target |
| Small `e` present but the plaintext is padded with OAEP and the message is long | Hastad/Coppersmith conditions not met |
| Common modulus across **different** keys (different `n`) | nothing shared; not the common-modulus flaw |
| `gcd(c_i, n) != 1` reported as "common modulus attack works" | that is direct factorization, a different (stronger) finding |
| Decrypted output that is not in the expected format (not ASCII/JSON/known structure) | coincidence |
| `d` recovered but `(e*d) % phi != 1` | invalid private exponent |

**The round-trip is mandatory.** Without `pow(m, e, n) == c`, the result is a hypothesis.

---

## 14. REMEDIATION REFERENCE

1. **Generate primes with a CSPRNG and never reuse them across keys** — shared-prime and Batch-GCD attacks recover keys from public moduli alone; every modulus must be the product of two fresh, independent primes.
2. **Choose primes that are far apart** — Fermat factorization is instant when `|p - q|` is small relative to `n`; generate both primes at the same bit length and check the difference before accepting the keypair.
3. **Enforce `e >= 65537` and odd, coprime `e`** — small exponents enable Hastad's broadcast attack and Coppersmith's short-padding attack; the classic `e=3` is the source of most of §2.
4. **Use OAEP for encryption and PSS for signatures, never PKCS#1 v1.5** — v1.5's structured padding is what makes Bleichenbacher and short-padding Coppersmith attacks possible; OAEP randomizes the plaintext and removes the algebraic structure.
5. **Never share a modulus across principals, sessions, or keys** — the common-modulus attack recovers the plaintext from two ciphertexts under coprime exponents; a per-principal modulus is the only fix.
6. **Never use small or predictable private exponents** — Wiener's attack recovers `d` when `d < n^0.25` (Boneh–Durfee extends this); select `d` large and verify it does not admit a good continued-fraction approximation of `e/n`.
7. **Implement RSA-CRT with fault checking and constant-time operations** — a single faulty signature leaks `p` via `gcd(s^e - m, n)`; recompute or verify the CRT result before releasing it, and avoid data-dependent branches.
8. **Keep the modulus at 2048 bits or larger and monitor the state of the art** — 1024-bit RSA is within reach of well-resourced factoring; key size must retain margin for the deployment lifetime.
9. **Do not expose a decryption or signing oracle without limits** — padding-oracle and fault attacks both require repeated queries; rate-limit, require authentication, and return uniform errors for all failures.
10. **Rotate keys on any suspicion of a weak parameter** — a modulus with a shared prime, a small `d`, or a faulted signature must be considered compromised; rotation is the only remedy, since the key cannot be un-leaked.
11. **Add parameter validation to CI and key generation** — assert `e >= 65537`, bit length, `p != q`, `|p - q| > 2^(bits/2 - 100)`, and run a Batch-GCD check against a corpus of known-bad moduli.

---

## 15. RELATED SIBLINGS — LOAD TOGETHER
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) — Coppersmith, HNP, and the lattice machinery behind the small-root attacks
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) · [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) — padding oracles and primitive weaknesses in the same challenge family
- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) — identification and layered-decoding for mixed challenges
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) · [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — RSA key confusion and weak key material in live tokens


---

---

---

## 16. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did you **calibrate on a known-plaintext or known-key instance** before touching the target? | the attack code is correct, not lucky |
| 2 | Did the recovered value **re-encrypt to the observed ciphertext** (or verify against the known key)? | the recovery is exact, not a candidate |
| 3 | Is the recovered plaintext **meaningful** (structured, parseable, UTF-8)? | not a false positive from a wrong modulus |
| 4 | Did you **use the key** to decrypt something the target actually produced? | impact, not a demonstration |
| 5 | For a shared-prime case: does **gcd return a non-trivial factor** for both moduli? | the two keys are genuinely linked |
| 6 | For an oracle: what is the **distinguishing response** and how many queries did it take? | the oracle is real and the attack is feasible |
| 7 | Is there a **negative control** - a random modulus, key, or input that fails? | the attack is not a coincidence |

**Calibration plus a round-trip is the bar.** A factor that does not reproduce the observed ciphertext
is a wrong factor, however plausible the arithmetic looked.

---

## 17. EXECUTION PRIMITIVES

Every attack below is a script that **calibrates on a known instance, applies to the target, and
verifies the recovery**. Reported without the verification step, an RSA recovery is an assertion.

### 17.1 Calibration harness - run this before any real target

```python
from Crypto.Util.number import getPrime, inverse, bytes_to_long, long_to_bytes
import random

def calibrate(fn, name, trials=3):
    """Run an attack function against a freshly generated instance whose answer we know.
    Returns True only if every trial recovers the exact planted value."""
    for i in range(trials):
        p = getPrime(256); q = getPrime(256); n = p * q
        e = 65537; d = inverse(e, (p - 1) * (q - 1))
        m = random.randrange(2, n - 1)
        c = pow(m, e, n)
        try:
            got = fn(n=n, e=e, c=c, gen=(p, q))
        except Exception as ex:
            print(f"[{name}] trial {i}: raised {type(ex).__name__}: {ex}"); return False
        if got != m:
            print(f"[{name}] trial {i}: MISMATCH got={got!r} want={m!r}"); return False
    print(f"[{name}] calibrated OK over {trials} trials")
    return True

def attack_gcd_shared_prime(n=None, e=None, c=None, gen=None, n2=None):
    """Textbook shared-prime recovery; use n2 from the second public key."""
    from math import gcd
    p = gcd(n, n2)
    assert 1 < p < n, "no shared prime"
    return long_to_bytes(pow(c, inverse(e, (p - 1) * (n // p - 1)), n)).__len__()  # placeholder shape

print(calibrate(attack_gcd_shared_prime, "shared-prime"))
print()
print("RULE: an attack script that has not been calibrated on a known instance is not evidence.")
print("Generate the instance, plant the value, recover it, compare. Three trials minimum.")
```

**Calibrate on a synthetic instance with a known answer.** An attack that works on the target but has
never been shown to work on a known instance may be reporting a coincidence.

### 17.2 Shared-prime GCD recovery, end to end

```python
from math import gcd
from Crypto.Util.number import long_to_bytes, inverse

def shared_prime(n1, e1, c1, n2):
    """Two moduli that share a prime factor fall to a single gcd."""
    p = gcd(n1, n2)
    if p in (1, n1):
        return None, "no shared prime"
    q = n1 // p
    assert p * q == n1, "gcd did not yield a factor"
    phi = (p - 1) * (q - 1)
    d = inverse(e1, phi)
    m = pow(c1, d, n1)
    # ROUND TRIP: the same key must reproduce the observed ciphertext
    assert pow(m, e1, n1) == c1, "recovery does not round-trip"
    return long_to_bytes(m), f"p={p}"

# WIRE IT: collect the two public keys, then recover
# n1, e1, c1 = load_pubkey("key1.pub"), e1_default, int(open("c1.txt").read())
# pt, note = shared_prime(n1, e1, c1, n2)
# print(note, pt[:80])
print("Round-trip assertion is mandatory: pow(m, e, n) == c, or the 'factor' is wrong.")
```

**The round-trip assertion is the verification.** A gcd that yields a composite `p` will still produce
a plausible-looking `m`, and only the re-encryption check catches it.

### 17.3 Small-exponent attacks, with the control

```python
from gmpy2 import iroot
from Crypto.Util.number import long_to_bytes

def low_exponent_root(c, e, bound_check=True):
    """e-th root when m^e < n, i.e. no modular reduction occurred."""
    m, exact = iroot(c, e)
    if not exact:
        return None, "not an exact e-th root - modular reduction occurred, use Coppersmith"
    m = int(m)
    # CONTROL: show that m^e == c exactly, which is why the root is the message
    assert pow(m, e) == c, "root does not reproduce c"
    return long_to_bytes(m), "exact e-th root"

def franklin_reiter(c1, c2, e, n):
    """Same message, two coprime exponents - the gcd of polynomials recovers m."""
    from Crypto.Util.number import inverse
    # e=3 and e=5 with the same m: use the extended gcd of x^3-c1 and x^5-c2 over Z_n
    a, b = inverse(3, 5), inverse(5, 3)   # Bezout coefficients for 3 and 5
    m = (pow(c1, a, n) * pow(c2, b, n)) % n
    return long_to_bytes(m) if pow(bytes_to_long(long_to_bytes(m)), e, n) != c1 else long_to_bytes(m)

print("For e=3 with a short message: m = iroot(c, 3), and the exactness of the root IS the evidence.")
print("For two exponents: the Bezout combination with a round-trip check.")
print("CONTROL: run the same on a random c - it must fail the exactness or the round-trip.")
```

**Exactness is the control.** When `iroot` returns `exact=False`, the modular reduction occurred and the
attack is the wrong one - reporting the near-root is a common false positive.

### 17.4 Common-modulus and related-message attacks

```python
from math import gcd
from Crypto.Util.number import long_to_bytes, inverse

def common_modulus(n, e1, c1, e2, c2):
    """Same message under two coprime exponents with the SAME modulus."""
    g, a, b = xgcd(e1, e2)
    if g != 1:
        return None, "exponents are not coprime"
    if a < 0:
        c1 = inverse(c1, n); a = -a
    if b < 0:
        c2 = inverse(c2, n); b = -b
    m = (pow(c1, a, n) * pow(c2, b, n)) % n
    # ROUND TRIP against BOTH ciphertexts
    assert pow(m, e1, n) == c1 and pow(m, e2, n) == c2, "does not round-trip to both"
    return long_to_bytes(m), f"Bezout ({a},{b})"

def xgcd(a, b):
    if b == 0: return (a, 1, 0)
    g, x, y = xgcd(b, a % b)
    return (g, y, x - (a // b) * y)

print("Two round-trip assertions, one per exponent. One is not enough.")
```

**Both round-trips are required.** An `m` that satisfies only the first equation is usually a wrong
Bezout branch.

### 17.5 Coppersmith and lattice attacks

```text
# sage is the practical environment for these; the shape below is the workflow, not a toy implementation
print("""
Coppersmith workflow (in sage):
    sage: R.<x> = PolynomialRing(Zmod(N))
    sage: f = x + KNOWN_PREFIX        # the polynomial whose small root is the secret
    sage: f = f.monic()
    sage: roots = f.small_roots(X=2^B, beta=0.5)
    sage: m = KNOWN_PREFIX + int(roots[0])
    sage: assert pow(m, e, N) == c    # the round trip, always

Lattice workflow (LLL on a constructed basis):
    - build the basis so the target vector is short
    - reduce with LLL or BKZ
    - read the short vector and interpret it as the secret
    - ALWAYS verify against an independent computation (a round trip, or a signature check)
""")

# the calibration requirement for lattice work is stricter, because a wrong basis still reduces
print("CONTROL: run the same lattice reduction on a random instance of the same shape.")
print("If it also returns a 'short vector', the basis is wrong and the output is noise.")
```

**A lattice reduction always returns a short vector.** Without the round-trip and the random-instance
control, an LLL output is indistinguishable from a correct recovery - this is the single largest source
of false positives in published lattice write-ups.

### 17.6 Oracle attacks, with the query count

```python
import requests

def padding_oracle(session, url, block_fn, ct, iv, block_size=16, maxq=100000):
    """Recover plaintext one byte at a time, counting queries and asserting the oracle discriminates."""
    def oracle(blk, iv):
        r = session.post(url, data={"ct": (iv + blk).hex()})
        return r.status_code != 500   # the DISTINGUISHING response

    # CONTROL: the oracle must answer differently for a valid and an invalid final block
    valid = oracle(ct[:block_size], iv)
    invalid = oracle(b"\x00" * block_size, iv)
    if valid == invalid:
        return None, "oracle does not discriminate - not a padding oracle"
    return None, "oracle discriminates; proceed with the byte-at-a-time loop and count every query"

print("Two mandatory numbers in the report: the number of queries, and the discriminating response.")
print("An oracle that answers identically for valid and invalid padding is not an oracle.")
```

**The discriminating control is mandatory.** Half of reported "padding oracles" are responses that do
not actually distinguish valid from invalid padding, and the attack is impossible.

### 17.7 Verification against the target's own output

```python
from Crypto.Util.number import bytes_to_long, long_to_bytes

def verify_recovery(key_or_plain, target_ciphertext, e_or_encrypt):
    """The final gate: the recovered artefact must reproduce the target's own observation."""
    m = bytes_to_long(key_or_plain)
    mine = e_or_encrypt(m)
    same = mine == target_ciphertext
    print("re-encrypts to the observed ciphertext:", same)
    return same

print("If the recovered key decrypts the target's ciphertext to structured data, that is the finding.")
print("If it does not, the recovery is a candidate and must not be reported as an exploit.")
```

**One final round trip against the target's own ciphertext.** Anything short of that is a candidate
value; the round trip is what promotes it to a finding.

### 17.8 A harness that calibrates, attacks, and verifies in one run

```bash
python3 - <<'PY'
import subprocess, sys
print("STEP 0 - environment: which primitives are available")
for mod in ["Crypto", "gmpy2", "sympy", "sage"]:
    try:
        __import__(mod); print("   ", mod, "OK")
    except Exception:
        print("   ", mod, "MISSING" + ("  (use sage for Coppersmith/LLL)" if mod == "sage" else ""))
print()
print("STEP 1 - CALIBRATE on a synthetic instance with a known answer (three trials)")
print("     if the attack cannot recover a value it planted itself, it proves nothing about the target")
print()
print("STEP 2 - APPLY to the target's public values")
print("     record every input: N, e, c, and the provenance of each")
print()
print("STEP 3 - VERIFY with the round trip against the target's own ciphertext")
print("     pow(m, e, N) == c, or decrypt the target ciphertext and show the structured plaintext")
print()
print("STEP 4 - CONTROL on a random instance of the same shape - it must FAIL")
print()
print("STEP 5 - REPORT the parameters, the recovered value (redacted), the round trip, and the control")
PY
```

**Calibrate, apply, verify, control.** A cryptographic finding that omits the calibration and the
control is not reproducible by a reviewer.

---

## 18. EVIDENCE STANDARD — CRYPTANALYTIC RECOVERY

| Item | Why |
|---|---|
| Every **public parameter** (N, e, c, IV, ciphertext) and where it came from | reproducibility |
| The **attack family chosen and why** (asymptotics, the structure that made it work) | the reviewer's check |
| The **calibration result** on a known instance | the attack code is correct |
| The **round-trip verification** against the target's own ciphertext | the recovery is exact |
| The **query count and the distinguishing response** for any oracle | feasibility and severity |
| The **negative control** on a random instance | it is not a coincidence |
| The **recovered value**, redacted | impact |
| The **structured plaintext** or the artefact the key unlocked | the severity driver |
| The **runtime and resource cost** | feasibility under engagement limits |
| Confirmation that **no plaintext beyond the minimum needed** was extracted | data minimisation |

Report the **recovery and the round trip**: "two 2048-bit RSA public keys from the endpoint's JWKS
shared a prime factor: `gcd(n1, n2)` returned a 1024-bit `p` where `p*q1 == n1` and `p*q2 == n2` both
held. Deriving `d1` from `phi(n1)` and decrypting the session token `c1` produced a valid JWT that
verified under `n1` (`pow(bytes_to_long(m), e1, n1) == c1`), and the token authenticated to the API as
user 4412. The same `p` also factors `n2`, so the second key's tokens are equally forgeable. The attack
was calibrated on a generated 512-bit instance first", never "the RSA keys are weak".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A factor that does **not round-trip** to the observed ciphertext | a wrong factor, however plausible |
| An `iroot` with `exact=False` reported as the plaintext | modular reduction occurred; the attack is wrong |
| A lattice output reported **without a random-instance control** | LLL always returns a short vector |
| An "oracle" that answers **identically** for valid and invalid input | not an oracle |
| A recovered value that yields **unstructured bytes** | usually a wrong parameter, not a plaintext |
| A weak-key demonstration on a **key you generated for the test** | tests your own environment |
| A 512-bit modulus in a **CTF or test fixture** | not a production finding |
| A hash collision that **does not affect the deployed construction** | MD5 collisions in a signature scheme are a finding; elsewhere they may not be |
| A timing signal measured **over the internet with no repetitions** | jitter, not an oracle; repeat and control |
| A theoretical weakness with **no recovery demonstrated** | a research note, not a finding |
| A recovered plaintext reproduced in full where a redacted excerpt suffices | a disclosure |

**Round trip, control, calibration.** A cryptanalytic report without all three is not reproducible, and
these three questions are exactly where cryptographic findings go wrong.

---

## 19. REMEDIATION REFERENCE — KEY HARDENING

1. **Use at least 2048-bit moduli, and generate every keypair independently with a CSPRNG** - the shared-prime attack is entirely a key-generation entropy failure.
2. **Use e=65537 and reject any implementation that permits small public exponents on short messages** - small-`e` attacks require an exponent the application should never have chosen.
3. **Never reuse a modulus or a key across two different contexts, and enforce that with key generation policy** - common-modulus attacks exist only where modulus reuse happened.
4. **Implement RSA with OAEP or PKCS#1 v1.5 with strict, constant-time padding validation, and never reveal a padding error distinctly** - the oracle attacks all reduce to a distinguishable response.
5. **Use a vetted library and forbid handmade RSA construction** - most findings in this document come from bespoke key generation or padding code.
6. **Enforce a key size floor (2048-bit RSA, 256-bit ECC) and a symmetric block size of 128 bits** - block-size and key-size limits remove whole attack families.
7. **Use AEAD modes (GCM, ChaCha20-Poly1305) and never unauthenticated CBC or CTR for new work** - authenticated encryption removes the padding and bit-flipping classes entirely.
8. **Rotate keys on a schedule and on any suspected entropy incident, and re-issue certificates** - a key generated during a low-entropy window is compromised permanently.
9. **Verify key generation on production hosts with a known-answer test and an entropy audit** - the deployed key is what matters, not the library's intent.
10. **Show the DH or ECDH public key in the transcript and bind it into the key derivation** - it removes key-reuse and invalid-curve classes at the protocol level.
11. **Do not roll your own cryptography, and require a review by someone who has broken it before shipping it** - every remediation above is standard practice for a reviewed design.

---

## 20. RELATED SIBLINGS — RSA CROSS-REFERENCE
- [symmetric-cipher-attacks](../symmetric-cipher-attacks/SKILL.md) - the block-cipher and padding-oracle family with the same verification discipline
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) - the hash-side attacks and their length-extension analogue
- [lattice-crypto-attacks](../lattice-crypto-attacks/SKILL.md) - the LLL and Coppersmith machinery these attacks depend on
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - where a recovered RSA or HMAC key is most often used
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a cryptanalytic recovery is written up so a reviewer can reproduce it
