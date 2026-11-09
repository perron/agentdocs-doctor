"""Check agent instruction files and skills for stale paths, missing commands, and conflicts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

__version__ = "0.1.0"

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".tox",
    "vendor",
    ".mypy_cache",
    ".pytest_cache",
    ".eggs",
}

INSTRUCTION_ROOT_NAMES = {
    "AGENTS.md",
    "Agents.md",
    "AGENT.md",
    "CLAUDE.md",
    "GEMINI.md",
    "HERMES.md",
    ".hermes.md",
    ".cursorrules",
}

SKILL_PARENTS = (
    Path(".claude") / "skills",
    Path(".agents") / "skills",
    Path(".cursor") / "skills",
    Path(".codex") / "skills",
    Path(".grok") / "skills",
    Path(".github") / "skills",
)

PATH_EXTS = (
    ".md",
    ".mdc",
    ".py",
    ".ts",
    ".js",
    ".tsx",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".sh",
    ".bash",
    ".zsh",
    ".css",
    ".html",
    ".rs",
    ".go",
    ".rb",
    ".txt",
    ".svg",
    ".png",
    ".jpg",
)

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
NPM_RUN_RE = re.compile(r"\b(?:npm|pnpm|yarn)\s+run\s+([A-Za-z0-9:_-]+)")
MAKE_RE = re.compile(r"\bmake\s+([A-Za-z0-9:_-]+)")
ASTRYX_MENTION_RE = re.compile(r"\bastryx\b|@astryxdesign/", re.I)
UNSCOPED_NPX_RE = re.compile(r"\bnpx(?:\s+--yes)?\s+astryx\b", re.I)
SCOPED_CLI_RE = re.compile(r"@astryxdesign/cli")
ASTRYX_VER_RE = re.compile(r"@astryxdesign/(cli|core)@([0-9]+\.[0-9]+\.[0-9]+)")
MCP_URL_RE = re.compile(r"https://astryx\.atmeta\.com/mcp")
ALWAYS_RE = re.compile(r"(?im)^(?:\s*[-*]\s*|\s*\d+\.\s*)?always\s+(.+?)(?:\.|$)$")
NEVER_RE = re.compile(r"(?im)^(?:\s*[-*]\s*|\s*\d+\.\s*)?never\s+(.+?)(?:\.|$)$")
PLACEHOLDER_RE = re.compile(r"[<>{}]|^\.\.\.|TODO|FIXME")

OFFICIAL_MCP = "https://astryx.atmeta.com/mcp"


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    path: str
    line: int = 0
    excerpt: str = ""


def tree_hash(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(skill_dir).as_posix()
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def discover_instruction_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for name in INSTRUCTION_ROOT_NAMES:
        path = root / name
        if path.is_file():
            found.append(path)
    claude_nested = root / ".claude" / "CLAUDE.md"
    if claude_nested.is_file():
        found.append(claude_nested)
    rules = root / ".cursor" / "rules"
    if rules.is_dir():
        for path in sorted(rules.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".mdc"}:
                found.append(path)
    copilot = root / ".github" / "copilot-instructions.md"
    if copilot.is_file():
        found.append(copilot)
    return found


def discover_skills(root: Path) -> list[Path]:
    skills: list[Path] = []
    for parent in SKILL_PARENTS:
        folder = root / parent
        if not folder.is_dir():
            continue
        for child in sorted(folder.iterdir()):
            if not child.is_dir() and not child.is_symlink():
                continue
            skill_md = child / "SKILL.md"
            if not skill_md.is_file():
                # case fallback
                for candidate in child.iterdir() if child.is_dir() else []:
                    if candidate.is_file() and candidate.name.lower() == "skill.md":
                        skill_md = candidate
                        break
            if skill_md.is_file():
                skills.append(skill_md)
    return skills


def looks_like_path(value: str) -> bool:
    s = value.strip().strip("\"'")
    if not s or PLACEHOLDER_RE.search(s):
        return False
    if s.startswith(("http://", "https://", "mailto:", "ftp://", "#")):
        return False
    if s.startswith("@") and "/" in s and not s.startswith("./"):
        # npm package, not a file path
        return False
    if s.startswith(("npx ", "npm ", "pnpm ", "yarn ", "git ", "python ", "python3 ", "pip ", "cargo ", "go ", "make ")):
        return False
    # flags or CLI args
    if s.startswith("-"):
        return False
    if " " in s:
        return False
    if s.startswith(("./", "../", ".claude", ".cursor", ".grok", ".agents", ".codex", ".github", ".hermes")):
        return True
    if s.endswith(PATH_EXTS):
        return True
    if "/" in s and not s.endswith("/"):
        return True
    return False


def extract_paths(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    lines = text.splitlines() or [""]
    # Map character offset to line later; easier to search per line plus full-text links.
    for i, line in enumerate(lines, 1):
        for match in MD_LINK_RE.finditer(line):
            target = match.group(1).split()[0] if match.group(1) else ""
            target = target.split("#", 1)[0]
            if looks_like_path(target):
                hits.append((i, target))
        for match in BACKTICK_RE.finditer(line):
            inner = match.group(1).strip()
            # strip trailing punctuation often left in prose
            inner = inner.rstrip(".,;:)")
            if looks_like_path(inner):
                hits.append((i, inner))
    return hits


def path_exists(root: Path, source: Path, raw: str) -> bool:
    candidate = Path(raw)
    options = []
    if candidate.is_absolute():
        options.append(candidate)
    else:
        options.append((source.parent / candidate))
        options.append(root / candidate)
    for option in options:
        try:
            if option.exists():
                return True
        except OSError:
            continue
    return False


def load_package_scripts(root: Path) -> dict:
    package = root / "package.json"
    if not package.is_file():
        return {}
    try:
        data = json.loads(package.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"__invalid__": True}
    if not isinstance(data, dict):
        return {"__invalid__": True}
    scripts = data.get("scripts") or {}
    deps = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        block = data.get(key) or {}
        if isinstance(block, dict):
            deps.update(block)
    return {"scripts": scripts if isinstance(scripts, dict) else {}, "deps": deps, "raw": data}


def makefile_targets(root: Path) -> set[str]:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return set()
    targets: set[str] = set()
    for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("\t") or line.startswith(" ") or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("."):
            name = line.split(":", 1)[0].strip()
            if name and " " not in name:
                targets.add(name)
    return targets


def normalize_rule(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower().rstrip(".")


def extract_mcp_files(root: Path) -> list[Path]:
    files = []
    for rel in (".mcp.json", Path(".cursor") / "mcp.json", Path(".vscode") / "mcp.json"):
        path = root / rel
        if path.is_file():
            files.append(path)
    return files


def scan(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    instruction = discover_instruction_files(root)
    skills = discover_skills(root)
    docs = instruction + skills
    package = load_package_scripts(root)
    make_targets = makefile_targets(root)

    if not docs:
        findings.append(
            Finding(
                "info",
                "no-instruction-files",
                "No AGENTS.md, CLAUDE.md, Cursor rules, or agent skill files were found in this project.",
                str(root),
            )
        )
        return findings

    # Dead paths and missing commands
    for file in docs:
        text = file.read_text(encoding="utf-8", errors="replace")
        rel = str(file.relative_to(root)) if file.is_relative_to(root) else str(file)
        for lineno, raw in extract_paths(text):
            if not path_exists(root, file, raw):
                findings.append(
                    Finding(
                        "warning",
                        "dead-path",
                        f"Referenced path {raw!r} does not exist relative to the file or the project root.",
                        rel,
                        lineno,
                        raw,
                    )
                )
        for match in NPM_RUN_RE.finditer(text):
            script = match.group(1)
            lineno = text[: match.start()].count("\n") + 1
            if not package or package.get("__invalid__"):
                findings.append(
                    Finding(
                        "warning",
                        "missing-package-json",
                        f"Command `{'npm run ' + script}` is mentioned, but package.json is missing or invalid.",
                        rel,
                        lineno,
                        match.group(0),
                    )
                )
            elif script not in package.get("scripts", {}):
                findings.append(
                    Finding(
                        "warning",
                        "missing-script",
                        f"package.json has no script named {script!r}, but the docs tell an agent to run it.",
                        rel,
                        lineno,
                        match.group(0),
                    )
                )
        for match in MAKE_RE.finditer(text):
            target = match.group(1)
            if target in {"-C", "-f", "-j", "-k", "-n", "-s"}:
                continue
            lineno = text[: match.start()].count("\n") + 1
            if not (root / "Makefile").is_file():
                findings.append(
                    Finding(
                        "warning",
                        "missing-makefile",
                        f"Command `make {target}` is mentioned, but there is no Makefile.",
                        rel,
                        lineno,
                        match.group(0),
                    )
                )
            elif target not in make_targets:
                findings.append(
                    Finding(
                        "warning",
                        "missing-make-target",
                        f"Makefile has no target named {target!r}.",
                        rel,
                        lineno,
                        match.group(0),
                    )
                )
        for match in UNSCOPED_NPX_RE.finditer(text):
            lineno = text[: match.start()].count("\n") + 1
            findings.append(
                Finding(
                    "warning",
                    "unscoped-npx-astryx",
                    "Unscoped `npx astryx` can resolve to an unrelated npm package. Prefer `npx @astryxdesign/cli` or a project `npm run astryx` script.",
                    rel,
                    lineno,
                    match.group(0),
                )
            )

    # Skill name drift across agent folders
    by_name: dict[str, list[tuple[str, str, Path]]] = {}
    for skill_md in skills:
        skill_dir = skill_md.parent
        rel = str(skill_dir.relative_to(root))
        by_name.setdefault(skill_dir.name, []).append((tree_hash(skill_dir), rel, skill_dir))
    for name, copies in by_name.items():
        hashes = {item[0] for item in copies}
        if len(hashes) > 1:
            paths = ", ".join(item[1] for item in copies)
            findings.append(
                Finding(
                    "warning",
                    "skill-drift",
                    f"Skill {name!r} has different content in more than one agent folder: {paths}.",
                    str(root),
                )
            )

    # always vs never conflicts across files
    always_map: dict[str, list[tuple[str, int]]] = {}
    never_map: dict[str, list[tuple[str, int]]] = {}
    versions: dict[str, list[tuple[str, str]]] = {}
    mentions_astryx = False
    for file in docs:
        text = file.read_text(encoding="utf-8", errors="replace")
        rel = str(file.relative_to(root)) if file.is_relative_to(root) else str(file)
        if ASTRYX_MENTION_RE.search(text):
            mentions_astryx = True
        for match in ALWAYS_RE.finditer(text):
            always_map.setdefault(normalize_rule(match.group(1)), []).append(
                (rel, text[: match.start()].count("\n") + 1)
            )
        for match in NEVER_RE.finditer(text):
            never_map.setdefault(normalize_rule(match.group(1)), []).append(
                (rel, text[: match.start()].count("\n") + 1)
            )
        for match in ASTRYX_VER_RE.finditer(text):
            versions.setdefault(match.group(1), []).append((match.group(2), rel))

    for phrase, always_hits in always_map.items():
        if phrase in never_map:
            a = always_hits[0]
            b = never_map[phrase][0]
            findings.append(
                Finding(
                    "warning",
                    "rule-conflict",
                    f"One file says 'always {phrase}' ({a[0]}:{a[1]}) and another says 'never {phrase}' ({b[0]}:{b[1]}).",
                    a[0],
                    a[1],
                    phrase,
                )
            )

    # package.json version vs docs
    if package and not package.get("__invalid__"):
        deps = package.get("deps") or {}
        for pkg, entries in versions.items():
            key = f"@astryxdesign/{pkg}"
            declared = deps.get(key)
            if not declared:
                continue
            declared_ver = re.sub(r"^[~^]=?", "", str(declared)).split()[0]
            for ver, rel in entries:
                if declared_ver and ver != declared_ver and not declared_ver.startswith(ver):
                    # if declared is ^0.7.11 and docs say 0.7.11, that is fine
                    stripped = declared_ver.lstrip("^~")
                    if ver != stripped:
                        findings.append(
                            Finding(
                                "warning",
                                "version-mismatch",
                                f"Docs in {rel} mention @astryxdesign/{pkg}@{ver}, but package.json has {declared}.",
                                rel,
                            )
                        )

    # Astryx-specific freshness, only if the project mentions Astryx
    if mentions_astryx:
        scripts = (package or {}).get("scripts") or {}
        deps = (package or {}).get("deps") or {}
        if not package or package.get("__invalid__"):
            findings.append(
                Finding(
                    "warning",
                    "astryx-no-package",
                    "Instruction files mention Astryx, but this project has no usable package.json.",
                    str(root / "package.json") if (root / "package.json").exists() else str(root),
                )
            )
        else:
            if "astryx" not in scripts:
                findings.append(
                    Finding(
                        "warning",
                        "astryx-missing-script",
                        "Instruction files mention Astryx, but package.json has no `astryx` script. A project script keeps agents from inventing the CLI path.",
                        "package.json",
                    )
                )
            if "@astryxdesign/cli" not in deps and "@astryxdesign/core" not in deps:
                findings.append(
                    Finding(
                        "info",
                        "astryx-missing-dep",
                        "Instruction files mention Astryx, but package.json does not declare @astryxdesign/cli or @astryxdesign/core.",
                        "package.json",
                    )
                )
        mcp_files = extract_mcp_files(root)
        has_official_mcp = False
        for mcp in mcp_files:
            text = mcp.read_text(encoding="utf-8", errors="replace")
            if MCP_URL_RE.search(text) or "astryx.atmeta.com/mcp" in text:
                has_official_mcp = True
        if not has_official_mcp:
            findings.append(
                Finding(
                    "info",
                    "astryx-missing-mcp",
                    f"No MCP config in .mcp.json or .cursor/mcp.json points at {OFFICIAL_MCP}. This is optional; the CLI works without MCP.",
                    str(root),
                )
            )
        grok_skills = root / ".grok" / "skills"
        has_grok = grok_skills.is_dir() and any(grok_skills.iterdir())
        if not has_grok:
            findings.append(
                Finding(
                    "info",
                    "astryx-missing-grok-skill",
                    "This project mentions Astryx but has no skill under .grok/skills. Official Astryx agent setup lists Claude, Cursor, Codex, Hermes, and Muse, not Grok Bot.",
                    str(root),
                )
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentdocs-doctor",
        description=(
            "Read-only check of AGENTS.md, CLAUDE.md, Cursor rules, Codex and "
            "Grok skill files for dead paths, missing commands, and conflicts."
        ),
    )
    parser.add_argument("path", nargs="?", default=".", help="project root (default: current directory)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--version", action="version", version=f"agentdocs-doctor {__version__}")
    args = parser.parse_args(argv)
    target = Path(args.path)
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 1
    if not target.is_dir():
        # Allow passing a file by using its parent as the project, but still
        # scan the whole project root if this looks like a repo file.
        target = target.parent if target.is_file() else target
    findings = scan(target)
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    infos = sum(1 for f in findings if f.severity == "info")
    if args.json:
        print(
            json.dumps(
                {
                    "findings": [asdict(f) for f in findings],
                    "errors": errors,
                    "warnings": warnings,
                    "infos": infos,
                },
                indent=2,
            )
        )
    else:
        if not findings:
            print(f"ok: agent docs look consistent in {target}")
        else:
            for f in findings:
                loc = f"{f.path}:{f.line}" if f.line else f.path
                print(f"{f.severity}: {f.code}: {f.message} ({loc})")
                if f.excerpt:
                    print(f"  excerpt: {f.excerpt}")
            print(f"{errors} error(s), {warnings} warning(s), {infos} info")
    if errors:
        return 2
    if warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
