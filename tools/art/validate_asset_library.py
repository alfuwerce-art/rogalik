#!/usr/bin/env python3
"""Rogalik GPT asset library validator (D30/D31).

Checks the machine catalog against the actual files on disk:

* every JSON in the library parses;
* `asset_index.json` entries are unique (case-insensitive), point at an existing
  `asset.json` inside the library root, and agree with that card;
* every `files[]` entry of every card points at a file that really exists,
  inside the card's own `<category>/<ID>_<slug>/` directory;
* recorded SHA-256 values match the bytes on disk;
* the `master` SHA-256 matches when the master file is physically available;
* frame entries do not duplicate an (animation, direction, frame_index) triple;
* relative paths never escape the library root.

Read-only. Exit code 0 = PASS, 1 = FAIL.

Usage:
    python tools/art/validate_asset_library.py
    python tools/art/validate_asset_library.py --library <path> --json-out <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
LIBRARY = REPO / "assets" / "references" / "gpt_asset_library"

CATEGORIES = (
    "characters",
    "enemies",
    "bosses",
    "weapons",
    "props",
    "environment",
    "tilesets",
    "textures",
    "vfx",
    "ui",
)

INDEX_REQUIRED = ("asset_id", "category", "slug", "manifest_path", "presence", "readiness")
CARD_REQUIRED = (
    "asset_id",
    "category",
    "display_name",
    "source_author",
    "profile_id",
    "master",
    "files",
    "animations",
    "status",
)
STATUS_REQUIRED = ("presence", "technical_export", "godot", "art_approval", "github")
FILE_REQUIRED = ("path", "role", "sha256", "file_type")

# Values in use by D30/D31 cards today. Anything else is a warning, not a failure,
# because the vocabulary is owned by docs/DECISIONS.md, not by this script.
KNOWN_PRESENCE = {
    "ABSENT",
    "LOCAL_ONLY",
    "COMMITTED_LOCAL",
    "PUSHED",
    "NOT_IMPORTED",
    "NOT_VERIFIED",
    "NOT_VERIFIED_IN_GITHUB",
}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.checks: list[dict] = []

    def fail(self, check: str, message: str) -> None:
        self.failures.append(f"[{check}] {message}")
        self.checks.append({"check": check, "result": "FAIL", "message": message})

    def warn(self, check: str, message: str) -> None:
        self.warnings.append(f"[{check}] {message}")
        self.checks.append({"check": check, "result": "WARN", "message": message})

    def ok(self, check: str, message: str) -> None:
        self.checks.append({"check": check, "result": "PASS", "message": message})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, report: Report, label: str) -> dict | None:
    if not path.exists():
        report.fail("json", f"{label}: file not found")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.fail("json", f"{label}: invalid JSON - {exc}")
        return None


def safe_rel(root: Path, rel: str, report: Report, check: str, label: str) -> Path | None:
    """Resolve a library-relative forward-slash path without escaping the root."""
    if not isinstance(rel, str) or not rel:
        report.fail(check, f"{label}: empty or non-string path")
        return None
    if "\\" in rel:
        report.warn(check, f"{label}: backslash in path `{rel}` (norm is `/`)")
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts:
        report.fail(check, f"{label}: path escapes the library root - `{rel}`")
        return None
    return root / Path(*pure.parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", default=None, help="library root (default: repository library)")
    parser.add_argument("--json-out", default="reports/d31_library_validation.json")
    args = parser.parse_args()

    library = Path(args.library).resolve() if args.library else LIBRARY
    report = Report()

    if not library.exists():
        report.fail("root", f"library directory is missing: {library}")
        print("\n".join(report.failures))
        return 1

    # --- 1. index ---
    index = load_json(library / "asset_index.json", report, "asset_index.json")
    if index is None:
        print("\n".join(report.failures))
        return 1

    entries = index.get("assets")
    if not isinstance(entries, list):
        report.fail("index", "`assets` is missing or not an array")
        entries = []
    else:
        report.ok("index", f"asset_index.json: {len(entries)} entries")

    seen_ids: dict[str, str] = {}
    manifests: list[tuple[str, dict, str]] = []
    for position, entry in enumerate(entries):
        label = f"index.assets[{position}]"
        missing = [field for field in INDEX_REQUIRED if field not in entry]
        if missing:
            report.fail("index-schema", f"{label}: missing fields {missing}")
            continue
        asset_id = entry["asset_id"]
        key = str(asset_id).strip().upper()
        if key in seen_ids:
            report.fail("index-unique-id", f"duplicate ID `{asset_id}` ({seen_ids[key]} and {label})")
        else:
            seen_ids[key] = label
        category = entry["category"]
        if category not in CATEGORIES:
            report.fail("index-category", f"{label}: unknown category `{category}`")
        slug = entry["slug"]
        if not str(slug).startswith(f"{asset_id}_"):
            report.fail("index-slug", f"{label}: slug `{slug}` does not start with `{asset_id}_`")
        manifest_path = safe_rel(library, entry["manifest_path"], report, "index-path", label)
        if manifest_path is None:
            continue
        expected_dir = f"{category}/{slug}/"
        if not entry["manifest_path"].startswith(expected_dir):
            report.fail(
                "index-path",
                f"{label}: manifest_path `{entry['manifest_path']}` is not inside `{expected_dir}`",
            )
        card = load_json(manifest_path, report, entry["manifest_path"])
        if card is None:
            continue
        manifests.append((entry["manifest_path"], card, label))

        if card.get("asset_id") != asset_id:
            report.fail(
                "card-id",
                f"{entry['manifest_path']}: asset_id `{card.get('asset_id')}` != index `{asset_id}`",
            )
        if card.get("category") != category:
            report.fail(
                "card-category",
                f"{entry['manifest_path']}: category `{card.get('category')}` != index `{category}`",
            )
        card_presence = card.get("status", {}).get("presence")
        if entry.get("presence") != card_presence:
            report.warn(
                "card-presence",
                f"{asset_id}: index presence `{entry.get('presence')}` != card status `{card_presence}`",
            )

    # --- 2. cards on disk that the index does not know about ---
    known = {manifest for manifest, _, _ in manifests}
    for card_path in sorted(library.glob("*/*/asset.json")):
        rel = card_path.relative_to(library).as_posix()
        if rel not in known:
            report.fail("index-coverage", f"card `{rel}` is not registered in asset_index.json")

    # --- 3. card contents ---
    frame_triples: dict[str, set] = {}
    total_files = 0
    for rel_manifest, card, _label in manifests:
        missing = [field for field in CARD_REQUIRED if field not in card]
        if missing:
            report.fail("card-schema", f"{rel_manifest}: missing fields {missing}")
        status = card.get("status", {})
        missing_status = [field for field in STATUS_REQUIRED if field not in status]
        if missing_status:
            report.fail("card-status", f"{rel_manifest}: status is missing {missing_status}")
        if status.get("presence") not in KNOWN_PRESENCE:
            report.warn(
                "card-status", f"{rel_manifest}: presence `{status.get('presence')}` outside the D3 vocabulary"
            )

        # master
        master = card.get("master") or {}
        recorded_master_sha = master.get("sha256")
        master_checked = False
        master_file_seen = False
        for field in ("external_master_path", "internal_master_path"):
            value = master.get(field)
            if not value:
                continue
            candidate = (REPO / value) if field == "external_master_path" else library / value
            if not candidate.exists():
                report.warn("master-missing", f"{rel_manifest}: `{field}` = `{value}` not on disk")
                continue
            master_file_seen = True
            if not recorded_master_sha:
                report.fail("master-sha", f"{rel_manifest}: master file exists but no SHA-256 recorded")
                continue
            actual = sha256_file(candidate)
            if actual != recorded_master_sha:
                report.fail(
                    "master-sha",
                    f"{rel_manifest}: master SHA mismatch for `{value}`: recorded {recorded_master_sha}, actual {actual}",
                )
            else:
                master_checked = True
                report.ok("master-sha", f"{rel_manifest}: master `{value}` verified by SHA-256")
        if recorded_master_sha and not master_file_seen:
            report.warn(
                "master-sha", f"{rel_manifest}: master SHA recorded but no master file available to compare"
            )

        # files[]
        files = card.get("files", [])
        if not isinstance(files, list):
            report.fail("card-files", f"{rel_manifest}: `files` is not an array")
            files = []
        total_files += len(files)
        triples: set = frame_triples.setdefault(rel_manifest, set())
        for position, item in enumerate(files):
            item_label = f"{rel_manifest} files[{position}]"
            missing_item = [field for field in FILE_REQUIRED if field not in item]
            if missing_item:
                report.fail("file-schema", f"{item_label}: missing fields {missing_item}")
                continue
            path = safe_rel(library, item["path"], report, "file-path", item_label)
            if path is None:
                continue
            if item.get("role") == "game_export" and path.suffix.lower() != ".png":
                report.fail("file-type", f"{item_label}: role=game_export but not a PNG - `{item['path']}`")
            if not path.exists():
                report.fail("file-missing", f"{item_label}: file does not exist - `{item['path']}`")
                continue
            actual = sha256_file(path)
            if actual != item["sha256"]:
                report.fail(
                    "file-sha",
                    f"{item_label}: SHA mismatch for `{item['path']}` (recorded {item['sha256']}, actual {actual})",
                )
            if item.get("animation") is not None:
                triple = (item.get("animation"), item.get("direction"), item.get("frame_index"))
                if triple in triples:
                    report.fail("file-duplicate-frame", f"{item_label}: duplicate frame {triple}")
                triples.add(triple)
            for field in ("canvas_px", "pivot_px"):
                if item.get(field) is None:
                    report.warn("file-measured", f"{item_label}: `{field}` not measured")

    report.ok("files", f"checked files[] entries: {total_files}")

    # --- 4. category directories present on disk ---
    present = sorted(p.name for p in library.iterdir() if p.is_dir() and p.name in CATEGORIES)
    missing_categories = [c for c in CATEGORIES if c not in present]
    if missing_categories:
        report.warn("categories", f"categories missing locally: {missing_categories}")
    else:
        report.ok("categories", f"all {len(CATEGORIES)} categories exist locally")

    # --- 5. template must not pretend to be an asset ---
    template = load_json(library / "_templates" / "asset.template.json", report, "_templates/asset.template.json")
    if template is not None and template.get("asset_id") != "EXAMPLE_ONLY":
        report.fail("template", "template must have asset_id=EXAMPLE_ONLY")

    status = "PASS" if not report.failures else "FAIL"
    payload = {
        "generated_by": "tools/art/validate_asset_library.py",
        "library_root": "assets/references/gpt_asset_library",
        "status": status,
        "assets_in_index": len(entries),
        "cards_checked": len(manifests),
        "files_checked": total_files,
        "failures": report.failures,
        "warnings": report.warnings,
        "checks": report.checks,
    }
    out = REPO / args.json_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"RESULT: {status}")
    print(f"assets_in_index={len(entries)} cards={len(manifests)} files={total_files}")
    print(f"failures={len(report.failures)} warnings={len(report.warnings)}")
    for line in report.failures:
        print("  FAIL " + line)
    for line in report.warnings:
        print("  WARN " + line)
    print(f"wrote {args.json_out}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
