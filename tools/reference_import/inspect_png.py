#!/usr/bin/env python
"""Inspect a PNG: hashes, chunk structure, metadata, decoder probe."""

from __future__ import annotations

import hashlib
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    for path in sys.argv[1:]:
        data = open(path, "rb").read()
        print(f"== {path}")
        print(f"size={len(data)} sha256={hashlib.sha256(data).hexdigest()}")
        pos = 8
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "not png"
        while pos + 8 <= len(data):
            (length,) = struct.unpack(">I", data[pos : pos + 4])
            ctype = data[pos + 4 : pos + 8]
            body = data[pos + 8 : pos + 8 + length]
            crc = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])[0]
            assert zlib.crc32(ctype + body) & 0xFFFFFFFF == crc, f"crc fail {ctype}"
            name = ctype.decode("ascii")
            extra = ""
            if name == "IHDR":
                w, h, depth, color, comp, filt, inter = struct.unpack(">IIBBBBB", body)
                extra = f" {w}x{h} depth={depth} color={color} interlace={inter}"
            elif name in ("tEXt", "iTXt", "zTXt"):
                extra = " " + body[:120].decode("latin-1", errors="replace").replace("\x00", ": ")
            print(f"  {name} len={length}{extra}")
            pos += 12 + length
            if name == "IEND":
                break
        from PIL import Image

        with Image.open(path) as im:
            im.load()
            print(f"  Pillow: {im.format} {im.mode} {im.size} frames={getattr(im, 'n_frames', 1)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
