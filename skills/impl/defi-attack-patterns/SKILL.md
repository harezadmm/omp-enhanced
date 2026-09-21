---
name: defi-attack-patterns
description: >-
  DeFi attack pattern playbook. Use when analyzing flash loan attacks, price oracle manipulation, MEV sandwich attacks, governance exploits, bridge vulnerabilities, and token standard edge cases in decentralized finance protocols.
---

# SKILL: DeFi Attack Patterns — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert DeFi exploitation techniques. Covers flash loan mechanics, oracle manipulation (spot vs TWAP), MEV extraction (sandwich, JIT, liquidation), precision loss attacks, governance exploits, bridge vulnerabilities, and token standard pitfalls. Base models often miss the single-transaction atomicity constraint of flash loans and the distinction between spot price and TWAP manipulation.

## 0. RELATED ROUTING

- [smart-contract-vulnerabilities](../smart-contract-vulnerabilities/SKILL.md) for underlying Solidity vulnerability patterns (reentrancy, integer overflow, delegatecall)
- [deserialization-insecure](../deserialization-insecure/SKILL.md) when targeting off-chain bridge relayer or indexer infrastructure

---

## 1. FLASH LOAN ATTACKS

### 1.1 Mechanism

Flash loans provide uncollateralized borrowing within a single transaction. The entire borrow → use → repay cycle must complete atomically; if repayment fails, the transaction reverts as if nothing happened.

| Provider | Max Amount | Fee |
|---|---|---|
| Aave V3 | Pool liquidity per asset | 0.05% (can be 0 for approved borrowers) |
| dYdX | Pool liquidity | 0 (uses internal balance manipulation) |
| Uniswap V3 | Pool liquidity per pair | 0.3% (swap fee tier) |
| Balancer | Pool liquidity | Protocol-configurable |

### 1.2 Price Oracle Manipulation

```
1. Flash borrow 100,000 WETH
2. Swap 100,000 WETH → TOKEN on AMM_A
   → TOKEN spot price on AMM_A skyrockets
3. On Lending_Protocol (reads AMM_A spot price as oracle):
   → Deposit small TOKEN collateral (valued at inflated price)
   → Borrow large amount of WETH against it
4. Swap TOKEN back → WETH on AMM_A (restore price)
5. Repay flash loan (100,000 WETH + fee)
6. Keep borrowed WETH from Lending_Protocol minus collateral cost
```

**Key insight**: protocols using AMM spot reserves (`getReserves()`) as price oracles are vulnerable. Must use TWAP or external oracle (Chainlink).

### 1.3 Liquidity Pool Drain via Reentrancy

Flash borrow → deposit into pool → trigger reentrancy during callback → withdraw more than deposited → repay loan.

Exploits the combination of flash loan capital with reentrancy in pool accounting logic.

### 1.4 Governance Flash Borrow

```
1. Flash borrow governance tokens
2. Create/vote on malicious proposal (if no snapshot or timelock)
3. Proposal passes instantly
4. Execute proposal (drain treasury, change admin, etc.)
5. Return governance tokens
```

Defense: snapshot-based voting (Compound Governor Bravo), timelocks, minimum proposal period.

---

## 2. PRICE ORACLE MANIPULATION

### 2.1 Spot Price vs TWAP

| Oracle Type | Manipulation Cost | Time Window |
|---|---|---|
| Spot price (`getReserves()`) | Single large swap (flash loanable) | Same transaction |
| TWAP (Time-Weighted Average) | Sustained multi-block manipulation | Multiple blocks (expensive) |
| Chainlink aggregator | Compromise ≥ majority of oracle nodes | Practically infeasible |

### 2.2 AMM Manipulation Flow

```
Normal state: Pool has 1000 ETH + 1,000,000 USDC → price = 1000 USDC/ETH

Attack:
├── Swap 9000 ETH into pool
│   Pool now: 10000 ETH + 100,000 USDC (constant product)
│   Spot price: 10 USDC/ETH (crashed 100x)
├── Dependent contract reads this price
│   → Liquidates positions at wrong price
│   → Or allows cheap borrowing against ETH collateral
├── Swap back: buy ETH with USDC
│   Price restores to ~1000 USDC/ETH
└── Net profit = value extracted from dependent contract - swap slippage - fees
```

### 2.3 Chainlink Oracle Staleness

```solidity
(, int price, , uint updatedAt, ) = priceFeed.latestRoundData();
// Missing checks:
// 1. price > 0
// 2. updatedAt != 0
// 3. block.timestamp - updatedAt < HEARTBEAT
// 4. answeredInRound >= roundId
```

If oracle is stale (network congestion, L2 sequencer down), price can be hours old → arbitrage against stale price.

**L2 Sequencer Risk**: If Arbitrum/Optimism sequencer is down, Chainlink prices freeze. When it comes back, prices jump → mass liquidations at wrong prices.

---

## 3. MEV (MAXIMAL EXTRACTABLE VALUE)

### 3.1 Sandwich Attack

```
Mempool observation: victim submits swap TOKEN_A → TOKEN_B with slippage 1%

Front-run:  Buy TOKEN_B (increase price)
Victim tx:  Swap executes at worse price (within slippage tolerance)
Back-run:   Sell TOKEN_B (profit from price impact)

Profit = victim's price impact - gas costs × 2
```

### 3.2 JIT (Just-In-Time) Liquidity

```
1. Observe large pending swap in mempool
2. Provide concentrated liquidity in the exact price range (Uniswap V3 tick)
3. Victim's swap executes → JIT LP earns majority of fees
4. Remove liquidity immediately after swap
5. Profit = fee earned - gas - impermanent loss (minimal for single block)
```

### 3.3 Liquidation MEV

```
1. Monitor lending protocols for positions approaching liquidation threshold
2. When price oracle updates → position becomes liquidatable
3. Front-run other liquidators → execute liquidation
4. Receive liquidation bonus (typically 5-15% of collateral)
5. Sell collateral for profit
```

### 3.4 MEV Protection Mechanisms

| Mechanism | How It Works |
|---|---|
| Flashbots Protect | Sends tx to private mempool; only block builder sees it |
| MEV Blocker | RPC endpoint that routes through MEV-aware relayers |
| Cow Protocol (batch auction) | Batch matching eliminates ordering advantage |
| Encrypted mempools | Threshold encryption; decrypt only at block build time |
| MEV-Share | User captures portion of MEV extracted from their tx |

---

## 4. PRECISION LOSS EXPLOITATION

### 4.1 Rounding Errors in Token Calculations

Solidity has no floating point. Integer division truncates:

```
shares = depositAmount * totalShares / totalAssets
```

If `totalAssets` is very large relative to `depositAmount * totalShares`, result rounds to 0 → depositor gets no shares but pool keeps the deposit.

### 4.2 First Depositor / Vault Inflation Attack

```
1. Attacker deposits 1 wei → receives 1 share
2. Attacker donates 1,000,000 tokens directly to vault (not via deposit)
3. Vault state: 1,000,001 tokens, 1 share
4. Victim deposits 999,999 tokens:
   shares = 999,999 * 1 / 1,000,001 = 0 (integer truncation)
5. Victim gets 0 shares; attacker owns 100% of vault (now 2,000,000 tokens)
6. Attacker withdraws all
```

**Defenses:**
- Mint dead shares on first deposit (OpenZeppelin ERC4626 offset)
- Require minimum initial deposit
- Internal accounting with virtual offset

### 4.3 Dust Attack via Precision Truncation

Repeated small operations where each truncation loses 1 wei. Accumulate across thousands of operations → material loss.

---

## 5. GOVERNANCE ATTACKS

### 5.1 Flash Loan Governance

Borrow governance tokens → vote → return. Only works if protocol doesn't snapshot balances before voting.

### 5.2 Timelock Bypass

| Vector | Method |
|---|---|
| Timelock set to 0 | Admin can execute proposals instantly |
| `emergencyExecute` function | Bypasses timelock for "emergencies" |
| Guardian/multisig override | Single point of failure |
| Proposal cancellation by attacker | Front-run with cancel if threshold met |

### 5.3 Quorum Manipulation

```
Protocol requires 10% quorum (10M tokens out of 100M supply)
├── Flash borrow 10M governance tokens
├── Create proposal: set admin = attacker
├── Vote with borrowed tokens → meets quorum
├── If no timelock: execute immediately
└── Return tokens
```

---

## 6. BRIDGE EXPLOITS

### 6.1 Common Bridge Attack Vectors

| Vector | Example |
|---|---|
| Signature verification bypass | Ronin Bridge ($624M) — compromised 5/9 validators |
| Message replay | Replay deposit proof on multiple chains |
| Fake deposit proof | Submit proof for non-existent L1 deposit |
| Validator collusion | Compromised majority of bridge validators |
| Smart contract bug | Wormhole ($320M) — uninitialized guardian set |
| Upgradeable proxy exploit | Attacker gains upgrade authority → swap implementation |

### 6.2 Cross-Chain Message Verification

```
Secure pattern:
├── Source chain: emit event with (destination, amount, nonce, chainId)
├── Relayer: submit proof (Merkle proof of event inclusion)
├── Destination chain: verify proof against known source block header
│   ├── Check nonce not replayed
│   ├── Check chainId matches
│   ├── Verify Merkle proof against trusted root
│   └── Mint/release tokens

Vulnerable pattern:
├── Relayer: submit (destination, amount) signed by N-of-M validators
└── If M is small or keys are compromised → forge signatures
```

---

## 7. TOKEN STANDARD EDGE CASES

### 7.1 ERC-20 Approval Front-Running

```
1. Alice approves Bob for 100 tokens
2. Alice wants to change approval to 50 tokens
3. Bob sees the approval change tx in mempool
4. Bob front-runs: transferFrom(Alice, Bob, 100) — uses old approval
5. Alice's approval change executes: approval = 50
6. Bob calls transferFrom(Alice, Bob, 50) — uses new approval
7. Bob extracted 150 tokens instead of 50
```

Defense: `approve(0)` first, then `approve(newAmount)`. Or use `increaseAllowance/decreaseAllowance`.

### 7.2 ERC-777 Reentrancy via Hooks

ERC-777 tokens call `tokensReceived()` hook on the recipient before completing the transfer → classic reentrancy vector.

```
transfer(attacker, amount)
├── _beforeTokenTransfer hook
├── Balance update
├── tokensReceived() callback to recipient  ← reentrancy window
│   └── attacker re-enters: transfer, swap, deposit, etc.
└── _afterTokenTransfer hook
```

### 7.3 Fee-on-Transfer Tokens

Tokens that deduct a fee on each transfer. Protocol receives less than `amount`:

```solidity
// Vulnerable: assumes received == amount
token.transferFrom(msg.sender, address(this), amount);
deposits[msg.sender] += amount; // overcredits by fee amount

// Fixed: measure actual balance change
uint before = token.balanceOf(address(this));
token.transferFrom(msg.sender, address(this), amount);
uint received = token.balanceOf(address(this)) - before;
deposits[msg.sender] += received;
```

### 7.4 Rebasing Tokens

Tokens that automatically adjust balances (e.g., Aave aTokens, stETH). Protocols holding rebasing tokens may have accounting mismatches if they cache balances.

---

## 8. NOTABLE DEFI EXPLOITS REFERENCE

| Exploit | Date | Loss | Primary Vector |
|---|---|---|---|
| Ronin Bridge | Mar 2022 | $624M | Compromised validator keys |
| Wormhole | Feb 2022 | $320M | Signature verification bug |
| Beanstalk | Apr 2022 | $182M | Flash loan governance |
| Mango Markets | Oct 2022 | $114M | Oracle manipulation |
| Euler Finance | Mar 2023 | $197M | Donation attack + liquidation logic |
| Curve (reentrancy) | Jul 2023 | $73M | Vyper compiler reentrancy bug |

---

## 9. DECISION TREE

```
Analyzing a DeFi protocol?
├── Does it use price oracles?
│   ├── Spot price (AMM reserves)? → Flash loan manipulation (Section 1.2)
│   │   └── Can oracle be manipulated in single tx? → HIGH RISK
│   ├── TWAP? → Multi-block manipulation needed → MEDIUM RISK
│   ├── Chainlink? → Check staleness handling (Section 2.3)
│   │   ├── Heartbeat check present? → OK
│   │   └── L2? → Check sequencer uptime oracle
│   └── Multiple oracles with fallback? → Evaluate each
├── Does it accept external tokens?
│   ├── Yes → Check fee-on-transfer handling (Section 7.3)
│   ├── ERC-777 tokens accepted? → Reentrancy via hooks (Section 7.2)
│   └── Rebasing tokens? → Accounting mismatch (Section 7.4)
├── Does it have governance?
│   ├── Yes → Flash loan governance possible? (Section 5.1)
│   │   ├── Snapshot-based voting? → Safer
│   │   └── Live balance voting? → Flash borrow attack
│   ├── Timelock present? → Check for bypass (Section 5.2)
│   └── Quorum threshold vs flash-loanable supply? (Section 5.3)
├── Is it a vault / yield aggregator?
│   ├── Yes → First depositor attack (Section 4.2)
│   │   └── Virtual offset or dead shares? → Mitigated
│   └── Precision loss in share calculation? (Section 4.1)
├── Is it a bridge?
│   ├── Yes → Load bridge vectors (Section 6)
│   │   ├── Validator set size and key management?
│   │   ├── Replay protection (nonce + chainId)?
│   │   └── Upgradeable? → Who holds upgrade key?
│   └── No → Continue
├── User-facing swap functionality?
│   ├── Yes → MEV exposure (Section 3)
│   │   ├── Slippage protection enforced?
│   │   └── Private mempool integration?
│   └── No → Continue
└── Load [smart-contract-vulnerabilities](../smart-contract-vulnerabilities/SKILL.md)
    for underlying Solidity-level bugs
```

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the exploit **profitable on a fork**, at the block the vulnerable code was live? | not "profitable in theory" |
| 2 | Did the **control** - the same sequence WITHOUT the manipulation - lose money? | the manipulation is causal |
| 3 | Is the **fork pinned** to the vulnerable block, with the fork block number recorded? | a moving chain makes the result unreproducible |
| 4 | What was the **attacker's balance** before and after, in the token and in native? | the profit, including gas |
| 5 | Was the drain an **attacker-recoverable** value, or did it sit in the contract? | profit, not a locked fund |
| 6 | Is the vulnerability **still live** on the target chain, or already patched? | a historical finding is a different report |
| 7 | What is the **impact on solvency**: proportional, or total? | severity |

**A profitable exploit on a pinned fork, with the control losing money, and the profit measured in the
attacker's own balance.** An identified vulnerability class is a hypothesis.

---

## 11. EXECUTION PRIMITIVES

A DeFi finding is proven by **a profitable exploit on a pinned fork, a control sequence that loses money,
and the attacker's balance measured before and after**. A recognized vulnerability class is not a finding.

### 10.1 The pinned fork, which is the precondition for everything

```bash
# the fork must be PINNED to the block where the code was live, or the result is unreproducible
RPC="${RPC:-https://eth-mainnet.g.alchemy.com/v2/$ALCHEMY_KEY}"
BLOCK="${BLOCK:?set BLOCK to the block at which the target was vulnerable}"
echo "=== 1. confirm the target code EXISTS at that block ==="
cast code "$TARGET" --block "$BLOCK" --rpc-url "$RPC" | head -c 80; echo " ..."
echo "  a 0x response means no code at that block - wrong address, or wrong chain."
echo
echo "=== 2. confirm the vulnerable variable's value AT that block, not now ==="
# example: a price, a reserve, a totalSupply, an owner
cast call "$TARGET" "totalSupply()(uint256)" --block "$BLOCK" --rpc-url "$RPC" || true
cast call "$TARGET" "getReserves()(uint112,uint112,uint32)" --block "$BLOCK" --rpc-url "$RPC" || true
echo
echo "=== 3. THE CONTROL: the same reads at HEAD, to show the state has moved ==="
cast call "$TARGET" "totalSupply()(uint256)" --rpc-url "$RPC" || true
echo "  -> a DIFFERENT value at HEAD than at BLOCK means the pool or supply has changed, which is why"
echo "     the fork must be pinned. Reporting a fork result against live state is the standard error."
echo
echo "=== 4. record the fork metadata in the report ==="
echo "  chain, RPC endpoint, block number, and the block's timestamp."
```

**The pinned block is the precondition, and the HEAD read is the control that shows the state moved.** A
fork result reported against live state is the standard error in this family.

### 10.2 The exploit harness, with the control sequence

```javascript
// Foundry shape: test, attack, and CONTROL in one file so the comparison is visible
// file: test/Exploit.t.sol
pragma solidity ^0.8.0;
import "forge-std/Test.sol";

interface IERC20 { function balanceOf(address) external view returns (uint256);
                   function approve(address,uint256) external returns (bool); }
interface IPool  { function swap(uint256,uint256,address,bytes calldata) external; }

contract ExploitTest is Test {
    address constant TARGET = address(0);   // set to the vulnerable contract
    address constant TOKEN  = address(0);
    uint256 constant FORK_BLOCK = 0;        // PIN IT

    address attacker = address(0xA11CE);

    function setUp() public {
        vm.createSelectFork(vm.envString("RPC"), FORK_BLOCK);   // the pin
        vm.deal(attacker, 100 ether);
        vm.label(attacker, "attacker");
    }

    /// the CONTROL arm: the same sequence WITHOUT the manipulation
    function test_Control_NoManipulation() public {
        vm.startPrank(attacker);
        uint256 before = IERC20(TOKEN).balanceOf(attacker);
        // ... the same calls, minus the oracle/price manipulation ...
        uint256 after_ = IERC20(TOKEN).balanceOf(attacker);
        // THE ASSERTION: the control must NOT profit. If it does, your 'exploit' is noise.
        assertLe(after_, before, "CONTROL PROFITED - the manipulation is not causal");
        vm.stopPrank();
    }

    /// the ATTACK arm
    function test_Exploit() public {
        vm.startPrank(attacker);
        uint256 before = IERC20(TOKEN).balanceOf(attacker);
        // ... flash loan, manipulation, the vulnerable interaction, repayment ...
        uint256 after_ = IERC20(TOKEN).balanceOf(attacker);
        assertGt(after_, before, "ATTACK DID NOT PROFIT at this block");
        emit log_named_uint("profit", after_ - before);
        vm.stopPrank();
    }
}
```

```bash
forge test --match-test "test_Control|test_Exploit" -vvv
echo "  BOTH arms must pass: the control does NOT profit, the exploit DOES."
echo "  A run where the control also profits proves the sequence is unprofitable either way, or that"
echo "  the 'profit' comes from the fork's own mechanics. Do not report it."
```

**Both arms must pass and the control must not profit.** A control that also profits means the
"exploit" is fork mechanics rather than the manipulation.

### 10.3 Profit accounting, which must include gas

```bash
cat <<'ACCOUNTING'
THE ARITHMETIC THAT DECIDES WHETHER THIS IS A FINDING
  profit = (assets out) - (assets in) - (gas actually paid) - (flash-loan fee)
An exploit that nets +0.4 ETH before gas and -0.9 ETH after is NOT profitable on mainnet; it is a
theoretical mispricing. Say which figure you are reporting and on which chain.

WHAT TO MEASURE, in the attacker's OWN balance:
  - the drained token and its value at the pinned block's price
  - the native-token balance delta, which includes gas
  - any receipt token, LP position, or claim that has a market value but is not yet realised
  - the flash-loan repayment, which is an outflow
Realised profit and unrealised receipts are DIFFERENT numbers and must not be summed silently.

RECOVERABILITY, which is the second question:
  a contract's reserves drained into the ATTACKER's address   -> realised profit
  a contract's accounting corrupted while funds stay in it    -> a DoS or a bad-debt finding
  a value transfer to an address the attacker does not control-> NOT profit; report the impact instead
  an unlimited approve granted but unused                     -> a latent risk, not a drain

SEVERITY, which follows the impact and not the technique:
  total loss of a pool's reserves           -> critical
  a proportional share of one pool          -> high, and state the fraction
  a mispricing that is not extractable      -> informational, and say so
  a governance or upgrade path reachable    -> critical regardless of the immediate profit
ACCOUNTING
```

**Profit must be net of gas and the flash-loan fee, and realised profit differs from an unrealised
receipt.** An unlimited approve that is never used is a latent risk rather than a drain.

### 10.4 Is the vulnerability live now?

```bash
# a historical exploit is a DIFFERENT report from a live vulnerability
echo "=== THE LIVE-CHECK, which decides which report this is ==="
RPC="${RPC:?}"
TARGET="${TARGET:?}"
echo "code size at HEAD      : $(cast code "$TARGET" --rpc-url "$RPC" | wc -c)"
echo "code size at FORK_BLOCK: $(cast code "$TARGET" --block "$FORK_BLOCK" --rpc-url "$RPC" | wc -c)"
echo "  -> a CHANGED code hash means the contract was upgraded or replaced since the pinned block."
cast codehash "$TARGET" --rpc-url "$RPC"
cast codehash "$TARGET" --block "$FORK_BLOCK" --rpc-url "$RPC"
echo
echo "=== the second check: is the vulnerable state still reachable? ==="
echo "  the same values read again at HEAD (10.1 step 3). A moved reserve or supply may mean the"
echo "  attack is no longer profitable even with identical code."
echo
echo "=== THE REPORT MUST SAY WHICH OF THESE IT IS ==="
echo "  1. LIVE: code and the vulnerable state are both present at HEAD -> an actionable finding"
echo "  2. PATCHED: the code hash changed -> a historical finding, and name the upgrade"
echo "  3. STALE: identical code but the state has moved such that the attack no longer profits"
echo "     -> a latent weakness; state the condition that would re-enable it"
```

**Live, patched, or stale — the report must say which.** Identical code with moved state is a latent
weakness, and naming the condition that would re-enable it is the actionable part.

### 10.5 The end-to-end harness

```bash
python3 - <<'PY'
print("=== DEFI EXPLOIT ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the chain, RPC, and the PINNED FORK BLOCK are recorded",
  "an unpinned fork makes the result unreproducible"),
 ("code EXISTS at the pinned block (a non-0x `cast code`)",
  "no code means a wrong address, chain, or block"),
 ("the vulnerable variable was read AT the block, with the HEAD value as the control",
  "this is what proves the pinning matters"),
 ("a CONTROL arm ran the same sequence WITHOUT the manipulation and did NOT profit",
  "if the control profits, the manipulation is not causal"),
 ("the exploit arm PROFITED, and both arms are shown together",
  "the comparison is the finding; one arm alone is an anecdote"),
 ("profit is net of gas AND the flash-loan fee, or the gross figure is labelled as gross",
  "a pre-gas profit on mainnet may be a loss"),
 ("realised profit and unrealised receipts are reported separately",
  "an LP position is not a drain"),
 ("the attacker's balance delta is shown in both the drained asset and native",
  "the native delta is where gas appears"),
 ("the vulnerability's LIVE / PATCHED / STALE status is stated, with the code hashes",
  "a historical exploit is a different report"),
 ("a remediation recommendation is stated even for a patched issue",
  "the same pattern recurs in sibling contracts"),
]
for n, how in CHECKS: print("  [ ] %-64s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  fork    : chain, RPC, block, timestamp, and the code hash at that block")
print("  control : the same sequence without the manipulation, and its result")
print("  exploit : the sequence, and the profit's full accounting")
print("  status  : LIVE / PATCHED / STALE, with the HEAD code hash")
print("  impact  : the fraction of a pool, or total loss, and who bears it")
PY
```

**Both arms together, the full profit accounting, and the live status.** The control arm is what converts
a sequence into a finding.

---

## 12. EVIDENCE STANDARD — EXPLOIT ARTEFACTS

| Item | Why |
|---|---|
| The **chain, RPC, fork block, and block timestamp** | the reproduction's coordinate system |
| The **code hash at the fork block** and at HEAD | distinguishes live, patched, and stale |
| The **vulnerable variable's value** at the block, with the HEAD value as the control | proves the pinning matters |
| The **control arm's result**: the same sequence without the manipulation | the manipulation must be causal |
| The **exploit arm's profit**, with both arms shown together | the comparison is the finding |
| The **profit accounting**: gas, flash-loan fee, and the flash-loan principal | a gross figure may be a loss |
| **Realised versus unrealised** value, separately | an LP position is not a drain |
| The **attacker's balance delta** in the drained asset and in native | the available profit |
| The **LIVE / PATCHED / STALE** status | which report this is |
| The **fraction of the pool** lost, or the total | severity |

Report the **control and the accounting**: "at Ethereum block `19_842_113` (`2024-03-11T14:22:00Z`) the
pool at `0x…` holds reserves of `1_204.31` WETH and `3_911_882` USDC, and `cast codehash` at that block
is `0x8a41…` against `0x8a41…` at HEAD, so the code is unchanged. The exploit arm flash-borrowed
`2_000` WETH, swapped through the pool to move its spot price by `31.4%`, called the vulnerable
`liquidate` while the manipulated spot price was the only oracle consulted, repaid the loan with its
`0.09%` fee, and ended with a balance of `+18.42` WETH and `+61_204` USDC, which is
`+121_508` USD at the block's own prices and `-0.031` ETH in gas, so the net realised profit is positive
and is the figure reported. The control arm ran the identical sequence with the swap removed and ended at
`-0.031` ETH, so the manipulation is causal. The state at HEAD has moved - reserves are now `890.11`
WETH and `2_988_221` USDC - so the same trade is no longer profitable at the current depth even though
the code is unchanged, which makes this a STALE rather than a LIVE vulnerability, and the condition that
would re-enable it is a return of the pool's depth to the pinned block's level", never "the protocol is
vulnerable to oracle manipulation".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An **unpinned fork** result | the state has moved; the result is unreproducible |
| A control arm that **also profits** | the manipulation is not causal |
| Profit reported **before gas and the flash-loan fee** | on mainnet that is frequently a loss |
| An **unrealised** LP position reported as a drain | no value left the protocol |
| Value transferred to an address the attacker **does not control** | a different impact class |
| An **unlimited approve** that was never used | a latent risk, not an exploit |
| A **historical** exploit reported as live, with no code-hash check | the reader will chase a patched issue |
| A **recognized vulnerability class** with no working sequence | a hypothesis |
| An exploit that **requires a different block's state** than the one pinned | the pinning is wrong |
| A profit measured in a **token with no liquidity** at that block | the value is not realisable |
| A fork result reported against **live state** | the state moved; see the control read |

**A pinned fork, a non-profiting control, a net-of-fees profit, and a live-status check.** A recognized
class and a control that also profits are this family's two standard non-findings.

---

## 13. REMEDIATION REFERENCE — DEFI EXPLOIT ASSESSMENT

1. **Pin the fork to the block at which the code was live, and record the chain, RPC, block, and timestamp with the result** - an unpinned fork makes any profit figure meaningless.
2. **Always run the control arm without the manipulation and require it not to profit** - the comparison is the finding, and a control that profits invalidates it.
3. **Report profit net of gas and the flash-loan fee, or label the figure as gross explicitly** - a pre-gas profit on mainnet is often a loss.
4. **Separate realised profit from unrealised receipts, because an LP position is not a drain** - the two numbers answer different questions.
5. **Measure the attacker's balance delta in both the drained asset and the native token** - the native delta is where gas appears.
6. **Read the vulnerable variable at the pinned block AND at HEAD as the control, to show the pinning matters** - a value that has moved is the reason the pin is required.
7. **Check the live status by comparing code hashes at the fork block and at HEAD, and classify the finding as LIVE, PATCHED, or STALE** - an identical code hash with moved state is a different finding from a patched one.
8. **For a STALE finding, name the condition that would re-enable it: the pool depth, the oracle's dominance, or the reachable governance path** - that is the actionable part.
9. **Do not treat a recognized vulnerability class as a finding without a working, profitable sequence** - the class is a hypothesis and the sequence is the evidence.
10. **State the impact as a fraction of a pool or as a total loss, and name who bears it** - severity follows the impact rather than the technique.
11. **Include a remediation recommendation even for a patched issue, because the same pattern recurs in sibling contracts and forks** - the value of a historical finding is upstream.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [smart-contract-vulnerabilities](../smart-contract-vulnerabilities/SKILL.md) - the contract-level defect classes underneath
- [symbolic-execution-tools](../symbolic-execution-tools/SKILL.md) - where a constraint must be solved rather than reasoned about
- [bug-bounty-agents](../bug-bounty-agents/SKILL.md) - the triage and reporting flow around a financial finding
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a profit-accounted finding is reported
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - where a drained-address trail is correlated
