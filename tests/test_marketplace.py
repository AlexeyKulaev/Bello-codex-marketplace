from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_two_clients_share_one_plugin_and_preserve_marketplace_identity():
    codex = read_json(".agents/plugins/marketplace.json")
    claude = read_json(".claude-plugin/marketplace.json")
    assert codex["name"] == claude["name"] == "bello-marketplace"
    assert codex["interface"]["displayName"] == "Bello Plugins"
    assert len(codex["plugins"]) == len(claude["plugins"]) == 1
    assert codex["plugins"][0] == {
        "name": "bello", "source": {"source": "local", "path": "./plugins/bello"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }
    assert claude["plugins"][0] == {"name": "bello", "source": "./plugins/bello"}
    assert claude["owner"]["name"]


def test_codex_manifest_shape_and_relative_paths():
    manifest = read_json("plugins/bello/.codex-plugin/plugin.json")
    assert manifest["name"] == "bello"
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", manifest["version"])
    assert manifest["skills"] == "./skills/"
    assert manifest["description"] and manifest["author"]["name"]
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        assert manifest["interface"][field]
    assert manifest["interface"]["displayName"] == "Bello"
    assert "hooks" not in manifest and "mcpServers" not in manifest and "apps" not in manifest
    assert "[TODO:" not in json.dumps(manifest)


def test_no_legacy_updater_or_duplicate_client_skills():
    plugin = ROOT / "plugins/bello"
    assert {path.name for path in (plugin / "skills").iterdir() if path.is_dir()} == {
        "bello-config-advisor", "bello-delegate",
    }
    assert not list(plugin.rglob("*.sh"))
    assert not list(plugin.rglob(".mcp.json"))
    assert not list(plugin.rglob("hooks.json"))
