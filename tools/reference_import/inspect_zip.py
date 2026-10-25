#!/usr/bin/env python
"""Read-only inspection of the Rogalik concept-art ZIP.

Prints a JSON report to stdout: archive facts, entry list, integrity test,
manifest contents and structural risk checks (duplicates, zip-slip,
absolute paths, symlinks). It never writes or extracts anything.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile

EXPECTED_PNGS = 23


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def risky_path_reason(name: str) -> str | None:
    norm = name.replace("\\", "/")
    if norm.startswith("/"):
        return "absolute unix path"
    if len(norm) > 1 and norm[1] == ":":
        return "windows drive letter"
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return "parent-directory traversal"
    if "\\" in name:
        return "backslash separator"
    return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    archive = sys.argv[1]
    report: dict = {}

    if not os.path.isfile(archive):
        print(json.dumps({"error": f"not a file: {archive}"}, ensure_ascii=False, indent=2))
        return 2

    report["archive"] = {
        "path": os.path.abspath(archive),
        "size_bytes": os.path.getsize(archive),
        "size_mib": round(os.path.getsize(archive) / (1024 * 1024), 3),
        "sha256": sha256_file(archive),
    }

    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        bad = zf.testzip()

        entries = []
        for info in infos:
            entries.append(
                {
                    "name": info.filename,
                    "size": info.file_size,
                    "compressed": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                    "method": info.compress_type,
                    "is_dir": info.is_dir(),
                    "external_attr": info.external_attr,
                    "symlink": bool((info.external_attr >> 16) & 0o170000 == 0o120000),
                }
            )

        pngs = [e for e in entries if not e["is_dir"] and e["name"].lower().endswith(".png")]
        other = [e for e in entries if not e["is_dir"] and not e["name"].lower().endswith(".png")]

        seen: dict[str, list[str]] = {}
        for e in entries:
            key = e["name"].replace("\\", "/").lower()
            seen.setdefault(key, []).append(e["name"])
        duplicates = {k: v for k, v in seen.items() if len(v) > 1}

        risky = {}
        for e in entries:
            reason = risky_path_reason(e["name"])
            if reason:
                risky[e["name"]] = reason

        names = {e["name"] for e in entries}
        manifest_name = next(
            (n for n in names if n.lower().endswith((".json", ".txt", ".sha256", ".md"))),
            None,
        )
        manifest_content = None
        if manifest_name:
            manifest_content = zf.read(manifest_name).decode("utf-8", errors="replace")

        report["zipfile"] = {
            "entry_count": len(infos),
            "png_count": len(pngs),
            "other_files": [
                {"name": e["name"], "size": e["size"], "crc32": e["crc32"]} for e in other
            ],
            "testzip_bad_member": bad,
            "duplicates_case_insensitive": duplicates,
            "risky_paths": risky,
            "symlink_entries": [e["name"] for e in entries if e["symlink"]],
            "manifest_candidate": manifest_name,
            "manifest_content": manifest_content,
        }

    report["checks"] = {
        "png_count_expected": EXPECTED_PNGS,
        "png_count_actual": report["zipfile"]["png_count"],
        "png_count_ok": report["zipfile"]["png_count"] == EXPECTED_PNGS,
        "crc_ok": report["zipfile"]["testzip_bad_member"] is None,
        "no_duplicates": not report["zipfile"]["duplicates_case_insensitive"],
        "no_risky_paths": not report["zipfile"]["risky_paths"],
        "no_symlinks": not report["zipfile"]["symlink_entries"],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
