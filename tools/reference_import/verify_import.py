#!/usr/bin/env python
"""Post-import verification of the Rogalik concept-art references.

Independent of the import step: re-hashes everything on disk, re-checks the
original archive, cross-checks the documented SHA-256 values and the paths
listed in docs/CONCEPT_ART_INDEX.md, and confirms there are no duplicate
images. Exit code 0 only when every check passes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import sys
import zipfile
import zlib

ARCHIVE_SHA256 = "e900eaad8806b881eb91d51ea649d9f2ad1131974a3687bd67628a3515169b23"
ARCHIVE_SIZE = 68551781
PNG_SIG = b"\x89PNG\r\n\x1a\n"

# SHA-256 values that specific documents claim for their reference images.
DOC_CLAIMS = {
    "docs/BOSS_REFERENCES.md": {
        "assets/references/bosses/poludnitsa.png":
            "fb1bf760eaee8b6aa8fc9cb10b7ae8c3bbde292f5345eb15ff5ffaeed0ab64e8",
        "assets/references/bosses/utoplennitsa.png":
            "2e160986e5cd9be059706ebf61745cab1cb62a6f8c55604fe87033024ecd75e1",
    },
    "docs/WEAPON_REFERENCES.md": {
        "assets/references/weapons/01_two_handed_weapons.png":
            "a95f7e606b6a40bde71c4704f425458cb26e7d7af639d93d4e12c9b682d80bd0",
        "assets/references/weapons/02_magic_staves.png":
            "861774fb7fcabc8dad1d4cb36f6ab7e5d16c956b13b95e6c240c95b74a017452",
        "assets/references/weapons/03_dual_weapons.png":
            "f82ce5d88d888cba76d280be4ef2ac2115f95d93e1f5a187359714d9763cffd1",
        "assets/references/weapons/04_bows.png":
            "d28986462a987d62a05c4f545accfa19c65237fd108034da9eae0ed0cb22c76c",
        "assets/references/weapons/05_combat_staves.png":
            "f7c53ef5c76990ef43f59a6a1af1b8b9ae3b752162f3292e808e2ca82b766269",
    },
}
# Claims about fixed pixel sizes stated by the documents.
DOC_SIZE_CLAIMS = {
    "assets/references/weapons/01_two_handed_weapons.png": (1672, 941),
    "assets/references/weapons/02_magic_staves.png": (1672, 941),
    "assets/references/weapons/03_dual_weapons.png": (1672, 941),
    "assets/references/weapons/04_bows.png": (1672, 941),
    "assets/references/weapons/05_combat_staves.png": (1672, 941),
    "assets/references/bosses/poludnitsa.png": (1024, 1536),
    "assets/references/bosses/utoplennitsa.png": (1024, 1536),
}
DOC_BYTE_CLAIMS = {
    "assets/references/bosses/poludnitsa.png": 2716015,
    "assets/references/bosses/utoplennitsa.png": 2725848,
}
# Owner-supplied references added after the archive import (not in its manifest).
SUPPLEMENTAL = {
    "assets/references/hero/hero_reference_front_back.png":
        "53c9ace7a25dd16916c2cd7dfbba7ef7410a8a701090b3a2fe042f788c99f985",
    "assets/references/gameplay/gameplay_look_reference.png":
        "c04d11f71ae2d2c98e8199ee654040b57dd3d451fa2d07943fb8556a744d9ae2",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ihdr(path: str) -> tuple[int, int, int, int]:
    with open(path, "rb") as fh:
        head = fh.read(33)
    if not head.startswith(PNG_SIG):
        raise ValueError("bad signature")
    length = struct.unpack(">I", head[8:12])[0]
    ctype = head[12:16]
    if ctype != b"IHDR" or length != 13:
        raise ValueError("no IHDR first")
    crc = struct.unpack(">I", head[29:33])[0]
    if zlib.crc32(head[12:29]) & 0xFFFFFFFF != crc:
        raise ValueError("IHDR CRC mismatch")
    w, h, depth, color = struct.unpack(">IIBB", head[16:26])
    return w, h, depth, color


def parse_manifest(path: str) -> dict[str, str]:
    out = {}
    for line in open(path, encoding="utf-8").read().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        out[rel.strip()] = digest.lower()
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    repo = os.path.abspath(sys.argv[1])
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    archive = os.path.join(repo, "assets", "archives", "rogalik_all_concept_art_with_weapons.zip")
    test = os.path.join(repo, "assets", "references")
    manifest_path = os.path.join(repo, "docs", "REFERENCE_FILE_MANIFEST.sha256")

    check("archive exists", os.path.isfile(archive), archive)
    arch_sha = sha256_file(archive)
    arch_size = os.path.getsize(archive)
    check("archive sha256 unchanged", arch_sha == ARCHIVE_SHA256, arch_sha)
    check("archive size unchanged", arch_size == ARCHIVE_SIZE, str(arch_size))
    with zipfile.ZipFile(archive) as zf:
        check("archive CRC scan (testzip)", zf.testzip() is None, "all members readable")

    manifest = parse_manifest(manifest_path)
    check("manifest entries", len(manifest) == 23, f"{len(manifest)} entries")

    on_disk: dict[str, str] = {}
    for dirpath, _dirs, files in os.walk(test):
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo).replace(os.sep, "/")
            on_disk[rel] = sha256_file(full)

    expected_files = set(manifest) | set(SUPPLEMENTAL)
    extra = sorted(set(on_disk) - expected_files)
    missing = sorted(set(manifest) - set(on_disk))
    missing_supp = sorted(set(SUPPLEMENTAL) - set(on_disk))
    check("no unexpected files in assets/references", not extra, ", ".join(extra) or "none")
    check("all manifest files present", not missing, ", ".join(missing) or "none")
    check("owner-supplied hero/gameplay refs present", not missing_supp,
          ", ".join(missing_supp) or "2/2 present")

    mismatched = sorted(rel for rel, sha in manifest.items() if on_disk.get(rel) != sha)
    check("every file matches manifest sha256", not mismatched, ", ".join(mismatched) or "23/23 match")
    supp_bad = sorted(rel for rel, sha in SUPPLEMENTAL.items() if on_disk.get(rel) != sha)
    check("hero/gameplay refs match owner-supplied sha256", not supp_bad,
          ", ".join(supp_bad) or "2/2 match")

    dupes: dict[str, list[str]] = {}
    for rel, sha in on_disk.items():
        dupes.setdefault(sha, []).append(rel)
    dupes = {sha: rels for sha, rels in dupes.items() if len(rels) > 1}
    check("no duplicate image content", not dupes,
          json.dumps(dupes) if dupes else f"{len(on_disk)} unique images")

    # Decompressed content of the archive equals what is on disk.
    with zipfile.ZipFile(archive) as zf:
        from_zip = {
            "assets/references/" + n[len("rogalik/assets/references/"):]: hashlib.sha256(
                zf.read(n)
            ).hexdigest()
            for n in zf.namelist()
            if n.startswith("rogalik/assets/references/") and n.lower().endswith(".png")
        }
    check("extracted bytes identical to archive",
          from_zip == {k: v for k, v in on_disk.items() if k in manifest},
          "byte-for-byte, no re-encoding")

    manifest_in_zip = None
    with zipfile.ZipFile(archive) as zf:
        manifest_in_zip = zf.read("rogalik/docs/REFERENCE_FILE_MANIFEST.sha256")
    check("docs manifest byte-identical to archive copy",
          open(manifest_path, "rb").read() == manifest_in_zip, "2950 bytes expected")

    # PNG structure and decoder probes.
    bad_png = []
    dims: dict[str, tuple[int, int]] = {}
    try:
        from PIL import Image
    except Exception as exc:
        check("Pillow available", False, str(exc))
        Image = None
    for rel in sorted(on_disk):
        path = os.path.join(repo, rel)
        try:
            w, h, _depth, _color = ihdr(path)
            dims[rel] = (w, h)
            if Image is not None:
                with Image.open(path) as im:
                    im.load()
                    if im.size != (w, h):
                        raise ValueError("Pillow size differs from IHDR")
        except Exception as exc:
            bad_png.append(f"{rel}: {exc}")
    check("all PNGs open and decode", not bad_png,
          "; ".join(bad_png) or f"{len(on_disk)}/{len(on_disk)} decoded")

    # Documented hashes and sizes.
    for doc, claims in DOC_CLAIMS.items():
        for rel, sha in claims.items():
            path = os.path.join(repo, rel)
            actual = on_disk.get(rel)
            check(f"{doc} sha256 claim: {rel}", actual == sha, f"actual {actual}")
    for rel, (w, h) in DOC_SIZE_CLAIMS.items():
        check(f"documented size {w}x{h}: {rel}", dims.get(rel) == (w, h), str(dims.get(rel)))
    for rel, size in DOC_BYTE_CLAIMS.items():
        actual = os.path.getsize(os.path.join(repo, rel))
        check(f"documented byte size {size}: {rel}", actual == size, str(actual))

    # CONCEPT_ART_INDEX.md paths must be exactly the files on disk.
    index_text = open(os.path.join(repo, "docs", "CONCEPT_ART_INDEX.md"), encoding="utf-8").read()
    indexed = set(re.findall(r"`(assets/references/[^`]+\.png)`", index_text))
    check("CONCEPT_ART_INDEX lists every reference path", indexed == set(on_disk),
          f"{len(indexed)} paths; missing in index: {sorted(set(on_disk) - indexed) or 'none'}; "
          f"stale in index: {sorted(indexed - set(on_disk)) or 'none'}")

    # BESTIARY registry paths must exist, and no extra art may appear.
    bestiary_text = open(os.path.join(repo, "docs", "BESTIARY.md"), encoding="utf-8").read()
    bestiary_paths = set()
    for token in re.findall(r"`((?:assets/references/|enemies/|bosses/|weapons/|locations/)"
                            r"[^`]+\.png)`", bestiary_text):
        rel = token if token.startswith("assets/") else "assets/references/" + token
        bestiary_paths.add(rel)
    check("BESTIARY lists only existing reference files",
          bestiary_paths <= set(on_disk),
          ", ".join(sorted(bestiary_paths - set(on_disk))) or f"{len(bestiary_paths)} paths exist")
    no_ref_families = sorted(
        fam for fam in ("B06", "B07", "B08", "B09", "E05", "E06", "E07", "E08", "E09", "E10")
        if f"| {fam} |" in bestiary_text
    )
    check("BESTIARY marks reference-less units", len(no_ref_families) == 10,
          f"{len(no_ref_families)}/10 units listed")

    # Approved / candidate split — computed over the archived (manifest) set only.
    manifest_set = set(manifest)
    approved = {rel for rel in manifest_set if "candidate" not in rel.lower()
                and not rel.startswith("assets/references/locations/")}
    candidates = manifest_set - approved
    check("approved vs candidate split (archive)", len(approved) == 17 and len(candidates) == 6,
          f"{len(approved)} approved, {len(candidates)} candidate")
    check("supplemental refs counted separately", len(SUPPLEMENTAL) == 2,
          "hero design reference + gameplay look reference")

    ok = all(c["ok"] for c in checks)
    report = {
        "status": "PASS" if ok else "FAIL",
        "repo": repo,
        "archive": {"path": archive, "size": arch_size, "sha256": arch_sha},
        "counts": {
            "pngs_verified": len(on_disk),
            "archive_manifest_files": len(manifest),
            "approved": len(approved),
            "candidate": len(candidates),
            "supplemental": len(SUPPLEMENTAL),
        },
        "dimensions": {rel: list(d) for rel, d in sorted(dims.items())},
        "checks": checks,
    }
    with open(os.path.join(repo, "reports", "reference_import_verify.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")
    print(f"\nRESULT: {report['status']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
