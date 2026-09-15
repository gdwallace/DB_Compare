#!/usr/bin/env python3
"""Set up the project (venv, Python/Node deps, .env) and start the API + UI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
WEB = ROOT / "web"
WEB_DIST = WEB / "dist"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


class LaunchError(RuntimeError):
    pass


def _is_windows() -> bool:
    return os.name == "nt"


def venv_python() -> Path:
    if _is_windows():
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(_quote(part) for part in command))
    try:
        subprocess.run(command, cwd=cwd or ROOT, env=env, check=True)
    except FileNotFoundError as exc:
        raise LaunchError(
            f"Could not start {command[0]!r}. Is it installed and on PATH?\n{exc}"
        ) from exc


def _quote(part: str) -> str:
    if _is_windows() and any(ch in part for ch in (" ", "\t")):
        return f'"{part}"'
    return part


def _is_store_alias(path: Path) -> bool:
    """Microsoft Store execution aliases are not a real Node.js install."""
    return any(part.lower() == "windowsapps" for part in Path(path).parts)


def _usable_file(path: Path | None) -> Path | None:
    if path is None:
        return None
    candidate = Path(path)
    if _is_store_alias(candidate) or not candidate.is_file():
        return None
    return candidate


def find_node_home() -> Path | None:
    names = ("node.exe", "node") if _is_windows() else ("node",)
    for name in names:
        found = shutil.which(name)
        usable = _usable_file(Path(found) if found else None)
        if usable:
            return usable.resolve().parent

    if _is_windows():
        for folder in _windows_node_dirs():
            if _usable_file(folder / "node.exe"):
                return folder
        located = _where("node") or _where("node.exe")
        if located:
            return located.parent
    return None


def find_node_exe() -> Path | None:
    home = find_node_home()
    if not home:
        return None
    for name in ("node.exe", "node"):
        found = _usable_file(home / name)
        if found:
            return found
    return None


def find_npm() -> Path:
    home = find_node_home()
    if home:
        found = _npm_next_to_node(home)
        if found:
            return found

    names = ("npm.cmd", "npm.exe", "npm") if _is_windows() else ("npm",)
    for name in names:
        found = shutil.which(name)
        usable = _usable_file(Path(found) if found else None)
        if usable:
            return usable

    if _is_windows():
        located = _where("npm") or _where("npm.cmd")
        if located:
            return located
        for candidate in _windows_npm_candidates():
            usable = _usable_file(candidate)
            if usable:
                return usable

    raise LaunchError(_npm_missing_message())


def _npm_next_to_node(home: Path) -> Path | None:
    names = ("npm.cmd", "npm.exe", "npm") if _is_windows() else ("npm",)
    for name in names:
        found = _usable_file(home / name)
        if found:
            return found
    return _npm_cli_js(home)


def _npm_cli_js(home: Path) -> Path | None:
    return _usable_file(home / "node_modules" / "npm" / "bin" / "npm-cli.js")


def npm_command(npm: Path, args: list[str], *, node: Path | None = None) -> list[str]:
    """Run npm without relying on Windows CreateProcess + PATHEXT.

    Prefer `node.exe npm-cli.js ...` when the official install is present.
    Otherwise wrap `npm.cmd` in cmd.exe — CreateProcess cannot launch .cmd files.
    """
    npm = Path(npm)
    node_path = _usable_file(Path(node) if node else None)
    if node_path:
        cli = _npm_cli_js(node_path.parent)
        if cli is None and npm.suffix.lower() == ".js":
            cli = npm
        if cli is not None:
            return [str(node_path), str(cli), *args]

    if _is_windows() and npm.suffix.lower() in {".cmd", ".bat"}:
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        cmdline = subprocess.list2cmdline([str(npm), *args])
        return [comspec, "/d", "/s", "/c", cmdline]
    return [str(npm), *args]


def run_npm(
    npm: Path,
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    node: Path | None = None,
) -> None:
    env = env.copy()
    home = Path(node).parent if node else Path(npm).parent
    env["PATH"] = str(home) + os.pathsep + env.get("PATH", "")
    run(npm_command(npm, args, node=node), cwd=cwd, env=env)


def _where(name: str) -> Path | None:
    if not _is_windows():
        return None
    try:
        output = subprocess.check_output(
            ["where.exe", name],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    for line in output.splitlines():
        usable = _usable_file(Path(line.strip()))
        if usable:
            return usable
    return None


def _windows_node_dirs() -> list[Path]:
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    app_data = Path(os.environ.get("APPDATA", ""))
    user_profile = Path(os.environ.get("USERPROFILE", ""))
    return [
        program_files / "nodejs",
        program_files_x86 / "nodejs",
        local_app_data / "Programs" / "nodejs",
        local_app_data / "fnm" / "aliases" / "default",
        local_app_data / "Volta" / "bin",
        app_data / "nvm",
        user_profile / "scoop" / "apps" / "nodejs" / "current",
        Path(r"C:\ProgramData\chocolatey\bin"),
    ]


def _windows_npm_candidates() -> list[Path]:
    return [folder / "npm.cmd" for folder in _windows_node_dirs()] + [
        Path(os.environ.get("APPDATA", "")) / "npm" / "npm.cmd",
    ]


def _ensure_windows_node_on_path() -> None:
    if not _is_windows():
        return
    parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    extras: list[str] = []
    for folder in _windows_node_dirs():
        if (folder / "node.exe").is_file() or (folder / "npm.cmd").is_file():
            extras.append(str(folder))
    os.environ["PATH"] = os.pathsep.join(extras + parts)


def _npm_missing_message() -> str:
    return (
        "Node.js / npm was not found by this Python process.\n"
        "1. Install Node.js LTS from https://nodejs.org (not only the Microsoft Store stub).\n"
        "2. Close every terminal and open a new Command Prompt.\n"
        "3. Check with:  where npm   and   npm -v\n"
        r"Expected file: C:\Program Files\nodejs\npm.cmd"
    )


def ensure_venv() -> Path:
    python = venv_python()
    if not python.exists():
        print("Creating virtualenv...")
        venv.EnvBuilder(with_pip=True).create(VENV)
    return python


def serve_api_only(python: Path, env: dict[str, str]) -> int:
    print("Starting API + built UI on http://127.0.0.1:8000")
    run(
        [str(python), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=ROOT,
        env=env,
    )
    return 0


def main() -> int:
    os.chdir(ROOT)
    _ensure_windows_node_on_path()
    python = ensure_venv()

    print("Installing Python packages...")
    run([str(python), "-m", "pip", "install", "-q", "-U", "pip"])
    run([str(python), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements-dev.txt")])

    if not ENV_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print(
            "Created .env from .env.example. "
            "Fill APPIAN_PASSWORD and APPIAN_STAGE_PASSWORD before comparing live servers."
        )

    env = os.environ.copy()
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(VENV)

    node = find_node_exe()
    try:
        npm = find_npm()
    except LaunchError as exc:
        if WEB_DIST.exists():
            print(str(exc))
            print("Falling back to the previously built UI in web/dist.")
            return serve_api_only(python, env)
        raise

    print(f"Using npm at {npm}" + (f" (node {node})" if node else ""))
    print("Installing web packages...")
    run_npm(npm, ["install"], cwd=WEB, env=env, node=node)

    print("Starting API on http://127.0.0.1:8000 and UI on http://127.0.0.1:5173")
    api = subprocess.Popen(
        [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        env=env,
    )
    try:
        run_npm(npm, ["run", "dev"], cwd=WEB, env=env, node=node)
    finally:
        api.terminate()
        try:
            api.wait(timeout=8)
        except subprocess.TimeoutExpired:
            api.kill()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LaunchError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except KeyboardInterrupt:
        raise SystemExit(130) from None
