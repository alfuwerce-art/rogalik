#!/usr/bin/env python
"""Verify and extract the 23 original concept-art PNGs from the Rogalik ZIP.

Guarantees:
  * every extracted file matches the SHA-256 recorded in the archive manifest;
  * the archive `rogalik/` prefix is stripped (no nested rogalik/rogalik);
  * only PNGs under assets/references/ are touched;
  * an existing destination file is never overwritten when its content differs;
  * the original ZIP is opened read-only and left untouched.

Writes a JSON report to --report and prints a short summary.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import zipfile
import zlib

PREFIX = "rogalik/"
REFS_PREFIX = PREFIX + "assets/references/"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"bad manifest line: {line!r}")
        digest, path = parts[0].lower(), parts[1].strip()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"bad digest in manifest: {line!r}")
        entries[path] = digest
    return entries


def png_structure(data: bytes) -> dict:
    """Walk PNG chunks, verify CRC of each, and require IHDR/IDAT/IEND."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("missing PNG signature")
    pos = len(PNG_SIGNATURE)
    chunks: list[str] = []
    width = height = bit_depth = color_type = None
    idat_bytes = 0
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if pos + 12 + length > len(data):
            raise ValueError(f"truncated chunk {ctype!r}")
        (crc,) = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])
        if zlib.crc32(ctype + body) & 0xFFFFFFFF != crc:
            raise ValueError(f"CRC mismatch in chunk {ctype!r}")
        name = ctype.decode("ascii", errors="replace")
        chunks.append(name)
        if name == "IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", body[:10])
        elif name == "IDAT":
            idat_bytes += length
        elif name == "IEND":
            pos += 12 + length
            break
        pos += 12 + length
    if "IHDR" not in chunks or "IDAT" not in chunks or "IEND" not in chunks:
        raise ValueError(f"missing mandatory chunk, got {chunks}")
    if not idat_bytes:
        raise ValueError("empty IDAT")
    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "chunks": len(chunks),
        "idat_bytes": idat_bytes,
    }


def pillow_probe(path: str) -> dict:
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"available": False, "error": f"Pillow import failed: {exc}"}
    try:
        with Image.open(path) as im:
            im.load()
            return {
                "available": True,
                "format": im.format,
                "mode": im.mode,
                "size": list(im.size),
                "animated": bool(getattr(im, "n_frames", 1) > 1),
            }
    except Exception as exc:
        return {"available": True, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    archive, repo_root, report_path = sys.argv[1], sys.argv[2], sys.argv[3]
    report: dict = {
        "archive": os.path.abspath(archive),
        "repo_root": os.path.abspath(repo_root),
        "files": [],
        "errors": [],
        "warnings": [],
    }

    with zipfile.ZipFile(archive) as zf:
        names = [i.filename for i in zf.infolist()]
        manifest_member = next(n for n in names if n.endswith("REFERENCE_FILE_MANIFEST.sha256"))
        manifest = parse_manifest(zf.read(manifest_member).decode("utf-8"))

        archive_pngs = [
            n for n in names if n.lower().endswith(".png") and not zf.getinfo(n).is_dir()
        ]
        manifest_members = {PREFIX + p: d for p, d in manifest.items()}

        missing = sorted(set(manifest_members) - set(archive_pngs))
        extra = sorted(set(archive_pngs) - set(manifest_members))
        if missing:
            report["errors"].append(f"manifest files absent from archive: {missing}")
        if extra:
            report["errors"].append(f"archive PNGs absent from manifest: {extra}")

        for member in archive_pngs:
            info = zf.getinfo(member)
            data = zf.read(member)
            actual = sha256_bytes(data)
            expected = manifest_members.get(member)
            rel = member[len(REFS_PREFIX):]
            dest = os.path.normpath(os.path.join(repo_root, "assets", "references", *rel.split("/")))
            record = {
                "member": member,
                "relative": rel,
                "destination": dest,
                "size": len(data),
                "sha256": actual,
                "sha256_manifest": expected,
                "sha256_match": actual == expected,
                "action": None,
                "png": None,
            }

            if expected is None:
                record["action"] = "skipped_unlisted"
                report["errors"].append(f"{rel}: not listed in manifest, not extracted")
                report["files"].append(record)
                continue
            if actual != expected:
                record["action"] = "skipped_hash_mismatch"
                report["errors"].append(f"{rel}: sha256 mismatch, not extracted")
                report["files"].append(record)
                continue

            if os.path.exists(dest):
                existing = sha256_file(dest)
                if existing == actual:
                    record["action"] = "unchanged"
                else:
                    record["action"] = "conflict_not_overwritten"
                    record["existing_sha256"] = existing
                    report["errors"].append(
                        f"{rel}: destination exists with different content, left untouched"
                    )
            else:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(data)
                record["action"] = "extracted"

            if record["action"] in ("extracted", "unchanged"):
                on_disk = sha256_file(dest)
                record["sha256_on_disk"] = on_disk
                if on_disk != expected:
                    report["errors"].append(f"{rel}: on-disk hash differs after write")
                try:
                    record["png"] = png_structure(data)
                except Exception as exc:
                    report["errors"].append(f"{rel}: PNG structure invalid: {exc}")
                record["pillow"] = pillow_probe(dest)

            report["files"].append(record)

        # Reference folder must contain exactly the manifest files.
        refs_root = os.path.join(repo_root, "assets", "references")
        expected_rel = {p[len("assets/references/"):].replace("/", os.sep) for p in manifest}
        found_rel = set()
        for dirpath, _dirnames, filenames in os.walk(refs_root):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                found_rel.add(os.path.relpath(full, refs_root))
        unexpected = sorted(found_rel - expected_rel)
        absent = sorted(expected_rel - found_rel)
        if unexpected:
            report["warnings"].append(f"extra files in assets/references: {unexpected}")
        if absent:
            report["errors"].append(f"missing files in assets/references: {absent}")

    extracted = [f for f in report["files"] if f["action"] in ("extracted", "unchanged")]
    report["summary"] = {
        "manifest_entries": len(manifest),
        "archive_pngs": len(archive_pngs),
        "verified_and_present": len(extracted),
        "extracted_now": sum(1 for f in report["files"] if f["action"] == "extracted"),
        "already_identical": sum(1 for f in report["files"] if f["action"] == "unchanged"),
        "conflicts": sum(1 for f in report["files"] if f["action"] == "conflict_not_overwritten"),
        "errors": len(report["errors"]),
        "warnings": len(report["warnings"]),
        "status": "PASS" if not report["errors"] else "FAIL",
    }

    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    for f in report["files"]:
        print(f"{f['action']:<26} {f['relative']}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for err in report["errors"]:
        print(f"ERROR: {err}", file=sys.stderr)
    for warn in report["warnings"]:
        print(f"WARN: {warn}", file=sys.stderr)
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
