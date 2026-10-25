#!/usr/bin/env python
"""Print a human-readable table from reports/reference_import.json."""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

report = json.load(open(sys.argv[1], encoding="utf-8"))
header = f"{'file':<58}{'bytes':>9}  {'PNG':<14}{'Pillow':<22}sha256[:16]"
print(header)
print("-" * len(header))
for f in report["files"]:
    png_info = f["png"]
    pil = f["pillow"]
    png = f"{png_info['width']}x{png_info['height']}" if png_info else "INVALID"
    if pil.get("available") and "error" not in pil:
        probe = f"{pil['mode']} {pil['size'][0]}x{pil['size'][1]}"
    else:
        probe = str(pil.get("error"))
    print(f"{f['relative']:<58}{f['size']:>9}  {png:<14}{probe:<22}{f['sha256'][:16]}")
print()
print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
