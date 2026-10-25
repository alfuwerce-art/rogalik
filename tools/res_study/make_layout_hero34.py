"""Добавляет в layout.json эксперимента записи для героя 3.1d (48 и 96 px).

Оба варианта проверяются в одинаковом экранном размере 192 px:
    hero34_48 — логическое 480×270, спрайт 48 px, 4×
    hero34_96 — логическое 960×540, спрайт 96 px, 2×

Фон берётся из уже собранных участков (`world_24` и `world_48`) в собственном
разрешении каждого варианта — так пиксель героя и пиксель среды совпадают.
Позиция героя и факела — те же, что в эксперименте 3.1c.

    python tools/res_study/make_layout_hero34.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "game" / "experiments" / "res_study" / "art"
LAYOUT = ART / "layout.json"

PAIRS = {
    "hero34_48": {"base": "a", "hero_png": "res://art/hero34/hero34_48.png", "height": 48,
                  "content_scale": 4},
    "hero34_96": {"base": "c", "hero_png": "res://art/hero34/hero34_96.png", "height": 96,
                  "content_scale": 2},
}


def main() -> int:
    data = json.loads(LAYOUT.read_text(encoding="utf-8"))
    for name, cfg in PAIRS.items():
        base = data[cfg["base"]]
        entry = dict(base)
        entry.update({
            "variant": name,
            "hero_png": cfg["hero_png"],
            "hero_height": cfg["height"],
            "content_scale": cfg["content_scale"],
            "hero_screen_height": cfg["height"] * cfg["content_scale"],
            "hero_scale": 1,
            "occluder": True,
            "source_variant": cfg["base"],
        })
        data[name] = entry
        print(f"{name}: логическое {entry['viewport']}, тайл {entry['tile']}, "
              f"герой {cfg['height']} px = {entry['hero_screen_height']} px на экране, "
              f"масштаб {cfg['content_scale']}×")
    LAYOUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"layout: {LAYOUT.relative_to(ROOT).as_posix()} ({len(data)} вариантов)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
