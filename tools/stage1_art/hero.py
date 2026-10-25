"""Rogalik hero sprite authoring (stage 1).

Design source: ``assets/references/hero/hero_reference_front_back.png``
(status VISUAL_APPROVED for the design).  The character keeps the reference's
identity at 52 px tall: red cloth blindfold, voluminous shoulder-length hair,
bare muscular torso, dark ragged trousers, red sash, forearm/shin wraps, bare
feet.  The weapon is intentionally *not* painted into the body sheet: it is a
separate sprite because the hero picks it up during the run.

Layout of the exported strip (frame 48x56):
    down idle,move,dodge,attack,hurt,death
    side idle,move,dodge,attack,hurt,death
    up   idle,move,dodge,attack,hurt,death
"""

from __future__ import annotations

from PIL import Image

from pixel_canvas import Canvas, Material, Palette, Region, hex_rgba

CELL_W = 48
CELL_H = 56
CX = 24
FOOT_Y = 55

INK = hex_rgba("#14111A")
SHADOW = (5, 5, 9, 70)

SKIN = Material(
    Palette(
        outline=INK,
        shadow=hex_rgba("#6A4736"),
        base=hex_rgba("#96684F"),
        light=hex_rgba("#B0835F"),
        highlight=hex_rgba("#C99C74"),
    ),
)
SKIN_DARK = Material(
    Palette(
        outline=INK,
        shadow=hex_rgba("#55382C"),
        base=hex_rgba("#79523F"),
        light=hex_rgba("#8E6450"),
        highlight=hex_rgba("#A47C63"),
    ),
)
HAIR = Material(
    Palette(
        outline=hex_rgba("#0E0B0A"),
        shadow=hex_rgba("#221A15"),
        base=hex_rgba("#342820"),
        light=hex_rgba("#4B3A2C"),
        highlight=hex_rgba("#63503D"),
    ),
    texture=9,
)
BLINDFOLD = Material(
    Palette(
        outline=hex_rgba("#26080D"),
        shadow=hex_rgba("#5A1822"),
        base=hex_rgba("#8A2A36"),
        light=hex_rgba("#A53A44"),
        highlight=hex_rgba("#C25A55"),
    ),
    texture=6,
)
PANTS = Material(
    Palette(
        outline=hex_rgba("#0F0D0C"),
        shadow=hex_rgba("#1F1C1A"),
        base=hex_rgba("#2E2A26"),
        light=hex_rgba("#3F3831"),
        highlight=hex_rgba("#514739"),
    ),
    texture=16,
)
SASH = Material(
    Palette(
        outline=hex_rgba("#1C070C"),
        shadow=hex_rgba("#49141D"),
        base=hex_rgba("#6A202C"),
        light=hex_rgba("#832B37"),
        highlight=hex_rgba("#9C3A42"),
    ),
    texture=6,
)
WRAP = Material(
    Palette(
        outline=hex_rgba("#151210"),
        shadow=hex_rgba("#3E362B"),
        base=hex_rgba("#5B5040"),
        light=hex_rgba("#726553"),
        highlight=hex_rgba("#8B7B63"),
    ),
    texture=8,
)
WRAP_DARK = Material(
    Palette(
        outline=hex_rgba("#121010"),
        shadow=hex_rgba("#30291F"),
        base=hex_rgba("#463C2F"),
        light=hex_rgba("#564A3A"),
        highlight=hex_rgba("#6A5B46"),
    ),
    texture=8,
)
MOUTH = hex_rgba("#3A1F1B")
BLOOD = hex_rgba("#771E27")

FACINGS = ("down", "side", "up")
ANIMATIONS = ("idle", "move", "dodge", "attack", "hurt", "death")

POSES: dict[str, list[dict]] = {
    "idle": [
        {"bob": 0, "lean": 0, "leg_l": 0, "leg_r": 0, "arm_l": 0, "arm_r": 0, "hair": 0},
        {"bob": 1, "lean": 0, "leg_l": 0, "leg_r": 0, "arm_l": 1, "arm_r": -1, "hair": 1},
    ],
    "move": [
        {"bob": 0, "lean": 1, "leg_l": -1, "leg_r": 1, "arm_l": 2, "arm_r": -2, "hair": 0},
        {"bob": 1, "lean": 0, "leg_l": 0, "leg_r": 0, "arm_l": 0, "arm_r": 0, "hair": 1},
        {"bob": 0, "lean": -1, "leg_l": 1, "leg_r": -1, "arm_l": -2, "arm_r": 2, "hair": 0},
        {"bob": 1, "lean": 0, "leg_l": 0, "leg_r": 0, "arm_l": 0, "arm_r": 0, "hair": 1},
    ],
    "dodge": [
        {"special": "dodge_crouch"},
        {"special": "dodge_tuck"},
        {"special": "dodge_rise"},
    ],
    "attack": [
        {"special": "attack_windup"},
        {"special": "attack_strike"},
        {"special": "attack_recover"},
    ],
    "hurt": [{"special": "hurt"}],
    "death": [
        {"special": "death_1"},
        {"special": "death_2"},
        {"special": "death_3"},
        {"special": "death_4"},
    ],
}


# ---------------------------------------------------------------------------
# Shared geometry helpers
# ---------------------------------------------------------------------------

# Shoulder / waist landmarks for the standing body.
SHOULDER_Y = 22.0
WAIST_Y = 33.0
HEAD_CY = 11.0


def _ground_shadow(c: Canvas, cx: int = CX, width: float = 10.0) -> None:
    for x, y in Region(CELL_W, CELL_H).ellipse(cx, FOOT_Y - 0.5, width, 2.4).pixels:
        c.put(x, y, SHADOW)


def _torso(cx: int, top: int) -> tuple[Region, Region, Region]:
    torso = Region(CELL_W, CELL_H).polygon(
        [
            (cx - 8.0, top + 1.0),
            (cx + 8.0, top + 1.0),
            (cx + 7.4, top + 6.0),
            (cx + 5.8, top + 11.5),
            (cx + 4.0, top + 13.5),
            (cx - 4.0, top + 13.5),
            (cx - 5.8, top + 11.5),
            (cx - 7.4, top + 6.0),
        ]
    )
    shoulders = Region(CELL_W, CELL_H)
    shoulders.ellipse(cx - 7.8, top + 2.0, 3.4, 3.0)
    shoulders.ellipse(cx + 7.8, top + 2.0, 3.4, 3.0)
    neck = Region(CELL_W, CELL_H).rect(cx - 2, top - 3, cx + 2, top + 1)
    return torso, shoulders, neck


def _torso_detail(c: Canvas, cx: int, top: int, *, back: bool) -> None:
    pal = SKIN.palette
    if back:
        for y in range(top + 4, top + 12):
            c.put(cx, y, pal.shadow)
        for side in (-1, 1):
            c.put(cx + side * 3, top + 3, pal.light)
            c.put(cx + side * 3, top + 4, pal.light)
            c.put(cx + side * 4, top + 5, pal.shadow)
            c.put(cx + side * 5, top + 6, pal.shadow)
        return
    for side in (-1, 1):
        # collar bone
        for step in range(4):
            c.put(cx + side * (2 + step), top + 2 + (1 if step == 3 else 0), pal.highlight)
        # pectoral mass
        for x, y in Region(CELL_W, CELL_H).ellipse(cx + side * 3.4, top + 5.4, 3.0, 1.8).pixels:
            if y <= top + 5:
                c.put(x, y, pal.light)
        c.put(cx + side * 3, top + 7, pal.shadow)
        c.put(cx + side * 5, top + 5, pal.shadow)
        # oblique shade
        c.put(cx + side * 5, top + 10, pal.shadow)
        c.put(cx + side * 4, top + 11, pal.shadow)
        # abdominal highlight
        c.put(cx + side * 2, top + 9, pal.light)
        c.put(cx + side * 3, top + 11, pal.light)
    c.put(cx, top + 4, pal.shadow)
    c.put(cx, top + 8, pal.shadow)
    c.put(cx - 2, top + 7, pal.shadow)
    c.put(cx + 2, top + 7, pal.shadow)
    c.put(cx, top + 10, pal.shadow)
    c.put(cx, top + 12, pal.shadow)
    # old scars
    for x, y in ((cx - 5, top + 4), (cx - 4, top + 5), (cx - 3, top + 6)):
        c.put(x, y, pal.light)
    for x, y in ((cx + 5, top + 9), (cx + 4, top + 10), (cx + 3, top + 11)):
        c.put(x, y, pal.light)


def _pants(cx: int, waist: int, leg_l: int, leg_r: int) -> tuple[Region, Region, Region]:
    hips = Region(CELL_W, CELL_H).ellipse(cx, waist + 1.5, 9.6, 4.4)
    left = Region(CELL_W, CELL_H).capsule(cx - 4.0, waist + 2.0, cx - 5.0, waist + 11.0 + leg_l, 5.2)
    right = Region(CELL_W, CELL_H).capsule(cx + 4.0, waist + 2.0, cx + 5.0, waist + 11.0 + leg_r, 5.2)
    return hips, left, right


def _fray(region: Region, y: int, seed: int) -> None:
    for x in range(CELL_W):
        value = (x * 73 + seed * 131) % 97
        if value < 30:
            region.pixels.discard((x, y))
        if value < 14:
            region.pixels.discard((x, y - 1))


def _legs(c: Canvas, cx: int, waist: int, leg_l: int, leg_r: int, *, back: bool) -> None:
    hips, left, right = _pants(cx, waist, leg_l, leg_r)
    _fray(left, waist + 13 + leg_l, 3)
    _fray(right, waist + 13 + leg_r, 8)
    c.paint(hips, PANTS, seed=1)
    c.paint(left, PANTS, seed=2)
    c.paint(right, PANTS, seed=3)
    # knee folds
    for side, leg in ((-1, leg_l), (1, leg_r)):
        knee_y = waist + 10 + leg
        c.put(cx + side * 5, knee_y, PANTS.palette.light)
        c.put(cx + side * 4, knee_y + 1, PANTS.palette.shadow)
    for side, leg in ((-1, leg_l), (1, leg_r)):
        fx = cx + side * 5
        shin = Region(CELL_W, CELL_H).capsule(fx, waist + 12 + leg, fx, waist + 19 + leg, 2.4)
        c.paint(shin, WRAP if side < 0 else WRAP_DARK, seed=4 + side)
        for band in (0.35, 0.7):
            by = int(waist + 12 + leg + 7 * band)
            c.put(fx - 2, by, WRAP_DARK.palette.shadow)
            c.put(fx - 1, by, WRAP_DARK.palette.shadow)
            c.put(fx, by, WRAP_DARK.palette.shadow)
            c.put(fx + 1, by, WRAP_DARK.palette.shadow)
            c.put(fx + 2, by, WRAP_DARK.palette.shadow)
        foot = Region(CELL_W, CELL_H).ellipse(fx, waist + 21.5 + leg, 3.2, 1.7)
        c.paint(foot, SKIN if side < 0 or not back else SKIN_DARK, seed=6 + side)
        if back:
            for x, y in list(foot.pixels):
                if y <= waist + 21 + leg:
                    c.put(x, y, SKIN.palette.shadow)


def _arm(c: Canvas, shoulder, elbow, hand, *, near: bool = True) -> None:
    material = SKIN if near else SKIN_DARK
    upper = Region(CELL_W, CELL_H).capsule(shoulder[0], shoulder[1], elbow[0], elbow[1], 2.8)
    forearm = Region(CELL_W, CELL_H).capsule(elbow[0], elbow[1], hand[0], hand[1] - 1.0, 2.2)
    c.paint(upper, material if near else SKIN_DARK, seed=11)
    c.paint(forearm, WRAP if near else WRAP_DARK, seed=12)
    for t in (0.3, 0.62):
        bx = elbow[0] * (1 - t) + hand[0] * t
        by = elbow[1] * (1 - t) + (hand[1] - 1.0) * t
        c.paint(Region(CELL_W, CELL_H).ellipse(bx, by, 2.4, 0.8), WRAP_DARK, seed=13)
    fist = Region(CELL_W, CELL_H).ellipse(hand[0], hand[1], 2.4, 2.3)
    c.paint(fist, material, seed=15)


def _default_arms(cx: int, top: int, bob: int, arm_l: int, arm_r: int):
    shoulder_y = top + 3.0 + bob
    return (
        (cx - 7.4, shoulder_y),
        (cx - 10.6, shoulder_y + 6.0),
        (cx - 11.0 - arm_l, shoulder_y + 12.5 + arm_l),
    ), (
        (cx + 7.4, shoulder_y),
        (cx + 10.6, shoulder_y + 6.0),
        (cx + 11.0 + arm_r, shoulder_y + 12.5 - arm_r),
    )


def _sash(c: Canvas, cx: int, waist: int, *, back: bool) -> None:
    band = Region(CELL_W, CELL_H).ellipse(cx, waist + 0.5, 9.8, 3.0)
    c.paint(band, SASH, seed=21)
    knot = Region(CELL_W, CELL_H).ellipse(cx - 4.5, waist + 0.5, 2.8, 2.4)
    c.paint(knot, SASH, seed=22)
    tails = [
        ((cx - 6.5, waist + 1.5), (cx - 9.0, waist + 9.0), 1.6),
        ((cx - 4.5, waist + 2.0), (cx - 6.5, waist + 7.5), 1.2),
        ((cx + 5.0, waist + 2.0), (cx + 7.0, waist + 7.5), 1.3),
    ]
    for index, (start, end, radius) in enumerate(tails):
        tail = Region(CELL_W, CELL_H).capsule(start[0], start[1], end[0], end[1], radius)
        _fray(tail, int(end[1]) + 1, 4 + index)
        c.paint(tail, SASH, seed=23 + index)


def _head(c: Canvas, cx: int, cy: int, *, back: bool, hair: int) -> None:
    # Hair volume sits behind the skull.
    hair_back = Region(CELL_W, CELL_H)
    hair_back.ellipse(cx, cy - 1.0, 6.6, 6.5)
    hair_back.ellipse(cx - 5.8, cy + 2.4, 2.2, 3.7)
    hair_back.ellipse(cx + 5.8, cy + 2.4, 2.2, 3.7)
    for index, (sx, ex, ey) in enumerate(
        [
            (cx - 6.3, cx - 7.3, cy + 6.5),
            (cx - 4.8, cx - 5.8, cy + 8.0),
            (cx + 6.3, cx + 7.3, cy + 6.5),
            (cx + 4.8, cx + 5.8, cy + 8.0),
        ]
    ):
        hair_back.capsule(sx, cy + 1, ex + hair, ey, 1.3)
    c.paint(hair_back, HAIR, seed=31)
    # strands catch the light so the hair mass does not read as a flat blob
    for x, y in ((cx - 4, cy - 4), (cx - 3, cy - 5), (cx - 2, cy - 6), (cx + 2, cy - 5), (cx + 3, cy - 4)):
        c.put(x, y, HAIR.palette.highlight)
    for y in range(cy - 1, cy + 4):
        c.put(cx - 6, y, HAIR.palette.light)
        c.put(cx + 6, y + 1, HAIR.palette.shadow)

    if back:
        crown = Region(CELL_W, CELL_H).ellipse(cx, cy - 0.5, 6.0, 6.2)
        c.paint(crown, HAIR, seed=32)
        # tied bandage at the back of the head
        knot = Region(CELL_W, CELL_H).ellipse(cx, cy + 3.6, 2.0, 1.6)
        c.paint(knot, BLINDFOLD, seed=33)
        for index, spread in enumerate((-1.8, 1.8)):
            tail = Region(CELL_W, CELL_H).capsule(
                cx + spread, cy + 3.6, cx + spread * 2.4 + hair, cy + 12.0, 1.1
            )
            c.paint(tail, BLINDFOLD, seed=34 + index)
        return

    face = Region(CELL_W, CELL_H).ellipse(cx, cy + 0.4, 4.9, 5.2)
    jaw = Region(CELL_W, CELL_H).ellipse(cx, cy + 3.0, 3.7, 2.7)
    c.paint(face, SKIN, seed=35)
    c.paint(jaw, SKIN, seed=36)
    # cheek shading / cheekbone
    for side in (-1, 1):
        c.put(cx + side * 4, cy + 2, SKIN.palette.shadow)
        c.put(cx + side * 4, cy + 3, SKIN.palette.shadow)
        c.put(cx + side * 3, cy + 2, SKIN.palette.light)

    fringe = Region(CELL_W, CELL_H)
    fringe.ellipse(cx, cy - 1.8, 6.4, 4.4)
    fringe.erase(Region(CELL_W, CELL_H).ellipse(cx, cy + 2.4, 3.8, 5.0))
    fringe.erase(Region(CELL_W, CELL_H).rect(cx - 12, cy + 5, cx + 12, cy + 14))
    for index, (x0, y0, x1, y1) in enumerate(
        [
            (cx - 5, cy - 3, cx - 6, cy + 3),
            (cx - 3, cy - 4, cx - 4, cy + 2),
            (cx + 5, cy - 3, cx + 6, cy + 3),
            (cx + 3, cy - 4, cx + 4, cy + 2),
            (cx, cy - 5, cx + hair, cy - 2),
        ]
    ):
        fringe.capsule(x0, y0, x1 + hair, y1, 1.0)
    c.paint(fringe, HAIR, seed=37)

    # Blindfold across the eyes.
    band = Region(CELL_W, CELL_H).ellipse(cx, cy + 1.8, 5.3, 1.9)
    band.union(Region(CELL_W, CELL_H).rect(cx - 5, cy + 0.5, cx + 5, cy + 2.6))
    c.paint(band, BLINDFOLD, seed=38)
    # band folds
    c.put(cx - 3, cy + 1, BLINDFOLD.palette.highlight)
    c.put(cx + 1, cy + 1, BLINDFOLD.palette.highlight)
    c.put(cx + 4, cy + 2, BLINDFOLD.palette.highlight)
    tail = Region(CELL_W, CELL_H).capsule(cx + 5, cy + 2.0, cx + 8.5 + hair, cy + 6.5, 1.1)
    c.paint(tail, BLINDFOLD, seed=39)
    tail2 = Region(CELL_W, CELL_H).capsule(cx + 8.0, cy + 5.5, cx + 7.5 + hair, cy + 10.0, 1.0)
    c.paint(tail2, BLINDFOLD, seed=40)

    # loose strands over the band
    c.paint(Region(CELL_W, CELL_H).capsule(cx - 5, cy - 2, cx - 6 + hair, cy + 3, 0.9), HAIR, seed=41)
    c.paint(Region(CELL_W, CELL_H).capsule(cx + 4, cy - 2, cx + 6 + hair, cy + 2, 0.9), HAIR, seed=42)

    c.put(cx - 1, cy + 5, MOUTH)
    c.put(cx, cy + 5, MOUTH)
    c.put(cx + 1, cy + 5, MOUTH)
    c.put(cx + 4, cy + 3, SKIN.palette.light)
    c.put(cx + 4, cy + 4, SKIN.palette.light)


def draw_front(c: Canvas, *, back: bool, bob: int, lean: int, head_dy: int,
               leg_l: int, leg_r: int, arm_l: int, arm_r: int, hair: int,
               arms_override=None, hurt: bool = False, torn_back: bool = False) -> None:
    _ground_shadow(c)
    cx = CX + lean
    waist = int(WAIST_Y + bob)
    top = 19 + bob
    head_cy = int(HEAD_CY + bob + head_dy)

    _legs(c, CX, int(WAIST_Y), leg_l, leg_r, back=back)
    torso, shoulders, neck = _torso(cx, top)
    c.paint(neck, SKIN_DARK, seed=4)
    c.paint(torso, SKIN, seed=5)
    c.paint(shoulders, SKIN, seed=6)
    _torso_detail(c, cx, top, back=back)

    arms = arms_override or _default_arms(cx, top, 0, arm_l, arm_r)
    _arm(c, *arms[0], near=True)
    _arm(c, *arms[1], near=True)

    _sash(c, cx, waist, back=back)
    _head(c, cx, head_cy, back=back, hair=hair)
    if hurt:
        for x, y in ((cx + 4, top + 5), (cx + 5, top + 6), (cx + 6, top + 7), (cx + 5, top + 8)):
            c.put(x, y, BLOOD)


def draw_side(c: Canvas, *, bob: int, lean: int, head_dy: int,
              leg_l: int, leg_r: int, arm_l: int, arm_r: int, hair: int,
              arms_override=None) -> None:
    _ground_shadow(c)
    cx = CX + lean
    waist = int(WAIST_Y + bob)
    head_cy = int(HEAD_CY + bob + head_dy)

    # far leg
    far = Region(CELL_W, CELL_H).capsule(cx + 2.5, waist + 2, cx + 3.5, waist + 11 + leg_l, 5.0)
    _fray(far, waist + 13 + leg_l, 12)
    c.paint(far, PANTS, seed=51)
    c.paint(Region(CELL_W, CELL_H).capsule(cx + 3.5, waist + 12 + leg_l, cx + 3.5, waist + 19 + leg_l, 2.2), WRAP_DARK, seed=52)
    c.paint(Region(CELL_W, CELL_H).ellipse(cx + 3.5, waist + 21.5 + leg_l, 3.0, 1.6), SKIN_DARK, seed=53)
    # near leg
    near = Region(CELL_W, CELL_H).capsule(cx - 2.5, waist + 2, cx - 4.0, waist + 11 + leg_r, 5.2)
    _fray(near, waist + 13 + leg_r, 6)
    c.paint(near, PANTS, seed=54)
    c.paint(Region(CELL_W, CELL_H).capsule(cx - 4.0, waist + 12 + leg_r, cx - 4.5, waist + 19 + leg_r, 2.3), WRAP, seed=55)
    c.paint(Region(CELL_W, CELL_H).ellipse(cx - 5.0, waist + 21.5 + leg_r, 3.4, 1.8), SKIN, seed=56)

    # far arm behind torso
    if arms_override:
        (near_sh, near_el, near_ha), (far_sh, far_el, far_ha) = arms_override
        _arm(c, (far_sh[0] + cx - CX, far_sh[1]), (far_el[0] + cx - CX, far_el[1]), (far_ha[0] + cx - CX, far_ha[1]), near=False)
    else:
        _arm(c, (cx + 3.5, 24 + bob), (cx + 4.5, 30 + bob), (cx + 3.5 + arm_r, 36 + bob), near=False)

    torso = Region(CELL_W, CELL_H).polygon(
        [
            (cx - 4.0, 19 + bob),
            (cx + 4.5, 19 + bob),
            (cx + 5.5, 24 + bob),
            (cx + 5.0, 30 + bob),
            (cx + 3.0, 33 + bob),
            (cx - 3.5, 33 + bob),
            (cx - 6.0, 27 + bob),
            (cx - 6.0, 22 + bob),
        ]
    )
    c.paint(torso, SKIN, seed=57)
    for y in range(21 + bob, 27 + bob):
        c.put(cx - 5, y, SKIN.palette.light)
    c.put(cx - 4, 23 + bob, SKIN.palette.highlight)
    c.put(cx - 4, 24 + bob, SKIN.palette.highlight)
    for y in range(20 + bob, 31 + bob):
        c.put(cx + 5, y, SKIN.palette.shadow)
    for x, y in ((cx + 1, 21 + bob), (cx + 2, 22 + bob), (cx + 3, 23 + bob)):
        c.put(x, y, SKIN.palette.shadow)
        c.put(x, y + 5, SKIN.palette.light)

    # sash with tails front and back
    c.paint(Region(CELL_W, CELL_H).ellipse(cx, waist + 0.5, 6.2, 3.0), SASH, seed=58)
    tail_back = Region(CELL_W, CELL_H).capsule(cx + 5.0, waist + 1.5, cx + 8.0, waist + 10.0, 1.6)
    tail_front = Region(CELL_W, CELL_H).capsule(cx - 5.0, waist + 2.0, cx - 7.0, waist + 8.5, 1.3)
    _fray(tail_back, waist + 11, 4)
    _fray(tail_front, waist + 9, 7)
    c.paint(tail_back, SASH, seed=59)
    c.paint(tail_front, SASH, seed=60)

    # head profile (faces screen-left)
    hair_region = Region(CELL_W, CELL_H)
    hair_region.ellipse(cx + 0.5, head_cy - 1.0, 6.2, 6.3)
    hair_region.ellipse(cx + 5.0, head_cy + 2.5, 2.8, 4.4)
    hair_region.capsule(cx + 4.0, head_cy + 1, cx + 5.0 + hair, head_cy + 10, 1.7)
    hair_region.capsule(cx + 1.5, head_cy + 2, cx + 2.5 + hair, head_cy + 11, 1.3)
    c.paint(hair_region, HAIR, seed=61)

    face = Region(CELL_W, CELL_H).ellipse(cx - 2.0, head_cy + 0.4, 4.6, 5.0)
    c.paint(face, SKIN, seed=62)
    c.put(cx - 6, head_cy + 1, SKIN.palette.light)
    c.put(cx - 7, head_cy + 2, SKIN.palette.light)
    c.put(cx - 6, head_cy + 2, SKIN.palette.base)
    c.put(cx - 6, head_cy + 3, SKIN.palette.shadow)

    fringe = Region(CELL_W, CELL_H).ellipse(cx - 1.2, head_cy - 2.8, 5.4, 2.8)
    fringe.erase(Region(CELL_W, CELL_H).rect(cx - 14, head_cy + 1, cx + 14, head_cy + 16))
    fringe.capsule(cx + 1, head_cy - 2, cx + 3 + hair, head_cy + 2, 1.2)
    c.paint(fringe, HAIR, seed=63)
    band = Region(CELL_W, CELL_H).ellipse(cx - 2, head_cy + 1.6, 4.6, 1.7)
    c.paint(band, BLINDFOLD, seed=64)
    c.put(cx - 4, head_cy + 1, BLINDFOLD.palette.highlight)
    c.put(cx - 1, head_cy + 1, BLINDFOLD.palette.highlight)
    tail = Region(CELL_W, CELL_H).capsule(cx + 2.5, head_cy + 1.6, cx + 6.0 + hair, head_cy + 6.5, 1.1)
    c.paint(tail, BLINDFOLD, seed=65)
    c.put(cx - 5, head_cy + 5, MOUTH)
    c.put(cx - 4, head_cy + 5, MOUTH)

    if arms_override:
        (near_sh, near_el, near_ha), _ = arms_override
        _arm(c, (near_sh[0] + cx - CX, near_sh[1]), (near_el[0] + cx - CX, near_el[1]), (near_ha[0] + cx - CX, near_ha[1]))
    else:
        _arm(c, (cx - 3.5, 24 + bob), (cx - 4.5, 30 + bob), (cx - 5.5 - arm_l, 36 + bob))


# ---------------------------------------------------------------------------
# Special poses
# ---------------------------------------------------------------------------


def _tuck(c: Canvas, *, down: bool = True) -> None:
    _ground_shadow(c, width=8)
    hair = Region(CELL_W, CELL_H).ellipse(CX, 42, 8.0, 6.4)
    c.paint(hair, HAIR, seed=81)
    body = Region(CELL_W, CELL_H).ellipse(CX, 45.5, 9.2, 7.4)
    c.paint(body, PANTS, seed=82)
    c.paint(Region(CELL_W, CELL_H).ellipse(CX, 48.5, 8.2, 4.8), SASH, seed=83)
    skin = Region(CELL_W, CELL_H).ellipse(CX, 38.5, 6.0, 3.4)
    c.paint(skin, SKIN, seed=84)
    head = Region(CELL_W, CELL_H).ellipse(CX, 34.5, 4.6, 4.4)
    c.paint(head, SKIN, seed=85)
    c.paint(Region(CELL_W, CELL_H).ellipse(CX, 32.2, 5.8, 3.8), HAIR, seed=86)
    c.paint(Region(CELL_W, CELL_H).rect(CX - 5, 33.4, CX + 5, 35.4), BLINDFOLD, seed=87)
    c.put(CX - 1, 32, HAIR.palette.highlight)
    # knees tucked into the ball
    c.paint(Region(CELL_W, CELL_H).ellipse(CX - 6, 49, 3.4, 2.4), SKIN, seed=88)
    c.paint(Region(CELL_W, CELL_H).ellipse(CX + 6, 49, 3.4, 2.4), SKIN, seed=89)


def _lying(c: Canvas, *, face_down: bool) -> None:
    _ground_shadow(c, width=15)
    # torso lying horizontally, head at the left
    torso = Region(CELL_W, CELL_H).ellipse(23, 49.5, 11.0, 4.4)
    c.paint(torso, SKIN, seed=161)
    hair = Region(CELL_W, CELL_H)
    hair.ellipse(9.0, 49.0, 5.6, 4.4)
    hair.capsule(7, 47, 5, 53, 1.5)
    c.paint(hair, HAIR, seed=162)
    head = Region(CELL_W, CELL_H).ellipse(12.5, 49.0, 4.0, 3.8)
    c.paint(head, SKIN, seed=163)
    c.paint(Region(CELL_W, CELL_H).rect(10, 47.6, 16, 49.2), BLINDFOLD, seed=164)
    # far arm sprawled above the torso
    c.paint(Region(CELL_W, CELL_H).capsule(20, 45.5, 27, 44.0, 2.2), SKIN_DARK, seed=165)
    c.paint(Region(CELL_W, CELL_H).ellipse(28, 44.0, 2.3, 2.0), SKIN_DARK, seed=166)
    # legs
    legs = Region(CELL_W, CELL_H).ellipse(34.5, 50.0, 7.5, 4.0)
    c.paint(legs, PANTS, seed=167)
    c.paint(Region(CELL_W, CELL_H).capsule(39.5, 50.5, 42.0, 52.0, 1.8), WRAP, seed=168)
    c.paint(Region(CELL_W, CELL_H).ellipse(43.0, 52.5, 2.4, 1.4), SKIN, seed=169)
    # sash tails spilled on the ground
    c.paint(Region(CELL_W, CELL_H).capsule(28, 46.0, 36, 43.5, 1.5), SASH, seed=170)
    if face_down:
        for x, y in ((15, 50), (14, 51), (13, 52)):
            c.put(x, y, SKIN.palette.shadow)


def draw_special(c: Canvas, facing: str, kind: str) -> None:
    if kind == "dodge_crouch":
        _ground_shadow(c)
        _legs(c, CX, int(WAIST_Y), 0, 0, back=False)
        torso, shoulders, neck = _torso(CX, 24)
        c.paint(neck, SKIN_DARK, seed=71)
        c.paint(torso, SKIN, seed=72)
        c.paint(shoulders, SKIN, seed=73)
        _torso_detail(c, CX, 24, back=False)
        arms = (
            ((16.0, 27.0), (13.5, 32.0), (15.5, 35.0)),
            ((32.0, 27.0), (34.5, 32.0), (32.5, 35.0)),
        )
        _arm(c, *arms[0])
        _arm(c, *arms[1])
        _sash(c, CX, 35, back=False)
        _head(c, CX, 17, back=False, hair=0)
        return
    if kind == "dodge_tuck":
        _tuck(c)
        return
    if kind == "dodge_rise":
        _ground_shadow(c)
        _legs(c, CX, int(WAIST_Y), 1, -1, back=False)
        torso, shoulders, neck = _torso(CX, 21)
        c.paint(neck, SKIN_DARK, seed=91)
        c.paint(torso, SKIN, seed=92)
        c.paint(shoulders, SKIN, seed=93)
        _torso_detail(c, CX, 21, back=False)
        arms = (
            ((16.0, 24.0), (13.0, 29.5), (14.0, 33.0)),
            ((32.0, 24.0), (35.0, 29.0), (34.0, 33.0)),
        )
        _arm(c, *arms[0])
        _arm(c, *arms[1])
        _sash(c, CX, 32, back=False)
        _head(c, CX, 14, back=False, hair=1)
        return
    if kind == "attack_windup":
        b = {"bob": -1, "lean": -1, "head_dy": 0}
        arms = (
            ((16.0, 23.0), (13.0, 27.5), (19.0, 26.0)),
            ((32.0, 23.0), (35.0, 27.5), (29.0, 26.0)),
        )
        if facing == "up":
            _draw_attack_body(c, b, arms, back=True)
        elif facing == "side":
            _draw_side_attack(c, "wind")
        else:
            _draw_attack_body(c, b, arms, back=False)
        return
    if kind == "attack_strike":
        b = {"bob": 1, "lean": 1, "head_dy": 0}
        arms = (
            ((16.0, 24.0), (19.0, 30.0), (21.0, 35.0)),
            ((32.0, 24.0), (29.0, 30.0), (27.0, 35.0)),
        )
        if facing == "up":
            _draw_attack_body(c, b, arms, back=True)
        elif facing == "side":
            _draw_side_attack(c, "strike")
        else:
            _draw_attack_body(c, b, arms, back=False)
        return
    if kind == "attack_recover":
        b = {"bob": 0, "lean": 0, "head_dy": 0}
        arms = (
            ((16.0, 24.0), (15.0, 30.0), (17.0, 34.0)),
            ((32.0, 24.0), (33.0, 30.0), (31.0, 34.0)),
        )
        if facing == "up":
            _draw_attack_body(c, b, arms, back=True)
        elif facing == "side":
            _draw_side_attack(c, "recover")
        else:
            _draw_attack_body(c, b, arms, back=False)
        return
    if kind == "hurt":
        b = {"bob": 1, "lean": -2, "head_dy": 1}
        arms = (
            ((16.0, 24.0), (12.0, 27.0), (9.0, 25.0)),
            ((32.0, 24.0), (36.0, 27.0), (39.0, 25.0)),
        )
        if facing == "up":
            _draw_attack_body(c, b, arms, back=True, hurt=True)
        elif facing == "side":
            _draw_side_hurt(c)
        else:
            _draw_attack_body(c, b, arms, back=False, hurt=True)
        return
    if kind == "death_1":
        b = {"bob": 2, "lean": -2, "head_dy": 1}
        arms = (
            ((16.0, 26.0), (12.0, 30.0), (9.0, 27.0)),
            ((32.0, 26.0), (36.0, 30.0), (39.0, 27.0)),
        )
        _draw_attack_body(c, b, arms, back=False)
        return
    if kind == "death_2":
        _ground_shadow(c, width=11)
        legs = Region(CELL_W, CELL_H)
        legs.ellipse(CX - 5, 49, 5.0, 4.0)
        legs.ellipse(CX + 5, 49, 5.0, 4.0)
        c.paint(legs, PANTS, seed=151)
        c.paint(Region(CELL_W, CELL_H).capsule(CX - 6, 49, CX - 6, 53, 1.9), WRAP, seed=152)
        c.paint(Region(CELL_W, CELL_H).capsule(CX + 6, 49, CX + 6, 53, 1.9), WRAP_DARK, seed=153)
        torso, shoulders, neck = _torso(CX, 30)
        c.paint(neck, SKIN_DARK, seed=154)
        c.paint(torso, SKIN, seed=155)
        c.paint(shoulders, SKIN, seed=156)
        _torso_detail(c, CX, 30, back=False)
        arms = (
            ((17.0, 33.0), (13.0, 39.0), (11.0, 43.0)),
            ((31.0, 33.0), (35.0, 39.0), (37.0, 43.0)),
        )
        _arm(c, *arms[0])
        _arm(c, *arms[1])
        _sash(c, CX, 42, back=False)
        _head(c, CX, 23, back=False, hair=0)
        return
    if kind == "death_3":
        _lying(c, face_down=facing == "up")
        # a pixel of lift while the body is still falling
        for y in range(40, CELL_H):
            for x in range(CELL_W):
                pixel = c.pixels[x, y]
                if pixel[3] > 0:
                    c.pixels[x, y] = (0, 0, 0, 0)
                    c.put(x, y - 1, pixel)
        return
    if kind == "death_4":
        _lying(c, face_down=facing == "up")
        return


def _draw_attack_body(c: Canvas, b: dict, arms, *, back: bool, hurt: bool = False) -> None:
    draw_front(
        c,
        back=back,
        bob=b["bob"],
        lean=b["lean"],
        head_dy=b["head_dy"],
        leg_l=1 if b["lean"] >= 0 else -1,
        leg_r=-1 if b["lean"] >= 0 else 1,
        arm_l=0,
        arm_r=0,
        hair=0,
        arms_override=arms,
        hurt=hurt,
    )


def _draw_side_attack(c: Canvas, phase: str) -> None:
    if phase == "wind":
        arms = (
            ((20.0, 24.0), (16.0, 30.0), (19.0, 26.0)),
            ((27.0, 24.0), (31.0, 28.0), (28.0, 25.0)),
        )
        draw_side(c, bob=-1, lean=-1, head_dy=0, leg_l=-1, leg_r=1, arm_l=0, arm_r=0, hair=0, arms_override=arms)
    elif phase == "strike":
        arms = (
            ((20.0, 24.0), (13.0, 28.0), (8.0, 31.0)),
            ((27.0, 24.0), (20.0, 29.0), (14.0, 33.0)),
        )
        draw_side(c, bob=1, lean=2, head_dy=0, leg_l=1, leg_r=-1, arm_l=0, arm_r=0, hair=0, arms_override=arms)
    else:
        arms = (
            ((20.0, 24.0), (16.0, 30.0), (13.0, 33.0)),
            ((27.0, 24.0), (25.0, 30.0), (22.0, 33.0)),
        )
        draw_side(c, bob=0, lean=0, head_dy=0, leg_l=0, leg_r=0, arm_l=0, arm_r=0, hair=0, arms_override=arms)


def _draw_side_hurt(c: Canvas) -> None:
    arms = (
        ((20.0, 24.0), (17.0, 28.0), (18.0, 25.0)),
        ((27.0, 24.0), (32.0, 27.0), (34.0, 24.0)),
    )
    draw_side(c, bob=1, lean=-2, head_dy=1, leg_l=1, leg_r=0, arm_l=0, arm_r=0, hair=0, arms_override=arms)
    for x, y in ((19, 26), (20, 27), (20, 28), (21, 29)):
        c.put(x, y, BLOOD)


# ---------------------------------------------------------------------------
# Frame assembly
# ---------------------------------------------------------------------------


def hero_frame(state: str, facing: str, index: int) -> Image.Image:
    pose = POSES[state][index]
    c = Canvas(CELL_W, CELL_H)
    if "special" in pose:
        draw_special(c, facing, pose["special"])
        return c.image
    if facing == "down":
        draw_front(
            c,
            back=False,
            bob=pose["bob"],
            lean=pose["lean"],
            head_dy=0,
            leg_l=pose["leg_l"],
            leg_r=pose["leg_r"],
            arm_l=pose["arm_l"],
            arm_r=pose["arm_r"],
            hair=pose["hair"],
        )
    elif facing == "up":
        draw_front(
            c,
            back=True,
            bob=pose["bob"],
            lean=pose["lean"],
            head_dy=0,
            leg_l=pose["leg_l"],
            leg_r=pose["leg_r"],
            arm_l=pose["arm_l"],
            arm_r=pose["arm_r"],
            hair=pose["hair"],
        )
    else:
        draw_side(
            c,
            bob=pose["bob"],
            lean=pose["lean"],
            head_dy=0,
            leg_l=pose["leg_l"],
            leg_r=pose["leg_r"],
            arm_l=pose["arm_l"],
            arm_r=pose["arm_r"],
            hair=pose["hair"],
        )
    return c.image


def hero_frames() -> list[Image.Image]:
    frames: list[Image.Image] = []
    for facing in FACINGS:
        for state in ANIMATIONS:
            for index in range(len(POSES[state])):
                frames.append(hero_frame(state, facing, index))
    return frames


def frame_ranges() -> dict[str, tuple[int, int]]:
    ranges: dict[str, tuple[int, int]] = {}
    cursor = 0
    for facing in FACINGS:
        for state in ANIMATIONS:
            count = len(POSES[state])
            ranges[f"{facing}:{state}"] = (cursor, count)
            cursor += count
    return ranges


def render_preview(path, scale: int = 5) -> None:
    frames = hero_frames()
    rows = len(FACINGS)
    columns = sum(len(POSES[s]) for s in ANIMATIONS)
    sheet = Image.new("RGBA", (columns * CELL_W, rows * CELL_H), (26, 30, 40, 255))
    index = 0
    for row, facing in enumerate(FACINGS):
        col = 0
        for state in ANIMATIONS:
            for _ in range(len(POSES[state])):
                shot = Image.new("RGBA", (CELL_W, CELL_H), (30, 34, 45, 255))
                shot.alpha_composite(frames[index])
                sheet.paste(shot, (col * CELL_W, row * CELL_H))
                col += 1
                index += 1
    sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    sheet.save(path)


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "hero_preview.png"
    render_preview(out)
    print(f"preview written: {out}")
