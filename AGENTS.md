# AGENTS.md

This repository is agentdocs-doctor, a small MIT-licensed Python CLI that
checks AGENTS.md, CLAUDE.md, Cursor rules, and agent skill files for dead
paths, missing commands, copy drift, and simple conflicts.

## Layout

- `agentdocs_doctor/cli.py` — discovery, checks, CLI
- `tests/test_agentdocs_doctor.py` — behavior tests
- `README.md` — install, a real quick-start example, limits

## How to work here

1. `pip install -e ".[dev]"` and `python3 -m pytest -q`.
2. Instruction-file discovery lives in `discover_instruction_files` and
   `discover_skills`. Add a new location there, with a test, if a vendor
   documents it.
3. Path extraction must ignore URLs, npm packages, and placeholders such as
   `<path>`.
4. Astryx-specific checks run only when the docs mention Astryx. Exact
   Astryx managed-block markers were not pinned here because they may change;
   do not invent them.
5. Exit codes: `0` clean or info-only, `1` warnings, `2` errors.

## Do not

- Do not publish, force-push, or change repository visibility.
- Do not modify the scanned project.
- Do not claim official Astryx `doctor` compatibility; this is a separate,
  broader check.

## Checks before you finish

```bash
python3 -m pytest -q
agentdocs-doctor --version
```
