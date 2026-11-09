# Security Policy

This project is a small local command-line tool. It does not phone home and does not require an API key.

## Reporting a vulnerability

Please open a [GitHub issue](https://github.com/perron/agentdocs-doctor/issues) and mention that it is a security report. Do not include secrets, tokens, or private file contents in the issue.

If the report includes a working exploit against this tool, describe the impact and a minimal reproduction without pasting live credentials.

## Notes for this tool

agentdocs-doctor is a read-only scan of a project tree. It does not modify files and it does not phone home. It may list path names from the files it reads; do not point it at a tree that contains secrets in markdown if you plan to paste the report into a public issue.

## Supported versions

The `master` branch and the latest tagged release, when one exists, are supported.
