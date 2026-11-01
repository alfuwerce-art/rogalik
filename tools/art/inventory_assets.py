#!/usr/bin/env python3
"""Rogalik D31 asset inventory.

Read-only. Walks the art zones of the working tree, measures every file
(SHA-256, PNG dimensions, alpha masks), resolves whether Godot actually
references it, and records the Git/push state. Writes a machine-readable
JSON report and a human-readable Markdown summary.

It never moves, renames, deletes or rewrites repository files.

Usage:
    python tools/art/inventory_assets.py
    python tools/art/inventory_assets.py --remote origin/stage3-hero
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Zones of the repository that hold art (or art metadata).
ZONES = {
    "library": "assets/references/gpt_asset_library",
    "archives": "assets/archives",
    "godot_prototype": "game/prototype/art",
    "godot_experiments": "game/experiments",
    "references": "assets/references",
}

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
TEXT_EXT_FOR_SCAN = {".tscn", ".tres", ".gd", ".json", ".import", ".godot"}

# Repository-relative parts excluded from the walk:
# nested checkouts, caches, and Godot's own import cache (gitignored, never an asset).
EXCLUDE_PARTS = (
    "tools/godot-mcp",
    ".cache/",
    "node_modules",
    "__pycache__",
    "/.git/",
    "/.godot/",
    ".TMP",
)


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    return out.stdout


def git_lines(*args: str) -> list[str]:
    return [line for line in git(*args, "-z").split("\0") if line]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_facts(path: Path) -> dict:
    """Dimensions, colour mode and alpha statistics of a PNG."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is part of the runtime
        return {"error": "PIL_UNAVAILABLE"}

    try:
        with Image.open(path) as img:
            img.load()
            facts: dict = {
                "size_px": [img.width, img.height],
                "mode": img.mode,
            }
            has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
            facts["has_alpha_channel"] = has_alpha
            if has_alpha:
                alpha = img.convert("RGBA").getchannel("A")
                gt0 = alpha.point(lambda v: 255 if v > 0 else 0).getbbox()
                ge16 = alpha.point(lambda v: 255 if v >= 16 else 0).getbbox()
                facts["bbox_alpha_gt0"] = list(gt0) if gt0 else None
                facts["bbox_alpha_ge16"] = list(ge16) if ge16 else None
                hist = alpha.histogram()
                facts["alpha_zero_px"] = hist[0]
                facts["alpha_full_px"] = hist[255]
                facts["alpha_partial_px"] = sum(hist[1:255])
                if ge16:
                    facts["bbox_agent_ge16_size"] = [ge16[2] - ge16[0], ge16[3] - ge16[1]]
            if img.mode in ("RGB", "RGBA"):
                colors = img.convert("RGBA").getcolors(maxcolors=200000)
                facts["unique_colors"] = len(colors) if colors else "ABOVE_200000"
            return facts
    except Exception as exc:  # noqa: BLE001 - report, never crash the inventory
        return {"error": f"{type(exc).__name__}: {exc}"}


def zone_of(rel: str) -> str | None:
    """Most specific zone for a repository-relative path."""
    for name in ("library", "archives", "godot_prototype", "godot_experiments", "references"):
        root = ZONES[name]
        if rel == root or rel.startswith(root + "/"):
            return name
    return None


def walk_zone(root: Path) -> list[Path]:
    if not root.exists():
        return []
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = "/" + path.relative_to(REPO).as_posix()
        if any(part in rel for part in EXCLUDE_PARTS):
            continue
        found.append(path)
    return sorted(found)


def build_text_corpus() -> dict[str, str]:
    """All Godot-facing text files, keyed by repository-relative path.

    `.import` files are deliberately excluded: each one contains the `res://`
    path of its own PNG, so counting them would make every PNG look referenced.
    """
    corpus: dict[str, str] = {}
    root = REPO / "game"
    if not root.exists():
        return corpus
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_EXT_FOR_SCAN:
            continue
        if path.suffix == ".import":
            continue
        rel = "/" + path.relative_to(REPO).as_posix()
        if any(part in rel for part in EXCLUDE_PARTS):
            continue
        try:
            corpus[path.relative_to(REPO).as_posix()] = path.read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            continue
    return corpus


def godot_refs(rel: str, corpus: dict[str, str]) -> list[dict]:
    """Which Godot-facing files reference this art file.

    `res://` paths are declared relative to the Godot project root, which is
    either `game/prototype` or `game/experiments/<project>`, so the declared
    form is `art/<sub>/<name>.png`. Several scripts compose the path at runtime
    from a directory constant (`const ART := "res://art/calibration/"`), so a
    bare-filename match is reported as a distinct, weaker kind of evidence.
    """
    name = Path(rel).name
    project_rel = "art/" + rel.split("/art/", 1)[-1] if "/art/" in rel else None
    hits: list[dict] = []
    for file_rel, text in corpus.items():
        if project_rel and project_rel in text:
            hits.append({"file": file_rel, "how": "project_relative_path"})
        elif name in text:
            hits.append({"file": file_rel, "how": "filename"})
    return hits


def classify(zone: str, refs: list[dict]) -> tuple[str, str]:
    """Return (decision, reason) per D31. Nothing is ever moved automatically."""
    if zone == "library":
        return "KEEP_IN_LIBRARY", "D30/D31 machine catalog: source of truth for GPT art metadata."
    if zone == "archives":
        return (
            "KEEP_ARCHIVE_UNTOUCHED",
            "Owner ZIP archive; D31 forbids migration or rewriting without a direct decision.",
        )
    if zone == "references":
        return (
            "KEEP_IN_PLACE_HISTORICAL",
            "Historical owner-provided reference; D31 forbids automatic migration.",
        )
    if refs:
        return (
            "KEEP_IN_PLACE_USED_BY_GODOT",
            "Referenced from Godot scripts/scenes; moving it would risk the playable build.",
        )
    return (
        "KEEP_IN_PLACE_UNREFERENCED",
        "No Godot reference found, but D31 requires an explicit decision before migrating.",
    )


def manifest_check() -> dict:
    manifest = REPO / "docs" / "REFERENCE_FILE_MANIFEST.sha256"
    if not manifest.exists():
        return {"status": "MANIFEST_ABSENT"}
    entries, missing, mismatched, ok = [], [], [], 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, rel = line.partition("  ")
        path = REPO / rel
        if not path.exists():
            missing.append(rel)
            entries.append({"path": rel, "expected": digest, "actual": None, "state": "ABSENT"})
            continue
        actual = sha256_file(path)
        state = "MATCH"
        if actual == digest:
            ok += 1
        else:
            mismatched.append(rel)
            state = "MISMATCH"
        entries.append({"path": rel, "expected": digest, "actual": actual, "state": state})
    return {
        "status": "OK" if not missing and not mismatched else "ATTENTION",
        "entries_total": len(entries),
        "match": ok,
        "absent": missing,
        "mismatch": mismatched,
        "detail": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", default="origin/stage3-hero")
    parser.add_argument("--json-out", default="reports/d31_asset_inventory.json")
    parser.add_argument("--md-out", default="reports/d31_asset_inventory.md")
    args = parser.parse_args()

    tracked = set(git_lines("ls-files"))
    pushed = set(git_lines("ls-tree", "-r", "--name-only", args.remote))
    corpus = build_text_corpus()

    records: list[dict] = []
    seen: set[str] = set()
    for zone, root_rel in ZONES.items():
        for path in walk_zone(REPO / root_rel):
            rel = path.relative_to(REPO).as_posix()
            if rel in seen:
                continue
            if zone_of(rel) != zone:
                continue  # keep the most specific zone only
            seen.add(rel)
            suffix = path.suffix.lower()
            record: dict = {
                "path": rel,
                "zone": zone,
                "kind": suffix.lstrip(".") or "no_ext",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "tracked": rel in tracked,
                "in_remote_branch": rel in pushed,
            }
            if suffix in IMAGE_EXT:
                record["png"] = png_facts(path)
                refs = godot_refs(rel, corpus) if zone.startswith("godot") else []
                record["godot_refs"] = refs
                record["decision"], record["decision_reason"] = classify(zone, refs)
            elif suffix == ".import":
                target = REPO / rel[: -len(".import")]
                record["import_target_exists"] = target.exists()
                record["decision"] = "KEEP_IN_PLACE"
                record["decision_reason"] = (
                    "Godot import metadata whose PNG exists."
                    if target.exists()
                    else "ORPHAN: import metadata without its PNG (pre-existing state)."
                )
            else:
                record["decision"] = "KEEP_IN_PLACE"
                record["decision_reason"] = "Non-image file inside an art zone."
            records.append(record)

    by_zone: dict[str, int] = {}
    for rec in records:
        by_zone[rec["zone"]] = by_zone.get(rec["zone"], 0) + 1

    image_kinds = {ext.lstrip(".") for ext in IMAGE_EXT}
    images = [r for r in records if r["kind"] in image_kinds]
    orphan_imports = [r["path"] for r in records if r.get("import_target_exists") is False]
    unreferenced_godot = [
        r["path"]
        for r in records
        if r["zone"].startswith("godot") and r["kind"] == "png" and not r.get("godot_refs")
    ]
    untracked = [r["path"] for r in records if not r["tracked"]]
    not_in_remote = [r["path"] for r in records if r["tracked"] and not r["in_remote_branch"]]

    report = {
        "generated_by": "tools/art/inventory_assets.py",
        "task": "D31 local asset library organization",
        "branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "head": git("rev-parse", "HEAD").strip(),
        "remote_ref": args.remote,
        "remote_head": git("rev-parse", args.remote).strip(),
        "zones": ZONES,
        "counts": {"records": len(records), "images": len(images), "by_zone": by_zone},
        "manifest": manifest_check(),
        "findings": {
            "orphan_import_files": orphan_imports,
            "unreferenced_godot_pngs": unreferenced_godot,
            "untracked_art_files": untracked,
            "tracked_not_in_remote": not_in_remote,
        },
        "files": records,
    }

    json_path = REPO / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# D31 — инвентаризация игровых ассетов, спрайтов и текстур",
        "",
        "Сгенерировано: `tools/art/inventory_assets.py` (только чтение, ничего не перемещает).",
        "",
        f"- ветка: `{report['branch']}`, HEAD `{report['head']}`",
        f"- удалённая ветка: `{args.remote}` = `{report['remote_head']}`",
        "",
        "## Сводка",
        "",
        f"- учтено файлов: **{len(records)}**",
        f"- изображений: **{len(images)}**",
        "- по зонам: " + ", ".join(f"`{k}` — {v}" for k, v in sorted(by_zone.items())),
        f"- `.import` без своего PNG: **{len(orphan_imports)}**",
        f"- PNG в Godot-зонах без ссылок из проекта: **{len(unreferenced_godot)}**",
        f"- артефакты вне Git: **{len(untracked)}**",
        "",
        "## Целостность оригиналов (`docs/REFERENCE_FILE_MANIFEST.sha256`)",
        "",
        f"- статус: **{report['manifest']['status']}**",
        f"- записей: {report['manifest']['entries_total']}, совпало: {report['manifest']['match']}",
        f"- отсутствуют: {report['manifest']['absent'] or 'нет'}",
        f"- расхождение SHA: {report['manifest']['mismatch'] or 'нет'}",
        "",
        "## Файлы",
        "",
        "| Путь | Зона | Тип | Байт | SHA-256 | В Git | В origin | Решение |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for rec in records:
        lines.append(
            "| `{path}` | {zone} | {kind} | {bytes} | `{sha}` | {tracked} | {remote} | {decision} |".format(
                path=rec["path"],
                zone=rec["zone"],
                kind=rec["kind"],
                bytes=rec["bytes"],
                sha=rec["sha256"][:16] + "…",
                tracked="да" if rec["tracked"] else "**нет**",
                remote="да" if rec["in_remote_branch"] else "**нет**",
                decision=rec["decision"],
            )
        )
    lines.append("")
    lines.append("Полные данные (SHA-256, размеры, alpha-маски, ссылки Godot) — в JSON рядом.")
    (REPO / args.md_out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        "records={} images={} zones={}".format(len(records), len(images), by_zone)
    )
    print(
        "orphan_imports={} unreferenced_godot_pngs={} untracked={}".format(
            len(orphan_imports), len(unreferenced_godot), len(untracked)
        )
    )
    print(
        "manifest={} match={}/{}".format(
            report["manifest"]["status"],
            report["manifest"]["match"],
            report["manifest"]["entries_total"],
        )
    )
    print(f"wrote {args.json_out} and {args.md_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
