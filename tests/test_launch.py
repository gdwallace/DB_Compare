from pathlib import Path

import pytest

from scripts.launch import LaunchError, find_npm, npm_command


def test_find_npm_uses_windows_cmd_shim(tmp_path, monkeypatch):
    home = tmp_path / "nodejs"
    home.mkdir()
    npm = home / "npm.cmd"
    npm.write_text("@echo off\n", encoding="utf-8")
    (home / "node.exe").write_bytes(b"MZ")
    monkeypatch.setattr("scripts.launch._is_windows", lambda: True)
    monkeypatch.setattr(
        "scripts.launch.shutil.which",
        lambda name: str(home / "node.exe") if name == "node.exe" else None,
    )
    monkeypatch.setattr("scripts.launch._where", lambda name: None)
    assert Path(find_npm()) == Path(npm)


def test_find_npm_skips_windowsapps_stub(tmp_path, monkeypatch):
    stub = tmp_path / "Microsoft" / "WindowsApps"
    stub.mkdir(parents=True)
    (stub / "node.exe").write_bytes(b"")
    (stub / "npm.cmd").write_text("", encoding="utf-8")

    home = tmp_path / "nodejs"
    home.mkdir()
    npm = home / "npm.cmd"
    npm.write_text("@echo off\n", encoding="utf-8")
    (home / "node.exe").write_bytes(b"MZ")

    monkeypatch.setattr("scripts.launch._is_windows", lambda: True)
    monkeypatch.setattr(
        "scripts.launch.shutil.which",
        lambda name: str(stub / "node.exe") if name in {"node", "node.exe"} else None,
    )
    monkeypatch.setattr("scripts.launch._where", lambda name: None)
    monkeypatch.setattr("scripts.launch._windows_node_dirs", lambda: [home])
    monkeypatch.setattr("scripts.launch._windows_npm_candidates", lambda: [home / "npm.cmd"])
    assert Path(find_npm()) == Path(npm)


def test_find_npm_missing_explains_windows_path(monkeypatch):
    monkeypatch.setattr("scripts.launch._is_windows", lambda: True)
    monkeypatch.setattr("scripts.launch.shutil.which", lambda name: None)
    monkeypatch.setattr("scripts.launch._where", lambda name: None)
    monkeypatch.setattr("scripts.launch._windows_node_dirs", lambda: [Path("Z:/missing")])
    monkeypatch.setattr("scripts.launch._windows_npm_candidates", lambda: [Path("Z:/missing/npm.cmd")])
    with pytest.raises(LaunchError, match="npm.cmd"):
        find_npm()


def test_npm_command_prefers_node_cli_on_windows(tmp_path, monkeypatch):
    home = tmp_path / "nodejs"
    cli = home / "node_modules" / "npm" / "bin" / "npm-cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node = home / "node.exe"
    node.write_bytes(b"MZ")
    npm = home / "npm.cmd"
    npm.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr("scripts.launch._is_windows", lambda: True)
    command = npm_command(npm, ["install"], node=node)
    assert command == [str(node), str(cli), "install"]


def test_npm_command_uses_cmd_on_windows(tmp_path, monkeypatch):
    npm = tmp_path / "npm.cmd"
    npm.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr("scripts.launch._is_windows", lambda: True)
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    command = npm_command(npm, ["install"])
    assert command[0].lower().endswith("cmd.exe")
    assert command[1:4] == ["/d", "/s", "/c"]
    assert "npm.cmd" in command[4]
    assert "install" in command[4]
