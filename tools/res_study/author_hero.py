"""Герой Rogalik — вид `down`, три уровня исходной детализации (задача 3.1c).

Один художественный замысел (утверждённый образ D7: красная повязка на глазах,
объёмные волосы средней длины, голый атлетичный торс, широкие рваные штаны,
кушак, льняные обмотки, босые стопы) рисуется в трёх собственных разрешениях:

    A: высота 48 px  — действующий стандарт D16
    B: высота 64 px  — исследовательский вариант
    C: высота 96 px  — исследовательский вариант

Пропорции взяты из замера утверждённого референса
(`tools/res_study/measure_reference.py`): ширина головы с волосами 0.140 H,
плечи вместе с руками 0.275 H, фигура ≈7.4 головы, талия уже плеч.

Детализация НЕ масштабируется из одного рисунка: у каждого варианта свои акценты
(при 48 px нет рядов пресса, шрамов и пальцев; при 96 px они есть). Эксперимент
должен показать вложенную художественную работу, а не апскейл.

    python tools/res_study/author_hero.py [a|b|c]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from res_study.form_render import (  # noqa: E402
    Canvas, hash_noise, sdf_capsule, sdf_ellipse, sdf_round_box, smooth_union, union,
)

OUT = ROOT / "game" / "experiments" / "res_study" / "art"
SOURCE = ROOT / "tools" / "res_study" / "source"
REPORTS = ROOT / "reports"

VARIANTS: dict[str, int] = {"a": 48, "b": 64, "c": 96}


def _torn(u: np.ndarray, seed: float) -> np.ndarray:
    """Неровный край ткани: сумма синусов + детерминированный шум."""
    return (np.sin(u * 26.0 + seed) * 0.45 + np.sin(u * 61.0 + seed * 2.3) * 0.25 +
            (hash_noise(np.round(u * 40.0), seed, int(seed * 13) + 5) - 0.5) * 1.1)


def draw_hero(height_px: int) -> Canvas:
    H = float(height_px)
    detail = 0 if height_px <= 48 else (1 if height_px <= 64 else 2)
    canvas = Canvas(int(round(H * 0.76)), int(round(H)))
    cx = canvas.width / 2.0

    def X(u: float) -> float:
        return cx + u * H

    def Y(v: float) -> float:
        return v * H

    def P(px: float) -> float:
        """Пиксели → единицы высоты: 1 px остаётся 1 px на любом размере."""
        return px / H

    # --- опорные пропорции (из замера референса) --------------------------
    head_cx, head_cy = 0.0, 0.062
    skull_rx, skull_ry = 0.045, 0.060
    jaw_cy, jaw_rx, jaw_ry = 0.108, 0.036, 0.032
    chin_v = 0.138
    band_v = 0.083           # повязка на линии глаз
    shoulder_v = 0.196
    torso_shoulder_hw = 0.086
    chest_cy, chest_hw = 0.234, 0.081
    waist_cy, waist_hw = 0.352, 0.067
    hip_cy, hip_hw = 0.424, 0.079
    sash_v = 0.414
    hem_v = 0.792
    ankle_v = 0.888

    arm = {"sh": (0.092, 0.220), "elbow": (0.106, 0.372), "wrist": (0.104, 0.470),
           "hand": (0.105, 0.503)}
    leg = {"hip": 0.046, "knee": 0.050, "ankle": 0.049, "foot": 0.052}

    # --- формы ------------------------------------------------------------

    def torso(x, y):
        # покатые трапеции: от шеи к дельтовидным, а не прямая «перекладина»
        traps = union(
            sdf_capsule(x, y, X(0.0), Y(0.176), X(-0.082), Y(0.212), 0.020 * H, 0.028 * H),
            sdf_capsule(x, y, X(0.0), Y(0.176), X(0.082), Y(0.212), 0.020 * H, 0.028 * H),
        )
        deltoids = union(
            sdf_ellipse(x, y, X(-0.086), Y(0.222), 0.031 * H, 0.034 * H),
            sdf_ellipse(x, y, X(0.086), Y(0.222), 0.031 * H, 0.034 * H),
        )
        chest = sdf_ellipse(x, y, X(0.0), Y(chest_cy + 0.012), chest_hw * H, 0.062 * H)
        waist = sdf_ellipse(x, y, X(0.0), Y(waist_cy), waist_hw * H, 0.060 * H)
        hips = sdf_ellipse(x, y, X(0.0), Y(hip_cy), hip_hw * H, 0.044 * H)
        neck = sdf_capsule(x, y, X(0.0), Y(0.116), X(0.0), Y(0.184), 0.028 * H, 0.034 * H)
        body = smooth_union(traps, deltoids, 0.022 * H)
        body = smooth_union(body, chest, 0.024 * H)
        body = smooth_union(body, waist, 0.030 * H)
        body = smooth_union(body, hips, 0.026 * H)
        return smooth_union(body, neck, 0.014 * H)

    def armpit_wedge(side, x, y):
        """Тёмный клин между рукой и корпусом: силуэт целый, без «дыры» в фоне."""
        s = side
        return sdf_capsule(x, y, X(s * 0.080), Y(0.250), X(s * 0.092), Y(0.482),
                           0.016 * H, 0.012 * H)

    def arm_shape(side, x, y):
        s = side
        upper = sdf_capsule(x, y, X(s * arm["sh"][0]), Y(arm["sh"][1]),
                            X(s * arm["elbow"][0]), Y(arm["elbow"][1]), 0.033 * H, 0.026 * H)
        fore = sdf_capsule(x, y, X(s * arm["elbow"][0]), Y(arm["elbow"][1]),
                           X(s * arm["wrist"][0]), Y(arm["wrist"][1]), 0.026 * H, 0.020 * H)
        return smooth_union(upper, fore, 0.012 * H)

    def hand_shape(side, x, y):
        s = side
        palm = sdf_ellipse(x, y, X(s * arm["hand"][0]), Y(arm["hand"][1]), 0.024 * H, 0.032 * H)
        fingers = sdf_capsule(x, y, X(s * arm["hand"][0]), Y(arm["hand"][1] + 0.012),
                              X(s * (arm["hand"][0] - 0.002)), Y(arm["hand"][1] + 0.042),
                              0.019 * H, 0.014 * H)
        return smooth_union(palm, fingers, 0.008 * H)

    def leg_shape(side, x, y):
        s = side
        thigh = sdf_capsule(x, y, X(s * leg["hip"]), Y(0.436), X(s * leg["knee"]), Y(0.652),
                            0.040 * H, 0.030 * H)
        calf = sdf_capsule(x, y, X(s * leg["knee"]), Y(0.652), X(s * leg["ankle"]), Y(ankle_v),
                           0.032 * H, 0.020 * H)
        return smooth_union(thigh, calf, 0.010 * H)

    def pants_shape(side, x, y):
        s = side
        upper = sdf_capsule(x, y, X(s * 0.048), Y(0.418), X(s * 0.052), Y(0.660),
                            0.052 * H, 0.046 * H)
        lower = sdf_capsule(x, y, X(s * 0.052), Y(0.640), X(s * 0.054), Y(0.830),
                            0.046 * H, 0.041 * H)
        shape = smooth_union(upper, lower, 0.012 * H)
        u = (x - cx) / H
        cut = Y(hem_v + 0.020 * _torn(u * 7.0 + s * 2.0, 3.1 + s))
        return np.maximum(shape, y - cut)

    def wraps_shape(side, x, y):
        s = side
        shin = sdf_capsule(x, y, X(s * 0.0495), Y(0.800), X(s * 0.0485), Y(0.886),
                           0.033 * H, 0.023 * H)
        fore = sdf_capsule(x, y, X(s * 0.1215), Y(0.392), X(s * 0.1275), Y(0.472),
                           0.0265 * H, 0.0195 * H)
        return union(shin, fore)

    def foot_shape(side, x, y):
        s = side
        main = sdf_ellipse(x, y, X(s * leg["foot"]), Y(0.942), 0.031 * H, 0.026 * H,
                           rot=s * 0.20)
        heel = sdf_ellipse(x, y, X(s * (leg["foot"] - 0.003)), Y(0.919), 0.023 * H, 0.016 * H)
        toes = sdf_capsule(x, y, X(s * (leg["foot"] - 0.012)), Y(0.958),
                           X(s * (leg["foot"] + 0.014)), Y(0.966), 0.011 * H, 0.009 * H)
        return smooth_union(smooth_union(main, heel, 0.007 * H), toes, 0.006 * H)

    def head_shape(x, y):
        cranium = sdf_ellipse(x, y, X(head_cx), Y(head_cy), skull_rx * H, skull_ry * H)
        jaw = sdf_ellipse(x, y, X(0.0), Y(jaw_cy), jaw_rx * H, jaw_ry * H)
        return smooth_union(cranium, jaw, 0.012 * H)

    def hair_back(x, y):
        mass = sdf_ellipse(x, y, X(0.0), Y(0.064), 0.068 * H, 0.078 * H)
        left = sdf_capsule(x, y, X(-0.058), Y(0.058), X(-0.064), Y(0.168), 0.026 * H, 0.017 * H)
        right = sdf_capsule(x, y, X(0.058), Y(0.058), X(0.064), Y(0.166), 0.026 * H, 0.017 * H)
        nape = sdf_ellipse(x, y, X(0.0), Y(0.148), 0.050 * H, 0.026 * H)
        return union(mass, left, right, nape)

    def band_shape(x, y):
        band = sdf_round_box(x, y, X(0.0), Y(band_v), 0.047 * H, 0.0135 * H, 0.006 * H)
        knot = sdf_ellipse(x, y, X(-0.045), Y(band_v + 0.005), 0.012 * H, 0.011 * H)
        return union(band, knot)

    def band_tails(x, y):
        t1 = sdf_capsule(x, y, X(-0.052), Y(band_v + 0.010), X(-0.074), Y(0.128),
                         0.0065 * H, 0.0040 * H)
        t2 = sdf_capsule(x, y, X(-0.048), Y(band_v + 0.016), X(-0.062), Y(0.142),
                         0.0055 * H, 0.0035 * H)
        u = (x - cx) / H
        cut = Y(0.146 + 0.010 * _torn(u * 9.0, 7.7))
        return np.maximum(union(t1, t2), y - cut)

    def sash_shape(x, y):
        belt = sdf_round_box(x, y, X(0.0), Y(sash_v), 0.074 * H, 0.021 * H, 0.012 * H)
        left = sdf_ellipse(x, y, X(-0.048), Y(sash_v + 0.014), 0.026 * H, 0.017 * H)
        right = sdf_ellipse(x, y, X(0.046), Y(sash_v + 0.012), 0.024 * H, 0.016 * H)
        return smooth_union(smooth_union(belt, left, 0.010 * H), right, 0.010 * H)

    def sash_tail(x, y):
        t1 = sdf_capsule(x, y, X(-0.056), Y(sash_v + 0.016), X(-0.062), Y(0.500),
                         0.013 * H, 0.008 * H)
        t2 = sdf_capsule(x, y, X(-0.061), Y(0.496), X(-0.055), Y(0.560), 0.008 * H, 0.005 * H)
        u = (x - cx) / H
        cut = Y(0.566 + 0.014 * _torn(u * 11.0, 9.3))
        return np.maximum(union(t1, t2), y - cut)

    # --- рисование: от дальнего плана к ближнему --------------------------
    canvas.paint(hair_back, "hair", ambient=0.16, contrast=0.9, radius=0.052 * H)
    canvas.paint(band_tails, "red_cloth", ambient=0.14, contrast=0.9,
                 radius=0.006 * H, roundness=0.6)

    # голые ноги — под тканью
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: leg_shape(s, x, y), "skin",
                     ambient=0.22, radius=0.034 * H)
    # широкие рваные штаны поверх ног
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: pants_shape(s, x, y), "pants",
                     ambient=0.22, contrast=0.85, radius=0.050 * H)
    # складки ткани: борозды по бокам штанины, без «молнии» по центру
    for side in (-1, 1):
        for i, off in enumerate((-0.026, 0.022)):
            canvas.paint(lambda x, y, s=side, o=off, i=i: sdf_capsule(
                x, y, X(s * 0.050 + o * H), Y(0.500 + 0.014 * i),
                X(s * 0.052 + o * H), Y(0.755), P(0.5), P(0.45)),
                "pants", level=1)
    # тень у рваного края: штанина «висит», а не обрезана
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.052), Y(0.752), X(s * 0.054), Y(0.786), 0.030 * H, 0.024 * H),
            "pants", level=1)
    # световая полоса на передней поверхности бедра
    if detail >= 1:
        for side in (-1, 1):
            canvas.paint(lambda x, y, s=side: sdf_capsule(
                x, y, X(s * 0.032), Y(0.500), X(s * 0.034), Y(0.700), 0.005 * H, 0.004 * H),
                "pants", level=4)
    # обмотки голеней и стопы
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.0495), Y(0.800), X(s * 0.0485), Y(0.886), 0.033 * H, 0.023 * H),
            "linen", ambient=0.22, radius=0.026 * H)
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: foot_shape(s, x, y), "skin",
                     ambient=0.22, radius=0.026 * H)

    canvas.paint(torso, "skin", ambient=0.22, contrast=1.0, radius=0.072 * H,
                 roundness=0.92)
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: arm_shape(s, x, y), "skin",
                     ambient=0.22, radius=0.026 * H)
        canvas.paint(lambda x, y, s=side: hand_shape(s, x, y), "skin",
                     ambient=0.20, radius=0.020 * H)
    # отделение руки от корпуса: тонкая тень по внутреннему контуру руки,
    # а не заливка просвета (иначе получается «чёрная планка»)
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.062), Y(0.248), X(s * 0.090), Y(0.470),
            P(0.55), P(0.5)), "skin", level=1)
    # обмотки предплечий поверх рук
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.1095), Y(0.390), X(s * 0.1135), Y(0.470), 0.0265 * H, 0.0205 * H),
            "linen", ambient=0.22, radius=0.022 * H)
    canvas.paint(sash_shape, "red_cloth", ambient=0.20, radius=0.020 * H, roundness=0.75)
    canvas.paint(sash_tail, "red_cloth", ambient=0.16, radius=0.010 * H, roundness=0.6)

    canvas.paint(head_shape, "skin", ambient=0.24, radius=0.044 * H, roundness=0.84)
    # передние пряди: чёлка над повязкой и пряди у висков
    fringe = [
        (-0.046, 0.030, -0.052, 0.072, 0.017, 0.010),
        (-0.022, 0.024, -0.026, 0.070, 0.018, 0.011),
        (0.002, 0.022, 0.000, 0.066, 0.018, 0.011),
        (0.026, 0.026, 0.028, 0.070, 0.017, 0.010),
        (0.048, 0.032, 0.052, 0.074, 0.016, 0.009),
    ]
    if detail >= 1:
        fringe += [(-0.034, 0.026, -0.040, 0.074, 0.014, 0.008),
                   (0.014, 0.024, 0.016, 0.070, 0.014, 0.008)]
    for (u0, v0, u1, v1, r0, r1) in fringe:
        canvas.paint(lambda x, y, a=u0, b=v0, c=u1, d=v1, r=r0, q=r1: sdf_capsule(
            x, y, X(a), Y(b), X(c), Y(d), r * H, q * H), "hair",
            ambient=0.18, radius=0.012 * H)
    # длинные пряди у висков, обрамляющие лицо
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.052), Y(0.048), X(s * 0.060), Y(0.150), 0.016 * H, 0.010 * H),
            "hair", ambient=0.18, radius=0.013 * H)

    canvas.paint(band_shape, "red_cloth", ambient=0.22, radius=0.012 * H, roundness=0.7)
    if detail >= 1:
        # тень от повязки на скулах и узел
        canvas.paint(lambda x, y: sdf_capsule(x, y, X(-0.036), Y(band_v + 0.016),
                                             X(0.036), Y(band_v + 0.016), 0.0035 * H),
                     "skin", level=1)
        canvas.paint(lambda x, y: sdf_capsule(x, y, X(-0.052), Y(band_v + 0.002),
                                             X(-0.052), Y(band_v + 0.010), 0.004 * H),
                     "red_cloth", level=1)

    # --- акценты формы ----------------------------------------------------
    # Толщина линий задаётся в АБСОЛЮТНЫХ пикселях (P): один пиксель остаётся
    # одним пикселем и при 48, и при 96 px — иначе на 48 px линии исчезают.
    creases = [
        (-0.048, 0.212, -0.014, 0.203, P(0.55)),     # ключица L
        (0.048, 0.212, 0.014, 0.203, P(0.55)),       # ключица R
        (0.000, 0.216, 0.000, 0.284, P(0.5)),        # грудина
        (-0.020, 0.284, -0.058, 0.270, P(0.55)),     # низ пекторали L
        (0.020, 0.284, 0.058, 0.270, P(0.55)),       # низ пекторали R
        (-0.060, 0.292, -0.049, 0.370, P(0.5)),      # косая L
        (0.060, 0.292, 0.049, 0.370, P(0.5)),        # косая R
        (-0.084, 0.218, -0.090, 0.254, P(0.5)),      # дельта L
        (0.084, 0.218, 0.090, 0.254, P(0.5)),        # дельта R
        (-0.068, 0.404, -0.034, 0.418, P(0.5)),      # складка кушака L
        (0.068, 0.404, 0.034, 0.418, P(0.5)),        # складка кушака R
        (-0.030, 0.430, -0.008, 0.448, P(0.5)),      # пах L
        (0.030, 0.430, 0.008, 0.448, P(0.5)),        # пах R
        (-0.026, 0.144, 0.026, 0.144, P(0.45)),      # линия челюсти
    ]
    if detail >= 1:
        creases += [
            (-0.026, 0.310, 0.026, 0.310, P(0.5)),   # ряд пресса 1
            (-0.026, 0.336, 0.026, 0.336, P(0.5)),   # ряд пресса 2
            (-0.001, 0.298, -0.001, 0.346, P(0.45)),  # белая линия живота
            (-0.110, 0.272, -0.116, 0.306, P(0.5)),  # бицепс L
            (0.110, 0.272, 0.116, 0.306, P(0.5)),    # бицепс R
            (0.000, 0.101, 0.000, 0.114, P(0.45)),   # переносица
            (-0.011, 0.126, 0.011, 0.126, P(0.45)),  # линия рта
        ]
    if detail >= 2:
        creases += [
            (-0.026, 0.360, 0.026, 0.360, P(0.5)),   # ряд пресса 3
            (-0.030, 0.398, -0.014, 0.408, P(0.45)),
            (0.030, 0.398, 0.014, 0.408, P(0.45)),
        ]
    for (u0, v0, u1, v1, r) in creases:
        canvas.paint(lambda x, y, a=u0, b=v0, c=u1, d=v1, rr=r: sdf_capsule(
            x, y, X(a), Y(b), X(c), Y(d), rr, rr),
            "skin", level=1)

    # --- детализация по уровню -------------------------------------------
    if detail >= 1:
        for (u0, v0, u1, v1) in [(-0.040, 0.040, -0.046, 0.070),
                                 (0.006, 0.034, 0.008, 0.062),
                                 (0.040, 0.042, 0.046, 0.068)]:
            canvas.paint(lambda x, y, a=u0, b=v0, c=u1, d=v1: sdf_capsule(
                x, y, X(a), Y(b), X(c), Y(d), P(0.5), P(0.4)),
                "hair", level=6)
    if detail >= 1:
        # швы обмоток
        seams = []
        for side in (-1, 1):
            for k in range(3):
                vv = 0.806 + 0.026 * k
                seams.append((side * 0.049, vv, side * 0.048, vv + 0.004))
            for k in range(2):
                vv = 0.400 + 0.026 * k
                seams.append((side * 0.121, vv, side * 0.126, vv + 0.004))
        for (u0, v0, u1, v1) in seams:
            canvas.paint(lambda x, y, a=u0, b=v0, c=u1, d=v1: sdf_capsule(
                x, y, X(a), Y(b), X(c), Y(d), P(0.45)),
                "linen", level=1)
    if detail >= 2:
        # шрамы как на утверждённом референсе
        for (u0, v0, u1, v1) in [(-0.050, 0.238, -0.028, 0.252),
                                 (0.036, 0.222, 0.052, 0.240),
                                 (-0.086, 0.264, -0.077, 0.290)]:
            canvas.paint(lambda x, y, a=u0, b=v0, c=u1, d=v1: sdf_capsule(
                x, y, X(a), Y(b), X(c), Y(d), P(0.4)),
                "skin", level=6)
        # пальцы на стопах
        for side in (-1, 1):
            for k, off in enumerate((-0.019, -0.006, 0.007)):
                canvas.paint(lambda x, y, s=side, o=off, k=k: sdf_capsule(
                    x, y, X(s * (0.052 + o)), Y(0.960 - 0.002 * k),
                    X(s * (0.052 + o) * 1.02), Y(0.974 - 0.002 * k), P(0.45)),
                    "skin", level=4)

    canvas.outline()
    return canvas


def render(variant: str) -> Path:
    height = VARIANTS[variant]
    canvas = draw_hero(height)
    image = canvas.to_image()
    target = OUT / variant / f"hero_down_{height}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    SOURCE.mkdir(parents=True, exist_ok=True)
    image.save(SOURCE / f"hero_down_{height}.png")
    opaque = int(canvas.alpha.sum())
    print(f"{variant.upper()} {image.width}x{image.height} px  непрозрачных={opaque}  "
          f"цветов={len(canvas.palette())}  {target.relative_to(ROOT).as_posix()}")
    return target


def make_sheet() -> Path:
    tiles = []
    labels = []
    for variant, height in VARIANTS.items():
        img = Image.open(OUT / variant / f"hero_down_{height}.png").convert("RGBA")
        tiles.append(img.resize((img.width * 6, img.height * 6), Image.NEAREST))
        labels.append(f"{variant.upper()} {height}px")
    gap = 28
    width = sum(t.width for t in tiles) + gap * (len(tiles) + 1)
    height_px = max(t.height for t in tiles) + 2 * gap
    sheet = Image.new("RGB", (width, height_px), (24, 21, 28))
    x = gap
    for tile in tiles:
        sheet.paste(tile, (x, gap), tile)
        x += tile.width + gap
    path = REPORTS / "stage3c_hero_abc_x6.png"
    sheet.save(path)
    print(f"лист: {path.relative_to(ROOT).as_posix()} {sheet.width}x{sheet.height} ({', '.join(labels)})")
    return path


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for variant in VARIANTS:
        if only and variant != only:
            continue
        render(variant)
    make_sheet()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
