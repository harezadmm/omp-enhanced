# Supply-chain policy

The committed `uv.lock` is the reproducible dependency source for the supported
Python 3.10–3.12 test matrix. CI installs CPU-only PyTorch from PyTorch's
explicit package index and resolves every other package from PyPI. The lock
contains exact versions, source URLs, environment markers, and artifact hashes.

CI uses exact Python tool versions and checksum-pinned standalone binaries.
`ci/digests.txt` records executable and GitHub Action pins; build, test, and
license-tool transitive dependencies are covered by `uv.lock`.

## Bayesian optimizer dependency

Optuna is a core dependency (`>=4.9,<5`), installed by both `pip install .`
and the documented locked development setup. The `optimized` and `heretic`
pipeline methods therefore receive their requested Bayesian optimization
without a separate manual installation. A partial environment that lacks
Optuna still reports the fallback in the pipeline log and checkpoint metadata.

The lock pins Optuna 4.9.0 and adds Alembic 1.19.2, colorlog 6.12.0,
greenlet 3.5.5, Mako 1.4.1, and SQLAlchemy 2.0.52 without upgrading existing
packages. These distributions come from PyPI, with artifact SHA-256 hashes in
`uv.lock`; the signed repository change records the reviewed lock. The package
registry and package publishers remain the source trust boundary. No hosted
Optuna service, dashboard, database connection, or integration extra is used:
the optimizer creates an in-memory study.

The package license inventory identifies MIT/MIT License for Optuna, Alembic,
colorlog, Mako, and SQLAlchemy. Optuna's bundled third-party notices cover
SciPy-derived BSD code and fdlibm's permissive notice. Greenlet's included
`LICENSE` and `LICENSE.PSF` identify MIT code and Stackless/Python-derived code
under PSF-2.0. The reviewed composite expression `MIT AND PSF-2.0` is therefore
included in the allow list; preserve both notices when redistributing it.
No vulnerability suppression is added. Dependency updates remain subject to
the same vulnerability and license gates as the rest of the lock.

`tests/test_bayesian_optimizer_optuna.py` runs real Optuna trials with tiny
local CPU tensors, verifies in-range warm starts and model restoration, and
uses no model download, network, credentials, or accelerator.

## Digest-bound release evidence

The release artifact is a deterministic ZIP snapshot of the tested repository
commit. No wheel, source distribution, executable, or other compiled package is
published. The release job creates the snapshot once with `git archive`, then
emits a bound CycloneDX source SBOM and a canonical `SHA256SUMS` manifest.

GitHub's keyless Sigstore-backed attestation service signs two in-toto
statements for that release set:

- SLSA build provenance for every subject named by `SHA256SUMS`;
- an SBOM attestation binding the CycloneDX document to the source ZIP digest.

The supply-chain job downloads the package job's retained artifact, verifies
`SHA256SUMS`, and revalidates the SBOM binding. It must not create a substitute
archive. Publication must use this same tested and attested ZIP. A commit,
dependency lock, snapshot instruction, artifact, checksum manifest, SBOM, or
release-policy change invalidates the evidence.

The release is first assembled as a draft and its uploaded asset digests are
compared with the verified workflow outputs. It is published only after the exact-tag
and applicable conditional gates pass. Failed tags remain immutable, unpublished
audit records; a corrected candidate uses a new version. See
[`RELEASE_PROCESS.md`](RELEASE_PROCESS.md) for the complete acceptance and
publication sequence.

Consumers can perform the portable integrity check with:

```bash
sha256sum --check SHA256SUMS
```

For authenticity and provenance, verify the source ZIP against the canonical
repository with GitHub's attestation verifier. A checksum without its signed
provenance proves byte integrity only; it does not prove who built the artifact
or which source and build instructions produced it.

## Required evidence

The Supply chain job retains these artifacts for 14 days:

- one redacted Gitleaks JSON report for the checkout;
- OSV audit JSON and scanner status for Python 3.10, 3.11, and 3.12 on Linux;
- a JSON license inventory for all supported dependency extras;
- a CycloneDX 1.5 source SBOM bound to the repository ZIP by SHA-256;
- the policy decisions and exact tested source ZIP used by those checks.

Every secret finding and every OSV vulnerability is blocking by default. OSV
does not provide a normalized severity for every advisory, so the policy treats
unknown, low, medium, high, and critical findings alike. This is stricter than
a high-only threshold and avoids silently passing advisories with missing
severity data.

License metadata must exactly match an expression in
`ci/supply-chain-policy.json`. OBLITERATUS itself is excluded from dependency
license evaluation because its AGPL license is the project license rather than
a third-party dependency decision.

## Exceptions

Exceptions live only in `ci/supply-chain-policy.json`; command-line ignores and
unconditional success conversion are forbidden.

- A vulnerability exception names an OSV/GHSA/CVE identifier, states a reason,
  records `approved_on` and `expires`, and declares whether a fix is available.
  Fixable findings may be excepted for at most 7 days; findings without a fix
  may be excepted for at most 90 days.
- A secret exception names the redacted Gitleaks fingerprint, states a reason,
  and records `approved_on` and `expires`. It may last at most 30 days.
- Expired, overlong, stale, malformed, or unused exceptions fail CI. A finding
  that gains a fix cannot use an exception declared as unfixable.
- License exceptions are not supported. Add an exact expression only after a
  maintainer verifies the package metadata and compatibility with AGPL-3.0-or-later.

## Updating the lock and tools

Use the version of uv recorded in `ci/digests.txt`:

```bash
uvx --from uv==0.12.4 uv lock --upgrade
uvx --from uv==0.12.4 uv lock --check
```

Review the complete lock diff, source indexes, new licenses, vulnerability
evidence, and SBOM diff. Update direct pins in `pyproject.toml` and executable
pins/checksums in `ci/digests.txt` in the same pull request. A normal dependency
or tool update must not add an exception merely to make CI green.
