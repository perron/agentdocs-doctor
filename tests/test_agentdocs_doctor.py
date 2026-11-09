from __future__ import annotations

import json
from pathlib import Path

import pytest

import agentdocs_doctor.cli as ad


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def codes(root: Path) -> set[str]:
    return {f.code for f in ad.scan(root)}


def test_help_and_version():
    with pytest.raises(SystemExit) as exc:
        ad.main(["--help"])
    assert exc.value.code == 0
    with pytest.raises(SystemExit) as exc:
        ad.main(["--version"])
    assert exc.value.code == 0


def test_clean_repo(tmp_path, capsys):
    write(tmp_path / "src" / "app.py", "print('ok')\n")
    write(tmp_path / "AGENTS.md", "Edit `src/app.py` when adding a feature.\n")
    assert ad.main([str(tmp_path)]) == 0
    assert "ok:" in capsys.readouterr().out


def test_dead_path(tmp_path, capsys):
    write(tmp_path / "AGENTS.md", "See `src/missing.py` and [docs](docs/guide.md).\n")
    assert ad.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "dead-path" in out
    assert "src/missing.py" in out


def test_http_link_is_not_a_dead_path(tmp_path):
    write(tmp_path / "AGENTS.md", "Read [the guide](https://example.com/docs/cli).\n")
    assert "dead-path" not in codes(tmp_path)


def test_missing_npm_script(tmp_path, capsys):
    write(tmp_path / "package.json", '{"name": "demo", "scripts": {"test": "echo ok"}}\n')
    write(tmp_path / "AGENTS.md", "Run `npm run lint` before you commit.\n")
    assert ad.main([str(tmp_path)]) == 1
    assert "missing-script" in capsys.readouterr().out


def test_present_npm_script_is_clean(tmp_path):
    write(tmp_path / "package.json", '{"name": "demo", "scripts": {"lint": "echo ok"}}\n')
    write(tmp_path / "AGENTS.md", "Run `npm run lint` before you commit.\n")
    assert "missing-script" not in codes(tmp_path)


def test_rule_conflict(tmp_path, capsys):
    write(tmp_path / "AGENTS.md", "- Always commit\n")
    write(tmp_path / "CLAUDE.md", "- Never commit\n")
    assert ad.main([str(tmp_path)]) == 1
    assert "rule-conflict" in capsys.readouterr().out


def test_unscoped_npx_astryx(tmp_path, capsys):
    write(tmp_path / "AGENTS.md", "Run `npx astryx component Button`.\n")
    write(
        tmp_path / "package.json",
        json.dumps({"name": "demo", "scripts": {}, "dependencies": {"@astryxdesign/cli": "0.7.11"}}),
    )
    assert ad.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "unscoped-npx-astryx" in out


def test_astryx_missing_script(tmp_path):
    write(tmp_path / "AGENTS.md", "Use the Astryx CLI to look up components.\n")
    write(tmp_path / "package.json", '{"name": "demo", "dependencies": {"@astryxdesign/cli": "0.7.11"}}\n')
    found = codes(tmp_path)
    assert "astryx-missing-script" in found


def test_astryx_script_present(tmp_path):
    write(tmp_path / "AGENTS.md", "Use `npx @astryxdesign/cli component Button`.\n")
    write(
        tmp_path / "package.json",
        json.dumps(
            {
                "name": "demo",
                "scripts": {"astryx": "node node_modules/@astryxdesign/cli/clients/cli/bin/astryx.mjs"},
                "devDependencies": {"@astryxdesign/cli": "0.7.11"},
            }
        ),
    )
    write(
        tmp_path / ".mcp.json",
        json.dumps({"mcpServers": {"astryx": {"url": "https://astryx.atmeta.com/mcp"}}}),
    )
    write(
        tmp_path / ".grok" / "skills" / "grok-astryx" / "SKILL.md",
        "---\nname: grok-astryx\ndescription: Build UI with Astryx when the user asks.\n---\nUse the CLI.\n",
    )
    found = codes(tmp_path)
    assert "astryx-missing-script" not in found
    assert "astryx-missing-mcp" not in found
    assert "astryx-missing-grok-skill" not in found
    assert "unscoped-npx-astryx" not in found


def test_skill_drift(tmp_path, capsys):
    write(
        tmp_path / ".claude" / "skills" / "tidy-notes" / "SKILL.md",
        "---\nname: tidy-notes\ndescription: Tidy notes when asked to clean a notes folder.\n---\none\n",
    )
    write(
        tmp_path / ".grok" / "skills" / "tidy-notes" / "SKILL.md",
        "---\nname: tidy-notes\ndescription: Tidy notes when asked to clean a notes folder.\n---\ntwo\n",
    )
    write(tmp_path / "AGENTS.md", "Skills live in the agent folders.\n")
    assert ad.main([str(tmp_path)]) == 1
    assert "skill-drift" in capsys.readouterr().out


def test_json_and_no_docs(tmp_path, capsys):
    assert ad.main([str(tmp_path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["infos"] >= 1
    assert any(f["code"] == "no-instruction-files" for f in data["findings"])


def test_missing_path(tmp_path, capsys):
    assert ad.main([str(tmp_path / "nope")]) == 1
    assert "path not found" in capsys.readouterr().err


def test_skips_node_modules(tmp_path):
    write(tmp_path / "AGENTS.md", "Use `src/app.py`.\n")
    write(tmp_path / "src" / "app.py", "print('ok')\n")
    write(tmp_path / "node_modules" / "pkg" / "AGENTS.md", "See `does-not-exist.py`.\n")
    assert "dead-path" not in codes(tmp_path)


def test_unicode_path(tmp_path):
    write(tmp_path / "docs" / "ガイド.md", "# ガイド\n")
    write(tmp_path / "AGENTS.md", "Read `docs/ガイド.md` before you start.\n")
    assert "dead-path" not in codes(tmp_path)


def test_looks_like_path_rejects_packages_and_commands():
    assert ad.looks_like_path("src/app.py")
    assert not ad.looks_like_path("https://astryx.atmeta.com/docs/cli")
    assert not ad.looks_like_path("@astryxdesign/cli")
    assert not ad.looks_like_path("npm run astryx")
    assert not ad.looks_like_path("<path>")
