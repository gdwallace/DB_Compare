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
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd or ROOT, env=env, check=True)


def ensure_venv() -> Path:
    python = venv_python()
    if not python.exists():
        print("Creating virtualenv...")
        venv.EnvBuilder(with_pip=True).create(VENV)
    return python


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

    print("Installing web packages...")
    run(["npm", "install"], cwd=WEB)

    env = os.environ.copy()
    bin_dir = python.parent
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(VENV)

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
        subprocess.run(["npm", "run", "dev"], cwd=WEB, env=env, check=True)
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
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except KeyboardInterrupt:
        raise SystemExit(130) from None
