# agentdocs-doctor proof

Captured 2026-11-09, afternoon America/Los_Angeles (PST).

Fresh-venv install: `pip install .` succeeded and `agentdocs-doctor --version` printed `agentdocs-doctor 0.1.0`.

Tests: 16 passed in 0.04s
Local pytest (same tree): 16 passed.

## version
```
agentdocs-doctor 0.1.0
```

## output on /tmp/ai-tools-proof/agentdocs-doctor
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
info: astryx-missing-mcp: No MCP config in .mcp.json or .cursor/mcp.json points at https://astryx.atmeta.com/mcp. This is optional; the CLI works without MCP. (/tmp/ai-tools-proof/agentdocs-doctor)
info: astryx-missing-grok-skill: This project mentions Astryx but has no skill under .grok/skills. Official Astryx agent setup lists Claude, Cursor, Codex, Hermes, and Muse, not Grok Bot. (/tmp/ai-tools-proof/agentdocs-doctor)
0 error(s), 5 warning(s), 3 info
```

Exit code: 1
