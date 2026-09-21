# Gate 3 increment 7 tiny-runtime and quantized-semantics report

Date: 2026-08-16
Exact base: `9683e0be4d892e6a6a134b45a065e591e139da3c`
Exact core implementation head: `acc6b3b254e6d358ddabe495b1ca79295dd36d70`
Exact canonical head: `b961623513a0e137b959f608ce31511d59e85888`
Canonical run: https://github.com/elder-plinius/OBLITERATUS/actions/runs/31947837466
Status: PASS; PR #109 was exact-head audited, signature-preserving merged, and
canonically reconciled

## Results

| Gate | Result |
|---|---|
| Focused contracts | 268 restoration, runtime, offline-model, analysis, and policy tests passed; the final runtime set is 111/111 green |
| Mandatory CPU lane | Python 3.12: 2,112 passed, 9 conditional tests deselected, 0 failed, and 0 skipped in 87.70s |
| Python 3.10 portability lane | 2,113 passed, 9 conditional tests deselected, 0 failed, and 0 skipped in 88.18s; mature scope 94.04% statements / 84.61% branches |
| Repository coverage | 82.76% statements / 69.55% branches before; 83.50% / 71.08% after |
| Mature CPU scope | 93.27% / 83.06% before; 94.02% statements / 84.54% branches after |
| Immutable mature floor | Raised from 92% / 80% to 94% / 84% in policy and validator |
| Changed executable lines | 58/58 (100%) against the exact base before documentation-only changes |
| Core pipeline | `abliterate.py`: 50.91% / 38.03% before; 52.63% statements / 40.73% branches after |
| Adaptive defaults | 93.59% / 81.65% before; 100% statements / 89.87% branches after |
| Advanced metrics | 91.73% / 82.19% before; 100% statements / 98.61% branches after |
| Loader decisions | 92.14% / 90.00% before; 100% statements / 96.67% branches after |
| Runtime contracts | 100% statements / 100% branches, including the new restoration policy |
| Selected mutation | 1,844/2,057 killed (89.65%); 208 survived and 5 timed out outside changed logic; every restoration-helper mutant killed |
| Repeatability | 702 tests passed in each of three file orders/hash seeds in 36.857s; no flakes, skips, or consistent failures |
| Package | Wheel and sdist built at version 0.1.2; both pass Twine metadata validation |
| Policy | Ruff, immutable quality policy, conditional policy, risk map, mutation-target guard, global/mature coverage, and changed-line gates passed |

The canonical item-7 head reaches every quantitative Gate 3 repository and
mature CPU exit criterion. Its post-merge run passed all eight required jobs;
the quality-depth lane completed the repeat and 2,057-mutant campaign in
28m26s. Ordinary feature work remains held until the conditional-evidence and
final-reporting items are reconciled.

## Contracts added

1. Multi-direction norm restoration measures logical dequantized weights,
   restores once after the full subspace projection, caps amplification, and
   fails closed for non-finite or degenerate norms.
2. Integer storage is promoted to a logical float parameter instead of casting
   a projected float back to Byte/uint8 and erasing the result. The exact
   Float-to-integer failure reported in issue #11 is covered.
3. Float and integer restoration preserve `Parameter` identity. Quantized
   replacement rebinds every module alias to the same replacement parameter,
   preserving tied/shared-weight semantics.
4. Packed modules use their repacker when available, explicitly materialize a
   float weight with a warning when safe, and fail closed when they expose
   neither a repacker nor writable logical weight.
5. A deterministic, generated GPT-2 fixture executes the real advanced
   two-direction pipeline, saves and reloads the checkpoint, proves weights
   changed, and independently verifies every transformer-layer matrix norm.
6. Adaptive-default knowledge lookup and merge boundaries, advanced-metric
   tensor/refusal/KL/CKA boundaries, and loader import-compatibility failures
   now have executable negative contracts rather than uncovered decision paths.
7. The source-to-test risk map now makes projection-math contracts mandatory
   whenever the core abliteration pipeline changes.

## Defects detected and corrected

The pre-change norm restoration iterated raw parameters, converted integer
weights to float for arithmetic, and copied the result back to the original
integer dtype. That reproduces the reported PyTorch Float-to-Byte failure or,
where a cast succeeds, silently destroys fractional projection and rescaling
values. It also measured packed bytes instead of logical dequantized weights.

The corrected path classifies storage before restoration, uses the model's
dequantization and replacement seams, and keeps integer values in float storage
when no quantization scale/zero-point contract exists. The first tied-weight
review then exposed a second defect: replacing one quantized parameter could
break aliases. Alias rebinding now preserves the tie after replacement.

The changed-line gate initially reported 43/47 covered lines. Packed fallback,
degenerate no-op, and in-place float restoration contracts raised the final
production result to 58/58. Coverage review also found a duplicate unreachable
empty-sequence check in first-token KL validation; the shared tensor validator
already rejects that input, so the dead branch was removed.

The first hosted matrix exposed a separate portability weakness: every test
passed on Python 3.10 and 3.11, but a random power-iteration start took an early
numerical path in the Riemannian curvature helper, lowering mature coverage to
93.85%. A direct deterministic correction contract now exercises the normal
path and both early-return boundaries without depending on Python or Torch RNG
behavior. A locked local Python 3.10 rerun passes the full suite and the 94/84
policy at 94.04% statements and 84.61% branches.

## Verification and evidence

- Mandatory Python 3.12 coverage:
  `/tmp/obliteratus-item7-final2-coverage-py3.12.json`
- Mandatory Python 3.12 JUnit:
  `/tmp/obliteratus-item7-final2-junit-py3.12.xml`
- Corrected mandatory Python 3.10 coverage:
  `/tmp/obliteratus-item7-fix-coverage-py3.10.json`
- Corrected mandatory Python 3.10 JUnit:
  `/tmp/obliteratus-item7-fix-junit-py3.10.xml`
- Exact-base Python 3.12 coverage:
  `/tmp/obliteratus-main-9683e0b-zvr8hF/test-evidence-py3.12/coverage-py3.12.json`
- Clean non-editable Python 3.12 test environment:
  `/tmp/obliteratus-item7-py312-env-AxUcVD`
- Mutation artifacts:
  ignored worktree-local `mutants/` evidence prepared from the exact candidate;
  final score 89.65% (1,844/2,057) with no changed-helper survivor
- Repeat evidence: `/tmp/obliteratus-item7-repeat-gate.json`
- Package artifacts: `/tmp/obliteratus-item7-package-QBOhVU/`; SHA-256
  `34dcd464df0661bf63da3a9c4e406b7acbfa73e6fd09127aef6211d7a30a249e`
  (wheel) and
  `f487391c98e4931896238b38b5232fb2f7c08147ec90767328734bf04c5c5c69`
  (sdist)
- Canonical reconciliation comment:
  https://github.com/elder-plinius/OBLITERATUS/pull/109#issuecomment-5307612606

The first isolated sync selected unsupported Python 3.13 and was not used as
evidence. A separate reused Python 3.12 environment correctly failed two
installed-artifact provenance assertions because it imported a different
worktree. The final environment was recreated non-editably from this worktree,
its isolated import resolved to its own `site-packages`, and all 2,112 selected
tests passed.

## Signing and integration policy

Every candidate commit is signed with the configured repository publish key
fingerprint `62297562B1C7053088F405DB0117DAAA677A5BF2` through the approved host
GPG wrapper and verified locally with `git verify-commit`. Integration must
preserve that signature by exact fast-forward or create a locally signed merge
commit. GitHub rebase merge is not acceptable because it recreates unsigned
canonical commits.

## Scope and release decision

This increment uses a synthetic random-initialized offline model and isolated
temporary filesystems. It makes no network, external-model, accelerator,
credential, or publication claim. The exact-head and canonical runs passed all
hosted CPU, repeat, mutation, package, Windows, and supply-chain gates, and the
signed commits were preserved on `main`. Conditional evidence reconciliation
and final Gate 3 reporting remain open, so ordinary feature work does not
resume yet.
