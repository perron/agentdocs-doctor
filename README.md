# agentdocs-doctor

Check `AGENTS.md`, `CLAUDE.md`, Cursor rules, Codex and Grok skill files, and
other agent instruction files in a repo for staleness: dead paths, missing
commands, copy drift, and simple conflicts between files.

This is a read-only consistency check. It is not Astryx's own `doctor`
command, and it does not refresh managed doc blocks for you.

## Install

Python 3.10 or later.

```bash
python3 -m pip install .
python3 -m pip install -e ".[dev]"  # optional, for tests
agentdocs-doctor --help
```

Or without installing:

```bash
PYTHONPATH=. python3 -m agentdocs_doctor --help
```

## 30-second quick start

```bash
mkdir -p demo && cd demo
cat > AGENTS.md << 'EOF'
Edit `src/missing.py` when you add a feature.
Run `npm run lint` before you commit.
- Always commit
Use `npx astryx component Button`.
EOF
cat > CLAUDE.md << 'EOF'
- Never commit
EOF
echo '{"name":"demo","scripts":{"test":"echo ok"}}' > package.json

agentdocs-doctor .
```

Real output from that tree (9 Nov 2026, America/Los_Angeles):

```
warning: dead-path: Referenced path 'src/missing.py' does not exist relative to the file or the project root. (AGENTS.md:1)
  excerpt: src/missing.py
warning: missing-script: package.json has no script named 'lint', but the docs tell an agent to run it. (AGENTS.md:2)
  excerpt: npm run lint
warning: unscoped-npx-astryx: Unscoped `npx astryx` can resolve to an unrelated npm package. Prefer `npx @astryxdesign/cli` or a project `npm run astryx` script. (AGENTS.md:4)
  excerpt: npx astryx
warning: rule-conflict: One file says 'always commit' (AGENTS.md:3) and another says 'never commit' (CLAUDE.md:1). (AGENTS.md:3)
  excerpt: commit
warning: astryx-missing-script: Instruction files mention Astryx, but package.json has no `astryx` script. A project script keeps agents from inventing the CLI path. (package.json)
info: astryx-missing-dep: Instruction files mention Astryx, but package.json does not declare @astryxdesign/cli or @astryxdesign/core. (package.json)
info: astryx-missing-mcp: No MCP config in .mcp.json or .cursor/mcp.json points at https://astryx.atmeta.com/mcp. This is optional; the CLI works without MCP.
info: astryx-missing-grok-skill: This project mentions Astryx but has no skill under .grok/skills. Official Astryx agent setup lists Claude, Cursor, Codex, Hermes, and Muse, not Grok Bot.
0 error(s), 5 warning(s), 3 info
```

Exit codes: `0` clean or info-only, `1` warnings, `2` errors.

`--json` prints a structured report. The scan also flags two copies of the
same skill name that have drifted apart across `.claude/skills`, `.grok/skills`,
and the other usual agent folders.

## Use it with your agent

You can point a coding agent at this repository and ask it to check a project,
explain a finding, or write a similar small CLI in the same style.

Sample prompt:

```
Use the agentdocs-doctor tool in this repo. Install it in a fresh virtualenv
with `python3 -m pip install .`, run `python3 -m pytest -q`, then run it on
the current project. Summarize dead paths, missing commands, and conflicts
in plain language. Do not edit the scanned files unless I ask, and do not
publish the package. If you want to build a similar tool, match this repo's
layout: a small MIT Python CLI, behavior tests, honest limits in the
README, and no secrets.
```

## How you can help

- Send a tiny repo that produced a false positive (for example a path that
  exists but was flagged, or an `https://` link treated as a file).
- Add a test for a documented instruction-file location we do not discover
  yet, with a link to the vendor docs.
- Improve conflict detection if you have a real "always X" / "never X" pair
  we missed, or a pair we should not have flagged.

See `CONTRIBUTING.md`. Please do not paste secrets from private agent files
into issues.

## Credit

Original tool. Path conventions follow public Agent Skills / Claude Code,
Cursor rules, Grok Build skill folders, and common `AGENTS.md` practice.
Astryx-specific hints follow public CLI / "Working with AI" docs fetched
9 Nov 2026. No third-party source was copied.

## Limits

- Path extraction looks at markdown links and backtick paths. It can miss unusual formatting, and it can flag a path that is created later in a workflow.
- Command checks cover `npm run` / `pnpm run` / `yarn run` script names and Makefile targets. They do not execute the commands.
- Always/never conflicts are a simple line match on the phrase after the word, not a full policy engine.
- Astryx managed-block markers were not pinned to an exact string because that format may change; the tool looks for mentions of Astryx, package scripts, dependencies, MCP config, and a `.grok/skills` folder instead.
- Official Astryx `init --agent` values do not include Grok. The missing Grok skill finding is an info hint, not a claim that Meta ships that path.
- Guidance and default paths were checked on 9 Nov 2026 and may change.

From GitHub you can also install with:

```bash
python3 -m pip install git+https://github.com/perron/agentdocs-doctor.git
```

This package is not published to PyPI.

## License

MIT. See `LICENSE`. Please read `SECURITY.md` before filing a vulnerability report.
