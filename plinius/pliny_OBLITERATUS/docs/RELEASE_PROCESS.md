# Pull-request acceptance and release process

OBLITERATUS separates contributor feedback, maintainer acceptance, canonical
integration, and release certification. A green pull-request check is necessary,
but it is not by itself an acceptance or release decision.

The enforced workflows and machine-readable policies remain authoritative. This
document explains how maintainers apply them.

## Pull-request states

1. **Reviewable:** the exact pull-request head is signed, conflict-free, and green
   in the contributor-facing checks. Relevant behavior has focused coverage and
   the description identifies tests not run, risk surfaces, and evidence limits.
2. **Accepted:** a maintainer audits that immutable head SHA for correctness,
   research integrity, security, compatibility, documentation, and applicable
   policy/risk-map changes. New commits invalidate the audit and require the new
   head to be checked.
3. **Integrated:** the accepted head is merged with the repository's configured
   merge-commit method. Squash and rebase merges are not used. The resulting
   canonical `main` commit must have a forge-verified signature, and its post-merge
   CI must pass before it can become a release candidate.
4. **Release-certified:** an exact signed `v*` tag on a clean canonical commit has
   passed every required release gate and its emitted source snapshot and evidence
   have been independently verified.

Maintainers may add test depth or hardening in separately attributable signed
commits before acceptance. Thresholds, assertions, required jobs, or risk mappings
must never be weakened merely to merge a pull request.

## Acceptance criteria

A pull request cannot be accepted while any of these conditions applies:

- its reviewed head SHA differs from the current head;
- a commit lacks a verifiable signature;
- required checks are pending, failing, stale, or attached to another SHA;
- relevant behavior has no meaningful test or contract coverage;
- review threads, conflicts, unexplained generated files, unrelated changes, or
  unaddressed trust-boundary risks remain;
- research or performance claims exceed the supplied reproducible evidence;
- dependency, workflow, policy, documentation, or compatibility effects are not
  included in the same reviewable change.

The fast pull-request lane is deliberately narrower than the release suite. It
establishes review readiness without shifting release-depth work to contributors.

## Release candidate preparation

After all accepted work is merged, maintainers:

1. reconcile the hosted pull-request and issue queues;
2. prune merged branches and confirm `main` is clean and synchronized;
3. verify the canonical merge signatures and post-merge CI results;
4. run the exhaustive local or hosted readiness suite against the exact candidate;
5. update the project version and create a new signed annotated version tag.

Tags are immutable audit records. A failed candidate is not moved, deleted, or
reused. It remains unpublished, and the corrected candidate receives a new patch
version and a new signed tag.

## Exact-tag release certification

Pushing a `v*` tag runs the exhaustive release workflow against the tagged commit:

- Python 3.10, 3.11, and 3.12 tests, import/CLI smoke checks, repository and branch
  coverage floors, critical-file floors, mature CPU-scope policy, and touched-module
  no-regression comparison;
- deterministic order and hash-seed repeats plus the bounded selective mutation
  score gate;
- Windows checkpoint contracts;
- lock, workflow, package, secret, vulnerability, license, and supply-chain policy;
- creation of exactly one deterministic `git archive` source ZIP, a digest-bound
  CycloneDX SBOM, `SHA256SUMS`, SLSA provenance, and Sigstore bundles.

The package job creates the source ZIP once. Downstream validation and publication
must reuse those exact bytes; rebuilding an equivalent archive is not acceptable.
OBLITERATUS releases do not publish wheels, source distributions, executables, or
compiled libraries.

## Conditional evidence and publication

Before publication, maintainers manually run the applicable hosted software gates
against the exact tagged commit, including the pinned model/evaluation, disposable
network-service, and operator-UI gates. Hardware or credential-bound gates run only
when their trusted prerequisites are available. An unselected gate is not positive
support evidence, and an approved waiver blocks the associated support claim.

Publication occurs only after:

- the complete exact-tag workflow succeeds;
- the source ZIP checksum, SBOM binding, archive contents, and repository
  attestations are independently verified;
- applicable conditional evidence is successful and fresh;
- a draft release contains only the tested source ZIP and its checksum, SBOM, and
  attestation evidence, with matching digests.

Publishing triggers the conditional workflow again. That release-event run must
also finish successfully and is retained as the final release record.

See [Supply-chain policy](SUPPLY_CHAIN_POLICY.md) for artifact verification and
[Conditional test operations](conditional-testing.md) for selection, freshness,
runner isolation, and waiver semantics.
