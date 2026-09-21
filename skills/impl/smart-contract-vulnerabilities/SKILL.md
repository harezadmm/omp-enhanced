---
name: smart-contract-vulnerabilities
description: >-
  Smart contract vulnerability playbook. Use when auditing Solidity/EVM contracts for reentrancy, integer overflow, access control, delegatecall, flash loan, signature replay, and MEV-related attack patterns.
---

# SKILL: Smart Contract Vulnerabilities — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert smart contract audit techniques. Covers reentrancy (single, cross-function, cross-contract, read-only), integer overflow, access control, delegatecall, randomness manipulation, flash loans, signature replay, front-running/MEV, and CREATE2 exploitation. Base models miss subtle cross-contract reentrancy and storage layout collisions in proxy patterns.

## 0. RELATED ROUTING

- [defi-attack-patterns](../defi-attack-patterns/SKILL.md) when the vulnerability is part of a DeFi protocol exploit (flash loans, oracle manipulation, governance attacks)
- [deserialization-insecure](../deserialization-insecure/SKILL.md) when the target is off-chain infrastructure deserializing blockchain data

### Advanced Reference

Also load [SOLIDITY_VULN_PATTERNS.md](./SOLIDITY_VULN_PATTERNS.md) when you need:
- Side-by-side vulnerable vs fixed code patterns for each vulnerability class
- Gas optimization traps that introduce vulnerabilities
- Proxy pattern storage collision examples with slot calculations

---

## 1. REENTRANCY

The most iconic smart contract vulnerability. External calls transfer execution control; if state is not updated before the call, the callee can re-enter.

### 1.1 Classic Reentrancy (Single-Function)

```
Victim.withdraw()
  ├── checks balance[msg.sender] > 0          ✓
  ├── msg.sender.call{value: balance}("")     ← external call
  │   └── Attacker.receive()
  │       └── Victim.withdraw()               ← re-enters before state update
  │           ├── checks balance[msg.sender]   ← still > 0!
  │           └── sends ETH again
  └── balance[msg.sender] = 0                 ← too late
```

### 1.2 Cross-Function Reentrancy

Two functions share state; attacker re-enters a different function during callback:

| Step | Execution | State |
|---|---|---|
| 1 | Call `withdraw()` → external call | balance still positive |
| 2 | Attacker fallback calls `transfer(attacker2)` | balance used before reset |
| 3 | `transfer` reads stale balance → moves funds | attacker2 receives tokens |
| 4 | Original `withdraw` completes, zeroes balance | damage done |

### 1.3 Cross-Contract Reentrancy

Contract A calls Contract B, which calls back into Contract A (or Contract C that reads A's stale state). Especially dangerous in DeFi protocols where multiple contracts share state.

### 1.4 Read-Only Reentrancy

The re-entered function is a `view` function used by a third-party contract for price calculation. No state modification in the victim, but the stale intermediate state misleads the reader.

**Real-world**: Curve pool `get_virtual_price()` read during `remove_liquidity()` callback → inflated price → profit on dependent lending protocol.

### Mitigations

| Pattern | Protection Level |
|---|---|
| Checks-Effects-Interactions (CEI) | Core defense; update state before external call |
| `ReentrancyGuard` (OpenZeppelin) | Mutex lock; prevents same-tx re-entry |
| Pull payment pattern | Eliminate external calls in state-changing functions |
| CEI + guard on all public functions | Defense-in-depth against cross-function |

---

## 2. INTEGER OVERFLOW / UNDERFLOW

### Pre-Solidity 0.8

Arithmetic silently wraps: `uint8(255) + 1 == 0`, `uint8(0) - 1 == 255`.

| Attack | Example |
|---|---|
| Balance underflow | `balances[attacker] -= amount` when amount > balance → huge balance |
| Supply overflow | `totalSupply + mintAmount` wraps → bypass cap checks |
| Timelock bypass | `lockTime[msg.sender] + extend` wraps to past → early unlock |

### Post-Solidity 0.8

Default checked arithmetic reverts on overflow. But `unchecked{}` blocks reintroduce risk:

```solidity
unchecked {
    // "gas optimization" — but if i can be influenced by user input, overflow returns
    for (uint i = start; i < end; i++) { ... }
}
```

### SafeMath Bypass Scenarios

- Casting: `uint256` → `uint128` truncation before SafeMath check
- Assembly blocks: `mstore` / `add` bypass Solidity-level checks
- Intermediate multiplication overflow before division: `(a * b) / c` where `a * b` overflows

---

## 3. ACCESS CONTROL

### tx.origin vs msg.sender

| Property | `msg.sender` | `tx.origin` |
|---|---|---|
| Value | Immediate caller | EOA that initiated the tx |
| Safe for auth | Yes | **No** — phishing contract can inherit tx.origin |

Attack: trick owner into calling attacker contract → attacker contract calls victim with owner's `tx.origin`.

### Common Patterns

| Issue | Impact |
|---|---|
| Missing `onlyOwner` on critical functions | Anyone can call admin functions |
| Unprotected `selfdestruct` | Anyone can destroy the contract, force-send ETH |
| Unprotected `delegatecall` | Attacker executes arbitrary code in victim's context |
| Default visibility (pre-0.6.0) | Functions default to `public` |
| Missing zero-address checks | Ownership transferred to `address(0)` |

---

## 4. RANDOMNESS MANIPULATION

On-chain randomness sources are predictable to miners/validators:

| Source | Predictability |
|---|---|
| `block.timestamp` | Miner has ~15s window to manipulate |
| `blockhash(block.number - 1)` | Known to all at execution time |
| `blockhash(block.number)` | Always returns 0 (current block hash unknown) |
| `block.difficulty` / `block.prevrandao` | Post-merge: known beacon chain value |

**Commit-reveal bypass**: If reveal phase doesn't enforce timeout or bond, attacker can choose not to reveal unfavorable outcomes (selective abort attack).

---

## 5. DELEGATECALL VULNERABILITIES

`delegatecall` executes callee's code in caller's storage context. Storage slot layout must match exactly.

### Storage Layout Collision

```
Proxy (storage):         Implementation (code):
slot 0: owner            slot 0: someVariable
slot 1: implementation   slot 1: anotherVariable
```

Implementation writes to `someVariable` (slot 0) → overwrites proxy's `owner`. Attacker calls implementation function that writes slot 0 → becomes proxy owner.

### Function Selector Collision

4-byte function selectors can collide. If proxy's `admin()` selector collides with implementation's `transfer()`, calling `admin()` on the proxy executes `transfer()` logic.

Tool: `cast selectors <bytecode>` (Foundry) to enumerate selectors.

---

## 6. FRONT-RUNNING / MEV

### Transaction Ordering Manipulation

```
Victim submits DEX swap tx (visible in mempool)
├── Front-runner: buy token before victim (raise price)
├── Victim tx executes at worse price
└── Back-runner: sell token after victim (profit from spread)
= Sandwich attack
```

### Protection Patterns

| Defense | Mechanism |
|---|---|
| Commit-reveal | Hide transaction intent until reveal |
| Flashbots / private mempool | Submit tx directly to block builder |
| Slippage protection | Set `minAmountOut` to limit MEV extraction |
| Time-lock | Delay execution to reduce predictability |

---

## 7. SIGNATURE REPLAY

### Missing Nonce

Reuse a valid signature to repeat the action (e.g., transfer) multiple times.

### Cross-Chain Replay

Same contract deployed on multiple chains with same address → signature valid on all chains. Must include `block.chainid` in signed message.

### EIP-712 Implementation Errors

| Error | Consequence |
|---|---|
| Missing `DOMAIN_SEPARATOR` with chainId | Cross-chain replay |
| Domain separator cached at deploy | Breaks after hard fork changing chainId |
| Missing nonce in struct hash | Signature replay |
| `ecrecover` returns `address(0)` on invalid sig | Passes `== address(0)` owner check |

---

## 8. SELF-DESTRUCT & FORCE-SEND ETH

`selfdestruct(recipient)` force-sends all contract ETH to recipient — bypasses `receive()` and `fallback()`, cannot be rejected.

Breaks contracts that rely on `address(this).balance` for logic (e.g., `require(balance == expected)`).

Post-EIP-6780 (Dencun): `selfdestruct` only sends ETH; code/storage deletion only if called in same tx as creation.

---

## 9. CREATE2 & DETERMINISTIC ADDRESS EXPLOITATION

`CREATE2` address = `keccak256(0xff ++ deployer ++ salt ++ keccak256(initCode))`.

| Attack | Method |
|---|---|
| Pre-fund exploitation | Predict address → send tokens/ETH before deployment → `selfdestruct` → redeploy different code at same address |
| Pre-approve exploitation | Predicted address gets token approvals → deploy malicious contract → drain approved tokens |
| Metamorphic contracts | `CREATE2` → `selfdestruct` → `CREATE2` with same salt but different `initCode` (pre-EIP-6780) |

---

## 10. FLASH LOAN ATTACK PATTERNS

```
Single transaction:
├── Borrow large amount (no collateral)
├── Manipulate state (price oracle, governance, etc.)
├── Extract profit from manipulated state
├── Repay loan + fee
└── Keep profit
```

Key: entire sequence must succeed atomically or the whole tx reverts.

---

## 11. SHORT ADDRESS ATTACK

EVM pads missing bytes in ABI-encoded calldata with zeros. If `transfer(address, uint256)` is called with a 19-byte address, the uint256 amount shifts left by 8 bits → multiplied by 256.

Mitigation: validate calldata length; modern Solidity compilers add checks.

---

## 12. TOOLS

| Tool | Purpose | Usage |
|---|---|---|
| Slither | Static analysis, vulnerability detection | `slither .` in project root |
| Mythril | Symbolic execution, path exploration | `myth analyze contract.sol` |
| Echidna | Property-based fuzzing | Define invariants, fuzz for violations |
| Foundry (Forge) | Test framework, fuzzing, gas analysis | `forge test --fuzz-runs 10000` |
| Hardhat | Development, testing, deployment | `npx hardhat test` |
| Certora | Formal verification | Write specs, prove/disprove properties |
| 4naly3er | Automated gas optimization + vuln report | CI integration |

---

## 13. DECISION TREE

```
Auditing a smart contract?
├── Is it a proxy pattern?
│   ├── Yes → Check storage layout collision (Section 5)
│   │   ├── Compare slot assignments between proxy and implementation
│   │   ├── Check for function selector collision
│   │   └── Verify initializer cannot be called twice
│   └── No → Continue
├── Does it make external calls?
│   ├── Yes → Check reentrancy (Section 1)
│   │   ├── State updated before call? → CEI pattern OK
│   │   ├── ReentrancyGuard present? → Check all entry points
│   │   ├── Cross-function state sharing? → Cross-function reentrancy risk
│   │   └── View functions read during callback? → Read-only reentrancy
│   └── No → Continue
├── Does it handle tokens/ETH?
│   ├── Yes → Check integer overflow (Section 2)
│   │   ├── Solidity < 0.8? → All arithmetic suspect
│   │   ├── unchecked{} blocks? → Verify no user-influenced values
│   │   └── Casting between uint sizes? → Truncation risk
│   └── Also check self-destruct force-send (Section 8)
├── Does it use signatures?
│   ├── Yes → Check replay (Section 7)
│   │   ├── Nonce included? → Verify incremented
│   │   ├── ChainId included? → Cross-chain safe
│   │   └── ecrecover result checked for address(0)? → OK
│   └── No → Continue
├── Does it use on-chain randomness?
│   ├── Yes → Predictable (Section 4)
│   │   └── Recommend Chainlink VRF or commit-reveal with bond
│   └── No → Continue
├── Does it interact with DeFi protocols?
│   ├── Yes → Load [defi-attack-patterns](../defi-attack-patterns/SKILL.md)
│   │   ├── Flash loan vectors
│   │   ├── Oracle manipulation
│   │   └── MEV exposure
│   └── No → Continue
├── Does it use CREATE2?
│   ├── Yes → Check deterministic address exploitation (Section 9)
│   └── No → Continue
└── Run automated tools (Section 12)
    ├── Slither for static analysis
    ├── Mythril for symbolic execution
    └── Echidna for fuzzing invariants
```

---

## 14. CONFIRMING THE FINDING

On-chain, a plausible code smell and an exploitable flaw are separated by **an executed transaction that
took value**, because the chain itself is the evidence. This table is the gate.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the **fork state pinned** to a block number, and the block recorded with its hash? | an unpinned fork is not reproducible |
| 2 | Is there an **executed transaction** - not a static-analysis report? | the chain is the evidence, and a detector is a hypothesis |
| 3 | Did **value or state actually move**, and is that observable in balances or storage? | the impact, not the mechanism |
| 4 | Is there a **negative control**: the same call against the patched/fixed contract, reverting? | the control that makes it a flaw, not a feature |
| 5 | Is the **precondition** stated: the attacker's starting capital, and whether it was borrowed? | a flash-loan-funded attack is a different finding from a free one |
| 6 | Was the **detector's own output** reconciled against the executed proof, with disagreements noted? | a tool's flag is a lead |
| 7 | Is the impact expressed in the protocol's own terms (funds at risk, function reachable)? | a severity without a quantity is an assertion |

**A pinned fork, an executed transaction, an observable value or state movement, and a fixed-contract control.**
A static analyser's report is a hypothesis about code; the chain is what proves it.

---

## 15. EXECUTION PRIMITIVES

Solidity's execution model makes this domain's verification unusually clean: **a fork gives you the exact
chain, and a test gives you the exact transaction.** Every step below is a procedure, with the control pair
being the flawed contract and the fixed contract under the same call.

### 14.1 The fork, pinned, and the baseline

```bash
# THE FORK MUST BE PINNED TO A BLOCK AND THE BLOCK HASH RECORDED. Otherwise nothing is reproducible.
echo "=== 1. the pinned fork ==="
cat <<'FORK'
  RECORD, AND PUT IN THE REPORT:
    the CHAIN and the CHAIN ID          (a replay across chains is a different finding)
    the BLOCK NUMBER the fork was taken at
    the BLOCK HASH                       <- the hash, not just the number: a reorg changes the number's meaning
    the RPC ENDPOINT's kind              (an archive node is required for historical state)
    the CONTRACT ADDRESSES and their CODE HASHES at that block
  WHY THE BLOCK MATTERS HERE SPECIFICALLY: contract state is MUTABLE and upgradeable, so a finding
  against a contract at block N may not exist at block N+1. THE BLOCK IS PART OF THE FINDING.
  AND THE CODE HASH: a proxy pattern means the address is stable while the implementation changes,
  so the ADDRESS alone identifies nothing. RECORD THE IMPLEMENTATION'S CODE HASH.
FORK
echo
echo "=== 2. the baseline: the protocol's own balances and invariants BEFORE the attack ==="
cat <<'BASE'
  RECORD BEFORE ANY EXPLOIT TRANSACTION:
    the protocol's total value locked, in the token's units
    the specific balances the attack will move (the pool, the vault, the attacker's start)
    THE INVARIANT the protocol claims to maintain (e.g. 'the sum of shares equals the total assets',
    'k = x*y is non-decreasing', 'the vault holds at least the sum of deposits')
  THE INVARIANT IS THE MOST VALUABLE BASELINE, because the finding is usually 'the invariant was
  violated' rather than 'a number changed'. STATE IT IN THE PROTOCOL'S OWN TERMS.
  AND THE CONTROL: MEASURE THE INVARIANT ON A NORMAL TRANSACTION TOO, and show it HOLDS. Without
  that, you have not shown the invariant is meaningful.
BASE
echo
echo "=== 3. the harness, with the fork pinned ==="
echo "  foundry:  forge test --fork-url \$RPC --fork-block-number \$BLOCK -vvvv"
echo "  hardhat:  await network.provider.request({method:'hardhat_reset',params:[{forking:{jsonRpcUrl:RPC,blockNumber:BLOCK}}]})"
echo "  record: the TOOL and its VERSION, the COMMIT of the PoC, and the exact command."
echo "  a PoC that depends on a moving fork (latest) is NOT reproducible, and it will fail for the reader."
```

**The block number and the implementation's code hash are part of the finding** — a proxy's address
identifies nothing, and contract state is mutable, so a finding at block N may not exist at block N+1.

### 14.2 The transaction, and the control pair

```bash
echo "=== THE CONTROL PAIR: the flawed contract AND the fixed contract, same call ==="
cat <<'PAIR'
  THE FINDING IS A DIFFERENCE. THE PAIR IS:
    A. the ATTACK TRANSACTION against the deployed contract at the pinned block   -> SUCCEEDS, value moves
    B. THE SAME CALL against the FIXED contract (or the same contract with the guard applied)
                                                                                  -> REVERTS
  AND THE EXACT REVERT REASON IN B IS ITSELF EVIDENCE: it names the guard that now holds
  (e.g. 'nonReentrant', 'insufficient allowance', 'slippage'). The guard's NAME identifies the fix.

  HOW TO GET B, in the order of preference:
    1. the PROTOCOL'S OWN PATCH, if one exists, deployed at a later block or on a testnet
    2. the CONTRACT WITH THE GUARD ADDED, compiled from source with ONE line changed - record the diff
    3. a MINIMAL MOCK reproducing only the flawed pattern and its guarded counterpart
  OPTION 2 IS THE MOST CONVINCING, because the diff is ONE line and proves the guard is the cause.

  AND THE SECOND CONTROL, which is specific to this domain:
    THE SAME ATTACK WITHOUT THE PRECONDITION (without the flash loan, without the front-run position)
                                                                                  -> FAILS or is unprofitable
  That control proves the PRECONDITION is load-bearing, and it separates 'a free exploit' from
  'an exploit that requires capital you must borrow'.
PAIR
echo
echo "=== THE PROFITABILITY ARITHMETIC, which most PoCs omit ==="
python3 - <<'PY'
print("  A DEFI-ADJACENT ATTACK THAT LOSES GAS AND FEES IS NOT AN EXPLOIT. SHOW THE ARITHMETIC:")
print()
print("    the attacker's STARTING balance (per token)")
print("    the value MOVED by the attack")
print("    the GAS used, and the fee at the block's base fee")
print("    any FLASH LOAN FEE (typically 0.05%-0.09%, and it is NOT free)")
print("    any SLIPPAGE or swap fee paid")
print("    the SANDWICH or competition cost, if applicable")
print("    ------------------------------------------------------------------")
print("    the NET, and whether it is positive AFTER the costs")
print()
print("  A PoC that shows a large number moving but a NET LOSS demonstrates the FLAW and not the")
print("  EXPLOIT. BOTH ARE FINDINGS, and they are DIFFERENT SEVERITIES. Say which one you have.")
print()
print("  AND THE CAPITAL CEILING: the profit is bounded by what the pool can absorb. An attack that")
print("  works for 1 ETH may fail for 1000 ETH because the price impact swallows the gain. STATE")
print("  WHERE THE ATTACK STOPS SCALING - that is the difference between a critical and a medium.")
PY
```

**The same call against the fixed contract reverting, with the guard's own name in the revert reason, is the
control** — and showing a flaw with a net loss is a different severity from showing a profitable exploit.

### 14.3 The class-specific proofs, and the tools

```bash
echo "=== THE INVARIANT CHECK, which is the strongest generic proof here ==="
cat <<'INV'
  FOR ANY OF SECTIONS 1-11, THE STRONGEST STATEMENT IS AN INVARIANT THAT HELD BEFORE AND WAS
  VIOLATED AFTER. THE PROCEDURE:
    1. STATE the invariant in the protocol's own terms
    2. MEASURE it on a NORMAL transaction -> it HOLDS
    3. MEASURE it across the attack transaction -> it is VIOLATED
    4. SHOW THE TRANSACTION THAT VIOLATED IT, and the two values on either side of it
  THIS COVERS REENTRANCY (the balance invariant), OVERFLOW (the arithmetic invariant), ACCESS
  CONTROL (the authorisation invariant), ORACLE MANIPULATION (the price invariant), AND
  FLASH-LOAN ATTACKS (the solvency invariant) - the SAME TEST SHAPE FOR ALL OF THEM.
INV
echo
echo "=== THE TOOL LAYER (section 12), and what each tool CAN and CANNOT prove ==="
python3 - <<'PY'
T = [("Slither",     "static analysis",      "pattern matches in SOURCE",
      "FALSE POSITIVES BY DESIGN. A flag is a LEAD, and it must be confirmed by an executed transaction."),
     ("Mythril",     "symbolic execution",    "paths that REACH a vulnerable state",
      "a path report is not an execution; the path must be realised on a fork."),
     ("Echidna",     "property fuzzing",      "an INVARIANT BROKEN by a generated input",
      "the STRONGEST signature, because a broken invariant is a real counterexample - but the input must be replayable."),
     ("Foundry",     "fork testing",          "AN EXECUTED TRANSACTION on real state",
      "THIS IS THE PROOF LAYER. Everything above leads here."),
     ("a manual read","human reasoning",      "the INTENT and the missing check",
      "the source of the best findings, and the source of the most false ones. Confirm on a fork.")]
print("%-13s %-22s %-40s %s" % ("tool","method","what it can prove","its limit"))
for a,b,c,d in T: print("%-13s %-22s %-40s %s" % (a,b,c,d))
print()
print("  THE RULE: A TOOL'S OUTPUT IS A HYPOTHESIS. THE FOUNDRY-EXECUTED TRANSACTION IS THE FINDING.")
print("  AND WHEN A TOOL AND THE EXECUTION DISAGREE, THE EXECUTION WINS - always, and the")
print("  disagreement is worth recording, because it characterises the tool's false-positive rate here.")
PY
echo
echo "=== THE ON-CHAIN CONTEXT, which decides whether it is a finding at all ==="
cat <<'CTX'
  A CONTRACT PATTERN IS A FLAW ONLY IF SOMETHING OF VALUE IS AT STAKE AND REACHABLE:
    - the VALUE the contract holds, at the pinned block, in its own units
    - the AUTHORISATION required to reach the function (none? a role? a signature?)
    - whether the PROTOCOL IS PAUSABLE (a pause switch changes exploitability DURING disclosure)
    - whether an ADMIN can front-run the fix, or has ALREADY fixed it
    - the CHAIN: a fork of the chain, an L2's own sequencer, a testnet - each is a different finding
  REPORT THE REACHABILITY, not just the pattern. 'The contract is vulnerable to reentrancy' without the
  value at stake and the function's authorisation is a pattern, not a finding.
CTX
```

**A tool's output is a hypothesis and the foundry-executed transaction is the finding** — and when they
disagree, the execution wins. Report the value at stake and the function's authorisation, not just the pattern.

### 14.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== SMART CONTRACT ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the fork is PINNED to a block number AND the block hash is recorded",
  "an unpinned fork is not reproducible, and contract state is mutable"),
 ("the IMPLEMENTATION's code hash is recorded, not just the proxy's address",
  "a proxy's address is stable while its implementation changes"),
 ("the protocol's claimed INVARIANT is stated and measured BEFORE the attack",
  "the finding is usually 'the invariant was violated', not 'a number changed'"),
 ("the invariant was also measured on a NORMAL transaction, and it HELD there",
  "without it, the invariant is not shown to be meaningful"),
 ("an ATTACK TRANSACTION was actually EXECUTED on the pinned fork, not merely reasoned about",
  "a static report is a hypothesis; the chain is the evidence"),
 ("the CONTROL ran: the same call against the FIXED contract REVERTS, and the guard is named in the revert",
  "the one-line diff proves the guard is the cause"),
 ("the SECOND CONTROL ran: the same attack WITHOUT the precondition fails or is unprofitable",
  "proves the precondition is load-bearing and separates free from capital-requiring exploits"),
 ("the PROFITABILITY arithmetic is shown: value moved, gas, flash-loan fee, slippage, and the NET",
  "a flaw with a net loss is a different severity from a profitable exploit"),
 ("the point where the attack STOPS SCALING is stated",
  "the capital ceiling is the difference between critical and medium"),
 ("the tool's output was RECONCILED against the execution, and any disagreement recorded",
  "a tool's flag is a lead, and the execution wins"),
 ("the value at stake and the function's AUTHORISATION are reported",
  "'vulnerable to reentrancy' without them is a pattern, not a finding"),
 ("the chain, the pause state, and any existing fix are stated",
  "each changes exploitability and the disclosure's shape"),
 ("the tool, its version, the PoC's commit, and the exact command are recorded",
  "the PoC must be reproducible by the next reader"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  state      : the chain, the block number and hash, the implementation's code hash")
print("  invariant  : the protocol's own invariant, before, after, and on a normal transaction")
print("  transaction: the executed attack, with the value moved and the state changes")
print("  control    : the fixed contract's revert, the guard's name, and the no-precondition case")
print("  economics  : value moved, costs, the net, and the scaling ceiling")
print("  context    : the value at stake, the authorisation, the pause state, any existing fix")
print("  reproduction: the tool, the version, the commit, the command")
PY
```

A pinned state, a stated invariant, an executed transaction, the fixed-contract revert, the economics, and
the on-chain context.

---

## 16. EVIDENCE STANDARD
| Item | Why |
|---|---|
| The **chain, the block number, and the block hash** the fork was pinned to | contract state is mutable, so the block is part of the finding |
| The **implementation's code hash**, not only the proxy's address | a proxy's address is stable while its implementation changes |
| The **protocol's claimed invariant**, measured before, after, and on a normal transaction | the invariant is usually the finding's real statement |
| The **executed transaction**, with the value moved and the storage changed | the chain is the evidence, and a static report is a hypothesis |
| The **fixed-contract control**, reverting, with the guard named in the revert reason | the one-line diff proves the guard is the cause |
| The **no-precondition control**: the same attack without the borrowed capital, failing | separates a free exploit from a capital-requiring one |
| The **profitability arithmetic**: value moved, gas, flash-loan fee, slippage, and the net | a flaw with a net loss is a different severity |

### Verification failures — how they mislead

| Failure | How it misleads |
|---|---|
| An **unpinned fork** | nothing reproduces, and the finding cannot be re-derived |
| The **proxy's address** recorded instead of the implementation's code hash | the implementation changes under a stable address |
| A **static analyser's flag** reported as the finding | a detector is a hypothesis; the execution is the evidence |
| **No fixed-contract control** | the flaw may be intended behaviour |
| The **precondition untested** | a flash-loan-funded attack and a free one are different findings |
| A **PoC showing a large number moving** with a net loss | demonstrates a flaw, not an exploit, and they are different severities |
| The **scaling ceiling ignored** | an attack that works for 1 ETH may fail at 1000 ETH |

| Item | Why |
|---|---|
| The **chain, block number, block hash**, and the **implementation's code hash** | the pinned, identified state the finding is against |
| The **protocol's invariant**, its value before, after, and on a normal transaction | the finding is usually the invariant's violation |
| The **executed transaction**, with the value moved and the storage changed | the chain is the evidence |
| The **fixed-contract revert**, with the guard's name | proves the guard is the cause |
| The **no-precondition control** | separates free from capital-requiring exploits |
| The **economics**: value moved, gas, flash-loan fee, slippage, and the net | a net loss and a net gain are different findings |
| The **scaling ceiling** and the value at stake | the difference between a critical and a medium |

**A pinned block, the implementation's code hash, an executed transaction, and the fixed-contract revert** —
and a tool's flag is a hypothesis while the execution on the fork is the finding.

---

## 17. REMEDIATION REFERENCE

Contract remediation is **code plus process**, and the process half is usually the one that fails.

1. **Fix at the invariant's layer.** If the invariant is "the vault holds at least the sum of deposits",
   the fix belongs where that is enforced, not at the entry point that happened to violate it.
2. **Name the guard and its ordering.** State whether the check is before or after the state change and
   whether a reentrancy guard is required, because the order is the fix.
3. **Distinguish an upgradeable fix from a redeploy.** A proxy implementation can be upgraded; an
   immutable contract cannot, so the remediation is a migration and it needs a plan.
4. **State the visibility requirement.** If the fix depends on a user action, say how users learn of it.
5. **Include the economics in the fix.** Where the flaw's exploitability depends on flash-loan capital,
   the remediation includes oracle design and liquidity limits, not only the guard.
6. **Say what the fix does not cover.** A guard at one function does not secure a second path to the same
   state, and an audit is not a fix.

---

## 18. RELATED SIBLINGS - LOAD TOGETHER
- [defi-attack-patterns](../defi-attack-patterns/SKILL.md) - the protocol-level patterns this domain's primitives compose into
- [code-review](../code-review/SKILL.md) - the source-reading practice a hypothesis starts from
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) - the differential and minimal-reproduction discipline
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how an economics argument is reported
- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) - the signature-and-replay analysis this shares with section 7
