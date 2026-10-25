"""Thin, testable wrapper around the Pixelorama 1.2.x command line interface.

Observed behaviour on Pixelorama 1.2.3 (Windows, Godot 4.7.2 runtime):

* ``Pixelorama.exe [SYSTEM OPTIONS] -- [USER OPTIONS] [FILES]`` is required;
  ``--headless`` alone keeps the app running, so ``--quit`` is mandatory.
* The app writes logs, backups and config into ``user://``, i.e. ``%APPDATA%``
  on Windows. Pointing ``APPDATA`` at a project-local directory keeps the run
  sandbox-friendly and reproducible.
* ``-o`` is applied to the project captured before the file is loaded, so the
  output name comes from the project file name, not from ``-o``.
* Headless export can crash on exit *after* the PNGs are written, so success is
  decided by the produced files, not by the exit code alone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PIXELORAMA_CANDIDATES = (
    r"C:\Users\bow\AppData\Roaming\Orama Interactive\Pixelorama\Pixelorama.exe",
    r"C:\Program Files\Pixelorama\Pixelorama.exe",
    "/usr/bin/pixelorama",
    "/Applications/Pixelorama.app/Contents/MacOS/Pixelorama",
)


def find_pixelorama() -> Path | None:
    override = os.environ.get("ROGALIK_PIXELORAMA")
    if override and Path(override).is_file():
        return Path(override)
    for candidate in DEFAULT_PIXELORAMA_CANDIDATES:
        if Path(candidate).is_file():
            return Path(candidate)
    return None


@dataclass
class ExportResult:
    ok: bool
    command: list[str] = field(default_factory=list)
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    files: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "command": self.command,
            "exit_code": self.exit_code,
            "files": self.files,
            "problems": self.problems,
            "stdout_tail": self.stdout[-1500:],
            "stderr_tail": self.stderr[-1500:],
        }


def _user_dir(workdir: Path) -> Path:
    override = os.environ.get("ROGALIK_PIXELORAMA_USERDIR")
    directory = Path(override) if override else workdir / ".pixelorama-user"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def run_cli(args: list[str], *, workdir: str | Path, timeout: int = 180) -> ExportResult:
    """Run Pixelorama with ``args`` placed after the ``--`` user-argument separator."""
    workdir = Path(workdir)
    exe = find_pixelorama()
    if exe is None:
        return ExportResult(
            ok=False,
            problems=["Pixelorama executable not found; set ROGALIK_PIXELORAMA"],
        )

    command = [
        str(exe),
        "--headless",
        "--quit",
        "--",
        *args,
    ]
    env = dict(os.environ)
    env["APPDATA"] = str(_user_dir(workdir))
    try:
        completed = subprocess.run(
            command,
            cwd=str(workdir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        code: int | None = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - environment specific
        return ExportResult(
            ok=False,
            command=command,
            problems=[f"Pixelorama did not finish within {timeout}s"],
            stdout=(exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
        )

    return ExportResult(ok=True, command=command, exit_code=code, stdout=stdout, stderr=stderr)


def export_project(
    project: str | Path,
    output_dir: str | Path,
    *,
    spritesheet: bool = False,
    scale: int | None = None,
    keep_name: str | None = None,
) -> ExportResult:
    """Export a .pxo project to PNG frame files or a single sprite sheet."""
    project = Path(project).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not project.is_file():
        return ExportResult(ok=False, problems=[f"project not found: {project}"])

    staging = output_dir / ".export_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    staged_project = staging / project.name
    shutil.copy2(project, staged_project)

    args = ["--export"]
    if spritesheet:
        args.append("--spritesheet")
    if scale:
        args.extend(["--scale", str(scale)])
    args.append(str(staged_project))

    result = run_cli(args, workdir=staging)
    result.command = result.command + [f"# project: {project}"]

    produced = sorted(staging.glob("*.png"))
    moved: list[str] = []
    stem = keep_name or project.stem
    for index, png in enumerate(produced, start=1):
        if spritesheet or len(produced) == 1:
            target = output_dir / f"{stem}.png"
        else:
            target = output_dir / f"{stem}_{index:04d}.png"
        if target.exists():
            target.unlink()
        shutil.move(str(png), str(target))
        moved.append(str(target))

    shutil.rmtree(staging, ignore_errors=True)

    result.files = moved
    if not moved:
        result.ok = False
        lowered = result.stderr.lower()
        if "invalid color" in lowered:
            result.problems.append("Pixelorama rejected the project metadata (invalid colour)")
        elif "could not create directory" in lowered:
            result.problems.append("Pixelorama could not write its user:// directory")
        else:
            result.problems.append("Pixelorama produced no PNG output")
    return result
