#!/usr/bin/env python
"""Copy owner-supplied supplemental references into assets/references/ safely.

Usage:
  add_supplemental_refs.py <repo> <src1> <dest-rel1> [<src2> <dest-rel2> ...]

Never overwrites a destination whose bytes differ; records SHA-256 and PNG
facts into reports/reference_supplemental.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import sys
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def png_facts(path: str) -> dict:
    data = open(path, "rb").read()
    if not data.startswith(PNG_SIG):
        raise ValueError("not a PNG")
    w, h, depth, color, comp, filt, inter = struct.unpack(">IIBBBBB", data[16:29])
    pos, idat = 8, 0
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        crc = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])[0]
        if zlib.crc32(ctype + body) & 0xFFFFFFFF != crc:
            raise ValueError(f"CRC mismatch in {ctype!r}")
        if ctype == b"IDAT":
            idat += length
        pos += 12 + length
        if ctype == b"IEND":
            break
    return {
        "width": w,
        "height": h,
        "bit_depth": depth,
        "color_type": color,
        "interlace": inter,
        "idat_bytes": idat,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    repo = os.path.abspath(sys.argv[1])
    pairs = list(zip(sys.argv[2::2], sys.argv[3::2]))
    if not pairs:
        print("no source/destination pairs", file=sys.stderr)
        return 2

    report = {"files": [], "errors": [], "status": "PASS"}
    for src, dest_rel in pairs:
        src = os.path.abspath(src)
        dest = os.path.join(repo, dest_rel)
        src_sha = sha256_file(src)
        record = {"source": src, "destination": dest_rel, "sha256": src_sha,
                  "size": os.path.getsize(src), "action": None}
        if os.path.exists(dest):
            existing = sha256_file(dest)
            if existing == src_sha:
                record["action"] = "unchanged"
            else:
                record["action"] = "conflict_not_overwritten"
                record["existing_sha256"] = existing
                report["errors"].append(f"{dest_rel}: differs from source, not overwritten")
                report["files"].append(record)
                continue
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            record["action"] = "copied"
        record["png"] = png_facts(dest)
        record["sha256_on_disk"] = sha256_file(dest)
        if record["sha256_on_disk"] != src_sha:
            report["errors"].append(f"{dest_rel}: hash changed after copy")
        try:
            from PIL import Image
            with Image.open(dest) as im:
                im.load()
                record["pillow"] = {"format": im.format, "mode": im.mode, "size": list(im.size)}
        except Exception as exc:
            report["errors"].append(f"{dest_rel}: Pillow failed: {exc}")
        report["files"].append(record)

    if report["errors"]:
        report["status"] = "FAIL"
    out = os.path.join(repo, "reports", "reference_supplemental.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    for f in report["files"]:
        print(f"{f['action']:<26} {f['destination']}  {f['png']['width']}x{f['png']['height']}  {f['sha256']}")
    print(f"\nRESULT: {report['status']} -> {out}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
