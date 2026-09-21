# Blind-SQLi challenge provenance

- Origin: implemented for T3MP3ST issue #189 after decomposition of proposal #163.
- License: AGPL-3.0-or-later, matching the repository.
- Intended vulnerability: the `/query` sku filter is built by string concatenation into one SQLite query; the single unescaped quote is the injection point. The oracle answers with a boolean plus a row count only, so values must be extracted through blind comparison.
- Flag handling: `T3MP3ST{bl1nd_or4cl3_d4t4}` is a committed synthetic lab constant held in the `secrets` table of an in-memory SQLite database; a correct extraction returns it and the solver asserts equivalence.
- Reproduction: `python3 ctf/docker/web/sqli-blind/solve.py` must print the flag.
- Rollback: delete `docker/web/sqli-blind/`, the two `sqli-blind-*` compose services, the `web_sqli_blind` manifest entry, and `scripts/test-ctf-sqli-blind.mjs`; the lab leaves no host state, volumes, or external network.
- Sensitive-data review: users, inventory, and flag values are synthetic constants created for this lab. No acquired data, production secret, key, credential, or user identifier is present; no host credential or production-data mount exists.
- Container trust: the Dockerfile pins the official Python multi-platform OCI index digest. There are no package-manager or third-party runtime dependencies (stdlib only). The challenge service has only an internal network; a separately constrained allow-list gateway owns the loopback host binding.
- Verification date: 2026-09-03.
