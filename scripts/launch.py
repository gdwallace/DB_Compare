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


def venv_python() -> Path:
    if os.name == "nt":
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
    if os.name == "nt" and any(ch in part for ch in (" ", "\t")):
        return f'"{part}"'
    return part


def find_npm() -> Path:
    names = ("npm.cmd", "npm.exe", "npm") if os.name == "nt" else ("npm",)
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)

    if os.name == "nt":
        for candidate in _windows_npm_candidates():
            if candidate.is_file():
                return candidate

    raise LaunchError(
        "Node.js / npm was not found.\n"
        "Install Node.js LTS from https://nodejs.org then open a new terminal.\n"
        "On Windows the launcher looks for npm.cmd (not just npm), usually at:\n"
        r"  C:\Program Files\nodejs\npm.cmd"
    )


def _windows_npm_candidates() -> list[Path]:
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    app_data = Path(os.environ.get("APPDATA", ""))
    return [
        program_files / "nodejs" / "npm.cmd",
        program_files_x86 / "nodejs" / "npm.cmd",
        local_app_data / "Programs" / "nodejs" / "npm.cmd",
        local_app_data / "fnm" / "aliases" / "default" / "npm.cmd",
        app_data / "nvm" / "npm.cmd",
        app_data / "npm" / "npm.cmd",
    ]


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

    try:
        npm = find_npm()
    except LaunchError as exc:
        if WEB_DIST.exists():
            print(str(exc))
            print("Falling back to the previously built UI in web/dist.")
            return serve_api_only(python, env)
        raise

    print(f"Using npm at {npm}")
    print("Installing web packages...")
    run([str(npm), "install"], cwd=WEB, env=env)

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
        run([str(npm), "run", "dev"], cwd=WEB, env=env)
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
