import os
from pathlib import Path

import pytest

from scripts.launch import LaunchError, find_npm


def test_find_npm_uses_windows_cmd_shim(tmp_path, monkeypatch):
    npm = tmp_path / "npm.cmd"
    npm.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr("scripts.launch.shutil.which", lambda name: str(npm) if name == "npm.cmd" else None)
    assert Path(find_npm()) == Path(npm)


def test_find_npm_missing_explains_windows_path(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr("scripts.launch.shutil.which", lambda name: None)
    monkeypatch.setattr("scripts.launch._windows_npm_candidates", lambda: [Path("Z:/missing/npm.cmd")])
    with pytest.raises(LaunchError, match="npm.cmd"):
        find_npm()
