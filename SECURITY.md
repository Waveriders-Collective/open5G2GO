# Security Policy

## Supported versions

open5G2GO does not publish versioned releases yet. Security fixes land on
`main` and in the `:latest` container images built from it, so update your
install to pick them up.

## Reporting a vulnerability

**Please do not report security vulnerabilities in public GitHub issues.**

Report them privately through GitHub instead: open the repository's
**Security** tab and choose **Report a vulnerability**
([direct link](https://github.com/Waveriders-Collective/open5G2GO/security/advisories/new)).
Only the maintainers can see the report.

Please include:

- what an attacker could do, and from where (same LAN, the radio side, the internet)
- steps to reproduce, and whether you run 4G or 5G mode
- the version, from `/api/v1/health` or `git rev-parse --short HEAD`

Leave out real SIM keys (Ki/OPc), passwords and private keys. Placeholder
values are enough to show the problem.

We aim to acknowledge reports within a week, and will agree a disclosure
date with you once a fix is ready.

## Scope

In scope: the web UI and API, the installer and setup scripts, the Docker
Compose files, and the container images this repository builds.

Report bugs in Open5GS itself to the
[Open5GS project](https://github.com/open5gs/open5gs).

## Known limitations

The web UI and API on port 8080 have **no authentication** yet
([#31](https://github.com/Waveriders-Collective/open5G2GO/issues/31)).
Anyone who can reach that port can view and change subscribers. Keep it on
a network you trust, and do not expose it to the internet.
