# Contributing to agentdocs-doctor

Thanks for helping. This doctor is a conservative, read-only consistency
check for agent instruction files and skills.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
agentdocs-doctor --help
```

Add a small temporary project in the test for each new check. Please include
a clean case as well as a failing one (for example an `https://` link must
not be reported as a dead path).

## Rules

- Only flag paths and commands you can reasonably verify from the tree
  (`package.json` scripts, Makefile targets, files that exist).
- If a vendor path or marker is unverified, say so and use an info finding
  or a documented limit, not a hard error.
- Skip `node_modules`, virtualenvs, and build directories.

## What not to do

- Do not add network calls or write back to the project.
- Do not copy Astryx-generated agent-doc blocks into this repo.
- Do not change repository visibility or publish to PyPI unless the
  maintainer asks for that exact action.

## Pull requests

Keep the diff small and mention false-positive risks in the PR.
