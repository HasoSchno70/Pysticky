# Security Policy

*[Deutsch](SECURITY.md) | English*

## Supported Versions

PySticky is currently pre-1.0. Only the current state of `main` is
supported:

| Version | Supported |
| ------- | --------- |
| main    | ✅        |
| older tags/releases | ❌ |

## Reporting a Vulnerability

Please do **not** report security vulnerabilities via a public issue.

Instead, use GitHub's private vulnerability reporting:
[Security → Report a vulnerability](https://github.com/HasoSchno70/Pysticky/security/advisories/new)
(the "Security" tab on the repository, if the link doesn't work directly).

Please include, if possible:
- Affected version/commit
- Steps to reproduce
- Potential impact (e.g. code execution, data loss, denial of service)

## What to Expect

- Acknowledgment once the report has been reviewed
- An assessment of whether and how the issue will be fixed
- Credit as the reporter in the fix (commit/release notes), if desired

PySticky is a local desktop application with no server backend and no
network communication involving user data. The most relevant attack
surface is reading file formats (`.pxs`, OXS/XSD/PAT, image import) —
reports of crashes or unexpected behavior when opening crafted files are
especially welcome.
