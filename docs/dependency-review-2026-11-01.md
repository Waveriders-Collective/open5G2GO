# Dependency consolidation — November 1, 2026

Reviewed all 18 open Dependabot PRs (#40–57) against `584d551` on `main`.
The combined branch includes the compatible changes and the small application
fixes needed to keep existing behavior. Passing checks on an individual PR did
not establish compatibility: for example, the PySNMP update silently disabled
monitoring, and the container updates were not covered by the Python test matrix.

## Disposition of each proposal

| PR | Proposed update | Disposition and evidence |
| --- | --- | --- |
| [#40](https://github.com/Waveriders-Collective/open5G2GO/pull/40) | Node 24 → 26 builder | Included; clean install, lint, build, and full frontend image build pass on the exact proposed Node 26 digest. CI and npm auditing now use Node 26. |
| [#41](https://github.com/Waveriders-Collective/open5G2GO/pull/41) | Python 3.12 → 3.15 image | Included; locked install, tests, and backend image build pass. CI adds 3.15 while retaining 3.11 and 3.12. |
| [#42](https://github.com/Waveriders-Collective/open5G2GO/pull/42) | Open5GS Ubuntu 22.04 → 26.04 | Deferred pending broader core integration testing, not a demonstrated build failure. ARM64 image build, all 14 daemon version/library checks, and isolated NRF HTTP/2 API smoke passed in Lima. The image still installs legacy MongoDB 6.0 packages from the Jammy repository; coordinate migration with [#32](https://github.com/Waveriders-Collective/open5G2GO/issues/32) and [#37](https://github.com/Waveriders-Collective/open5G2GO/issues/37). |
| [#43](https://github.com/Waveriders-Collective/open5G2GO/pull/43) | setup-buildx-action 3.12.0 → 4.4.1 | Included; upstream tag/commit and removed-input compatibility reviewed. Container CI now exercises this Action. |
| [#44](https://github.com/Waveriders-Collective/open5G2GO/pull/44) | TypeScript 5.9.3 → 7.0.2 | Deferred; the compiler removes `baseUrl`, and the existing TypeScript ESLint stack crashes on the changed API. Migrate compiler configuration and lint dependencies together. |
| [#45](https://github.com/Waveriders-Collective/open5G2GO/pull/45) | eslint-plugin-react-hooks 4.6.2 → 7.1.1 | Deferred; seven new `set-state-in-effect` errors across six components. Refactor those effects before adopting the new recommended rules. |
| [#46](https://github.com/Waveriders-Collective/open5G2GO/pull/46) | @vitejs/plugin-react 4.7.0 → 6.1.2 | Deferred; plugin 6 requires Vite 8, but the project uses Vite 6. Upgrade the build stack together. |
| [#47](https://github.com/Waveriders-Collective/open5G2GO/pull/47) | React and React types 18 → 19 | Deferred; the proposal leaves React DOM and its types on 18, producing incompatible peers. Migrate all four packages and application types together. |
| [#48](https://github.com/Waveriders-Collective/open5G2GO/pull/48) | HTTPX 0.27.2 → 0.28.1 | Included; new real FastAPI/Starlette/HTTPX tests exercise application startup, health, and OpenAPI. |
| [#49](https://github.com/Waveriders-Collective/open5G2GO/pull/49) | Lucide React 0.300.0 → 1.64.0 | Included; frontend lint and production build pass. |
| [#50](https://github.com/Waveriders-Collective/open5G2GO/pull/50) | pytest-cov 4.1.0 → 7.1.0 | Included; the suite passes with coverage enabled. |
| [#51](https://github.com/Waveriders-Collective/open5G2GO/pull/51) | PySNMP 6.2.6 → 7.1.30 | Included with migration to `v3arch.asyncio.get_cmd`, awaited transport creation, and engine cleanup. Regression tests verify installed API availability and real transport construction with mocked query responses. |
| [#52](https://github.com/Waveriders-Collective/open5G2GO/pull/52) | Ruff 0.1.15 → 0.17.3 | Included with an explicit `E4`, `E7`, `E9`, `F` selection preserving the project's prior checks; the new release expands its defaults. Lint passes. |
| [#53](https://github.com/Waveriders-Collective/open5G2GO/pull/53) | FastAPI 0.135.4 → 0.162.0 | Included; application and HTTP compatibility tests pass. |
| [#54](https://github.com/Waveriders-Collective/open5G2GO/pull/54) | mypy 1.20.2 → 2.4.1 | Included; runs with the same 24 pre-existing diagnostics in six files as the baseline. CI does not currently gate mypy. |
| [#55](https://github.com/Waveriders-Collective/open5G2GO/pull/55) | metadata-action 5.10.0 → 6.2.0 | Included; upstream pin and tag-expression compatibility reviewed. Container CI now exercises it. |
| [#56](https://github.com/Waveriders-Collective/open5G2GO/pull/56) | build-push-action 6.19.2 → 7.4.0 | Included; upstream pin and inputs reviewed. Container CI now uses the same Action with `push: false`. |
| [#57](https://github.com/Waveriders-Collective/open5G2GO/pull/57) | login-action 3.7.0 → 4.7.0 | Included; upstream pin and existing GHCR inputs reviewed. Authenticated publishing was not invoked for validation. |

## Combined validation

- Python 3.12 and 3.15: 93 tests and 31 subtests pass on each interpreter;
  coverage invocation, Ruff, and Poetry lock validation pass.
- All 50 locked Python package/version variants pass the vulnerability audit.
  Only the six proposed Python versions and their transitive dependency changes
  were introduced by lock resolution.
- Frontend: clean installation, lint, and production build pass on Node 24 and
  the exact Node 26 container digest. Production npm audit has no findings;
  the full audit has no high/critical findings and retains the existing 15
  moderate development-only minimatch findings tracked in
  [#35](https://github.com/Waveriders-Collective/open5G2GO/issues/35).
- Frontend and backend container images build locally on ARM64. Runtime checks
  cover backend health, frontend static delivery, nginx API proxying, and PySNMP
  availability in an isolated network with no host ports exposed. These checks
  do not replace the Linux CI matrix or multi-platform release verification.
- Workflow YAML, actionlint, the current Dependabot configuration schema, and
  whitespace checks pass.

No live eNodeB/gNodeB or subscriber radio session was exercised. SNMP tests mock
the network response while using the installed package's transport and engine.
No image was published and no deployment was changed during local validation.
The Ubuntu 26 review image's installed `mongodb-org-shell` package contains no
`mongo` executable; baseline behavior was not compared, so this is not classified
as a regression caused by the proposed Ubuntu update.

## Future updates

The `dependencies` multi-ecosystem group batches Python, npm, Docker, and GitHub
Actions version updates into one weekly PR, including compatible major updates.
GitHub applies security updates separately and supports grouping them only
within an ecosystem. See the official
[multi-ecosystem configuration](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configuring-multi-ecosystem-updates)
and [security grouping limits](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates).

Targeted version holds keep the deferred migrations out of the routine batch.
Remove each hold with its coordinated migration. Holds can also affect security
fixes in those ranges, so continue reviewing security alerts and package audits.
Grouping configuration takes effect when merged into the default branch; it
does not enable automatic merging.
