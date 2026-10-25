"""Герой Rogalik — эталонный образ в ракурсе three-quarter top-down (задача 3.1d).

Пропорции взяты не на глаз: они прочитаны по игровому look-референсу
(`tools/res_study/measure_look_hero.py`, сетка по кадру) и по замеру
утверждённого героя (`measure_reference.py`). Главный вывод замера: при камере
сверху под углом голова занимает ~0.20 высоты фигуры, плечи широкие и плоские
сверху, корпус сжат, повязка лежит по ПЕРЕДНЕЙ нижней части массы волос, а
лицо — только узкий клин (нос, скулы, челюсть) под повязкой.

Автор работает слоями, как художник, а не «одним SDF-рендером»:

    П1  силуэт: дальние слои (масса волос, дальняя рука, ноги, штаны, стопы)
    П2  корпус: плоские плоскости сверху + фронтальная плоскость, выемка шеи
    П3  кушак, узел и свисающие концы ткани
    П4  ближняя рука: плечо, предплечье в обмотках, кулак
    П5  голова: череп, уши, клин лица, масса волос с вырезом, пряди, повязка
    П6  свет: тёплый ключевой слева, холодный контровой справа, окклюзия,
        тёплый отблеск земли снизу
    П7  контур 1 px (только от края изображения)

Детализация у 48 и 96 px разная по замыслу (пробор, витки обмоток, пальцы,
шрамы — только на 96).

    python tools/res_study/author_hero34.py [--analyse]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from res_study.form_render import (  # noqa: E402
    Canvas, hash_noise, ramp_rgb, sdf_capsule, sdf_ellipse, sdf_round_box, smooth_union,
    union,
)

OUT = ROOT / "game" / "experiments" / "res_study" / "art" / "hero34"
SOURCE = ROOT / "tools" / "res_study" / "source"
REPORTS = ROOT / "reports"

VARIANTS = {"a": 48, "b": 96}
DETAIL = {48: 0, 96: 1}


def _wobble(t: np.ndarray, seed: float, freq: float = 9.0) -> np.ndarray:
    return (np.sin(t * freq + seed) * 0.55 + np.sin(t * freq * 2.3 + seed * 1.7) * 0.28 +
            (hash_noise(np.round(t * 30.0), seed, int(seed * 11) + 3) - 0.5) * 0.8)


def draw(height_px: int) -> Canvas:
    H = float(height_px)
    detail = DETAIL[height_px]
    canvas = Canvas(int(round(H * 0.80)), int(round(H)))
    cx = canvas.width / 2.0

    def X(u: float) -> float:
        return cx + u * H

    def Y(v: float) -> float:
        return v * H

    def P(px: float) -> float:
        return px / H

    # --- АВТОРСКИЕ ЯКОРЯ ПРОПОРЦИЙ (three-quarter top-down) ---------------
    hair_top = 0.020
    hair_c = (0.002, 0.080)      # масса волос видна сверху
    hair_rx, hair_ry = 0.066, 0.058
    band_v0, band_v1 = 0.146, 0.176   # повязка по передней нижней части головы
    face_v0, face_v1 = 0.172, 0.224   # клин лица: скулы, нос, челюсть
    neck_v0, neck_v1 = 0.218, 0.256
    shoulder_v = 0.262
    shoulder_hw = 0.118
    chest_v, chest_hw = 0.300, 0.090
    waist_v, waist_hw = 0.372, 0.068
    hip_v, hip_hw = 0.448, 0.086
    sash_v0, sash_v1 = 0.404, 0.452
    hem_v = 0.788
    ankle_v = 0.882
    foot_v = 0.928

    near = {"sh": (0.108, 0.268), "elbow": (0.118, 0.368), "wrist": (0.116, 0.448),
            "hand": (0.114, 0.482)}
    far = {"sh": (-0.106, 0.264), "elbow": (-0.114, 0.364), "wrist": (-0.112, 0.444),
           "hand": (-0.110, 0.478)}
    leg = {"hip": 0.048, "knee": 0.052, "ankle": 0.052, "foot": 0.056}

    # --- ручные операции ---------------------------------------------------
    def stamp(sdf_fn, ramp: str, level: int, *, stipple: float = 0.0, seed: int = 5,
              invert: bool = False) -> None:
        cover = canvas.coverage(sdf_fn)
        sel = cover >= 0.5
        if stipple > 0.0:
            gx, gy = canvas.grid(1)
            noise = hash_noise(gx, gy, seed)
            sel &= (noise < stipple) if invert else (noise >= stipple)
        if not sel.any():
            return
        canvas.color[sel] = ramp_rgb(ramp)[level]
        canvas.alpha[sel] = True

    def stroke(points, width_px: float, ramp: str, level: int, *, stipple: float = 0.0,
               seed: int = 3) -> None:
        for (u0, v0), (u1, v1) in zip(points[:-1], points[1:]):
            def fn(x, y, a=u0, b=v0, c=u1, d=v1):
                return sdf_capsule(x, y, X(a), Y(b), X(c), Y(d), P(width_px))
            stamp(fn, ramp, level, stipple=stipple, seed=seed)

    # =====================================================================
    # П1. Дальние слои силуэта
    # =====================================================================
    def hair_back(x, y):
        """Масса волос: сверху видна почти круглая шапка, сзади — объём."""
        crown = sdf_ellipse(x, y, X(hair_c[0]), Y(hair_c[1]), hair_rx * H, hair_ry * H)
        back = sdf_ellipse(x, y, X(hair_c[0] * 0.5), Y(hair_c[1] - 0.020),
                           0.054 * H, 0.044 * H)
        return smooth_union(crown, back, 0.012 * H)

    canvas.paint(hair_back, "hair", ambient=0.14, contrast=0.9, radius=0.055 * H,
                 roundness=0.95)

    def far_arm(x, y):
        upper = sdf_capsule(x, y, X(far["sh"][0]), Y(far["sh"][1]),
                            X(far["elbow"][0]), Y(far["elbow"][1]), 0.030 * H, 0.023 * H)
        fore = sdf_capsule(x, y, X(far["elbow"][0]), Y(far["elbow"][1]),
                           X(far["wrist"][0]), Y(far["wrist"][1]), 0.023 * H, 0.018 * H)
        return smooth_union(upper, fore, 0.010 * H)

    canvas.paint(far_arm, "skin", ambient=0.16, contrast=0.85, radius=0.028 * H)

    def leg_shape(side, x, y):
        s = side
        thigh = sdf_capsule(x, y, X(s * leg["hip"]), Y(0.470), X(s * leg["knee"]), Y(0.660),
                            0.044 * H, 0.034 * H)
        calf = sdf_capsule(x, y, X(s * leg["knee"]), Y(0.660), X(s * leg["ankle"]), Y(0.880),
                           0.034 * H, 0.021 * H)
        return smooth_union(thigh, calf, 0.010 * H)

    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: leg_shape(s, x, y), "skin", ambient=0.18,
                     radius=0.034 * H)

    def pants_shape(side, x, y):
        """Широкие штаны: сверху сливаются у пояса, ниже читается разделение."""
        s = side
        upper = sdf_capsule(x, y, X(s * 0.048), Y(0.438), X(s * 0.052), Y(0.660),
                            0.052 * H, 0.046 * H)
        lower = sdf_capsule(x, y, X(s * 0.052), Y(0.640), X(s * 0.054), Y(0.810),
                            0.046 * H, 0.042 * H)
        shape = smooth_union(upper, lower, 0.010 * H)
        u = (x - cx) / H
        cut = Y(hem_v + 0.020 * _wobble(u * 6.0 + s * 2.0, 4.7 + s))
        return np.maximum(shape, y - cut)

    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: pants_shape(s, x, y), "pants", ambient=0.18,
                     contrast=0.85, radius=0.050 * H)

    # складки вдоль цилиндра ноги и свет на передней плоскости
    for side in (-1, 1):
        stroke([(side * 0.052 - 0.026, 0.520), (side * 0.058 - 0.028, 0.780)],
               1.0, "pants", 1, stipple=0.5, seed=11)
        stroke([(side * 0.052 + 0.022, 0.520), (side * 0.058 + 0.024, 0.780)],
               1.0, "pants", 1, stipple=0.5, seed=13)
        if detail >= 1:
            stroke([(side * 0.038, 0.500), (side * 0.042, 0.760)], 1.0, "pants", 4,
                   stipple=0.4, seed=17)
    # тень под рваным краем — штанина висит над обмоткой
    for side in (-1, 1):
        stamp(lambda x, y, s=side: sdf_round_box(x, y, X(s * 0.054), Y(hem_v + 0.012),
                                                 0.042 * H, 0.009 * H, 0.004 * H),
              "pants", 0, stipple=0.25, seed=19)

    # обмотки голеней
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.052), Y(0.790), X(s * 0.052), Y(0.876), 0.030 * H, 0.022 * H),
            "linen", ambient=0.18, radius=0.024 * H)
    if detail >= 1:
        for side in (-1, 1):
            for k in range(3):
                vv = 0.806 + 0.026 * k
                stroke([(side * 0.052 - 0.024, vv), (side * 0.052 + 0.024, vv + 0.002)],
                       1.0, "linen", 1)

    # стопы сверху: вытянуты к зрителю
    def foot_shape(side, x, y):
        s = side
        main = sdf_ellipse(x, y, X(s * leg["foot"]), Y(foot_v), 0.029 * H, 0.038 * H,
                           rot=s * 0.10)
        toes = sdf_ellipse(x, y, X(s * (leg["foot"] + 0.002)), Y(foot_v + 0.034),
                           0.025 * H, 0.019 * H)
        return smooth_union(main, toes, 0.010 * H)

    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: foot_shape(s, x, y), "skin", ambient=0.20,
                     radius=0.030 * H)
    if detail >= 1:
        for side in (-1, 1):
            for off in (-0.016, -0.005, 0.006, 0.016):
                stroke([(side * (leg["foot"] + off), foot_v + 0.050),
                        (side * (leg["foot"] + off), foot_v + 0.056)], 1.0, "skin", 5)

    # =====================================================================
    # П2. Корпус
    # =====================================================================
    def torso(x, y):
        traps = union(
            sdf_capsule(x, y, X(0.0), Y(0.238), X(-0.108), Y(0.258), 0.024 * H, 0.032 * H),
            sdf_capsule(x, y, X(0.0), Y(0.238), X(0.108), Y(0.258), 0.024 * H, 0.032 * H),
        )
        shoulders = union(
            sdf_ellipse(x, y, X(-0.100), Y(0.272), 0.032 * H, 0.026 * H),
            sdf_ellipse(x, y, X(0.100), Y(0.272), 0.032 * H, 0.026 * H),
        )
        chest = sdf_ellipse(x, y, X(0.0), Y(chest_v), chest_hw * H, 0.048 * H)
        waist = sdf_ellipse(x, y, X(0.0), Y(waist_v), waist_hw * H, 0.040 * H)
        hips = sdf_ellipse(x, y, X(0.0), Y(hip_v), hip_hw * H, 0.034 * H)
        neck = sdf_capsule(x, y, X(0.0), Y(neck_v0 - 0.004), X(0.0), Y(neck_v1),
                           0.034 * H, 0.038 * H)
        body = smooth_union(traps, shoulders, 0.016 * H)
        body = smooth_union(body, chest, 0.018 * H)
        body = smooth_union(body, waist, 0.022 * H)
        body = smooth_union(body, hips, 0.020 * H)
        body = smooth_union(body, neck, 0.012 * H)
        notch = sdf_ellipse(x, y, X(0.0), Y(0.246), 0.018 * H, 0.010 * H)
        return np.maximum(body, -notch)

    canvas.paint(torso, "skin", ambient=0.20, contrast=0.95, radius=0.072 * H,
                 roundness=0.88)

    # =====================================================================
    # П3. Кушак
    # =====================================================================
    def sash(x, y):
        belt = sdf_round_box(x, y, (X(0.0)), (Y(sash_v0) + Y(sash_v1)) / 2,
                             0.080 * H, (Y(sash_v1) - Y(sash_v0)) / 2, 0.012 * H)
        knot = sdf_ellipse(x, y, X(-0.068), Y(sash_v1 - 0.004), 0.022 * H, 0.016 * H)
        return smooth_union(belt, knot, 0.008 * H)

    def sash_tail(x, y):
        t1 = sdf_capsule(x, y, X(-0.074), Y(sash_v1 + 0.010), X(-0.080), Y(0.520),
                         0.014 * H, 0.009 * H)
        t2 = sdf_capsule(x, y, X(-0.078), Y(0.512), X(-0.070), Y(0.566),
                         0.009 * H, 0.006 * H)
        u = (x - cx) / H
        cut = Y(0.572 + 0.016 * _wobble(u * 10.0, 8.3))
        return np.maximum(union(t1, t2), y - cut)

    canvas.paint(sash, "red_cloth", ambient=0.20, contrast=0.9, radius=0.020 * H,
                 roundness=0.7)
    canvas.paint(sash_tail, "red_cloth", ambient=0.16, radius=0.010 * H, roundness=0.6)

    # =====================================================================
    # П4. Ближняя рука
    # =====================================================================
    def near_arm(x, y):
        upper = sdf_capsule(x, y, X(near["sh"][0]), Y(near["sh"][1]),
                            X(near["elbow"][0]), Y(near["elbow"][1]), 0.032 * H, 0.024 * H)
        fore = sdf_capsule(x, y, X(near["elbow"][0]), Y(near["elbow"][1]),
                           X(near["wrist"][0]), Y(near["wrist"][1]), 0.024 * H, 0.018 * H)
        return smooth_union(upper, fore, 0.010 * H)

    def near_hand(x, y):
        palm = sdf_ellipse(x, y, X(near["hand"][0]), Y(near["hand"][1]), 0.024 * H,
                           0.028 * H)
        fingers = sdf_capsule(x, y, X(near["hand"][0] - 0.002), Y(near["hand"][1] + 0.014),
                              X(near["hand"][0] - 0.004), Y(near["hand"][1] + 0.040),
                              0.019 * H, 0.014 * H)
        return smooth_union(palm, fingers, 0.007 * H)

    # мостик кожи: закрывает подпиксельные щели между рукой и корпусом
    # (иначе контур заливает их чёрным и получаются «провалы» в силуэте)
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_capsule(
            x, y, X(s * 0.062), Y(0.286), X(s * 0.082), Y(0.436), 0.016 * H, 0.013 * H),
            "skin", ambient=0.18, radius=0.020 * H)
    canvas.paint(near_arm, "skin", ambient=0.20, radius=0.028 * H)
    # предплечье в льняных обмотках
    canvas.paint(lambda x, y: sdf_capsule(
        x, y, X(near["elbow"][0] - 0.002), Y(0.392), X(near["wrist"][0] - 0.001), Y(0.458),
        0.0250 * H, 0.0190 * H), "linen", ambient=0.18, radius=0.021 * H)
    canvas.paint(near_hand, "skin", ambient=0.18, radius=0.020 * H)
    if detail >= 1:
        for k in range(2):
            vv = 0.404 + 0.026 * k
            stroke([(near["elbow"][0] - 0.030, vv), (near["wrist"][0] + 0.026, vv + 0.002)],
                   1.0, "linen", 1)
        for k in range(3):
            stroke([(near["hand"][0] - 0.016 + 0.007 * k, 0.494),
                    (near["hand"][0] - 0.016 + 0.007 * k, 0.508)], 1.0, "skin", 2)

    # =====================================================================
    # П5. Голова
    # =====================================================================
    # череп под волосами
    canvas.paint(lambda x, y: sdf_ellipse(x, y, X(0.0), Y(0.104), 0.058 * H, 0.062 * H),
                 "skin", ambient=0.14, contrast=0.6, radius=0.050 * H)
    # уши
    for side in (-1, 1):
        canvas.paint(lambda x, y, s=side: sdf_ellipse(
            x, y, X(s * 0.056), Y(0.158), 0.014 * H, 0.018 * H), "skin", ambient=0.18,
            radius=0.012 * H)

    def face_shape(x, y):
        """Клин лица: скулы, нос, челюсть. Всё выше закрыто повязкой и волосами."""
        upper = sdf_ellipse(x, y, X(0.0), Y(face_v0 + 0.020), 0.046 * H, 0.028 * H)
        jaw = sdf_ellipse(x, y, X(0.0), Y(face_v1 - 0.012), 0.030 * H, 0.020 * H)
        return smooth_union(upper, jaw, 0.008 * H)

    canvas.paint(face_shape, "skin", ambient=0.24, contrast=0.85, radius=0.032 * H)

    def hair_crown(x, y):
        """Волосы сверху: шапка с вырезом под лицо спереди."""
        mass = hair_back(x, y)
        cut = sdf_ellipse(x, y, X(0.0), Y(0.252), 0.050 * H, 0.090 * H)
        return np.maximum(mass, -cut)

    canvas.paint(hair_crown, "hair", ambient=0.22, contrast=1.0, radius=0.052 * H,
                 roundness=0.9)

    # пробор (виден сверху) и пряди по краю
    if detail >= 1:
        stroke([(-0.012, 0.026), (0.000, 0.058), (0.010, 0.092)], 1.0, "hair", 0,
               stipple=0.5, seed=23)
    # пряди прилегают к массе волос и идут вниз-наружу, а не торчат вверх
    locks = [(-0.052, 0.128, -0.068, 0.176, 0.014, 0.009),
             (-0.058, 0.096, -0.072, 0.140, 0.013, 0.008),
             (0.050, 0.126, 0.066, 0.172, 0.014, 0.009),
             (0.056, 0.094, 0.070, 0.138, 0.013, 0.008),
             (-0.026, 0.020, -0.020, 0.044, 0.012, 0.009),
             (0.028, 0.020, 0.022, 0.044, 0.012, 0.009)]
    for (u0, v0, u1, v1, r0, r1) in locks:
        canvas.paint(lambda x, y, a=u0, b=v0, c=u1, d=v1, r=r0, q=r1: sdf_capsule(
            x, y, X(a), Y(b), X(c), Y(d), r * H, q * H), "hair", ambient=0.18,
            radius=0.011 * H)

    # повязка: широкая полоса по передней нижней части головы, с узлом слева
    def band_shape(x, y):
        cy_band = (band_v0 + band_v1) / 2
        strip = sdf_round_box(x, y, X(0.0), Y(cy_band), 0.054 * H,
                              (band_v1 - band_v0) / 2 * H, 0.006 * H)
        # полоса повторяет кривизну головы: края опускаются
        curve = np.abs((y - Y(cy_band)) - ((x - cx) ** 2) / (0.50 * H * H) * H) \
            - (band_v1 - band_v0) / 2 * H * 1.05
        strip = np.maximum(strip, curve)
        knot = sdf_ellipse(x, y, X(-0.056), Y(cy_band + 0.002), 0.014 * H, 0.012 * H)
        return union(strip, knot)

    def band_tails(x, y):
        t1 = sdf_capsule(x, y, X(-0.062), Y(band_v1 - 0.006), X(-0.080), Y(0.216),
                         0.008 * H, 0.0045 * H)
        t2 = sdf_capsule(x, y, X(-0.056), Y(band_v1), X(-0.068), Y(0.226),
                         0.006 * H, 0.0035 * H)
        u = (x - cx) / H
        cut = Y(0.230 + 0.010 * _wobble(u * 12.0, 6.1))
        return np.maximum(union(t1, t2), y - cut)

    canvas.paint(band_tails, "red_cloth", ambient=0.12, radius=0.006 * H, roundness=0.6)
    canvas.paint(band_shape, "red_cloth", ambient=0.22, contrast=0.95, radius=0.010 * H,
                 roundness=0.7)

    # =====================================================================
    # П6. Свет: тепло слева, холод справа, окклюзия, отблеск земли
    # =====================================================================
    # тёплый ключевой: верхние плоскости плеч и макушка
    stamp(lambda x, y: sdf_ellipse(x, y, X(-0.118), Y(0.264), 0.036 * H, 0.016 * H),
          "skin", 6, stipple=0.28, seed=31)
    stamp(lambda x, y: sdf_ellipse(x, y, X(-0.060), Y(0.244), 0.040 * H, 0.014 * H),
          "skin", 5, stipple=0.5, seed=37)
    stamp(lambda x, y: sdf_ellipse(x, y, X(-0.026), Y(0.058), 0.032 * H, 0.020 * H),
          "hair", 6, stipple=0.45, seed=43)
    # верхняя плоскость кушака
    stamp(lambda x, y: sdf_round_box(x, y, X(-0.020), Y(sash_v0 + 0.008), 0.060 * H,
                                     0.007 * H, 0.004 * H), "red_cloth", 5, stipple=0.35,
          seed=41)
    # лицо: свет на скуле слева, тень справа
    stamp(lambda x, y: sdf_ellipse(x, y, X(-0.020), Y(0.196), 0.018 * H, 0.014 * H),
          "skin", 6, stipple=0.3, seed=47)

    # холодный контровой справа
    stroke([(0.152, 0.286), (0.158, 0.330)], 1.0, "rim_cold", 2, stipple=0.3, seed=51)
    stroke([(0.166, 0.380), (0.162, 0.440)], 1.0, "rim_cold", 2, stipple=0.35, seed=53)
    stroke([(0.104, 0.480), (0.108, 0.560)], 1.0, "rim_cold", 1, stipple=0.4, seed=59)
    stroke([(0.104, 0.600), (0.108, 0.770)], 1.0, "rim_cold", 1, stipple=0.5, seed=61)
    stroke([(0.082, 0.800), (0.080, 0.868)], 1.0, "rim_cold", 2, stipple=0.45, seed=63)
    stroke([(0.058, 0.030), (0.070, 0.086), (0.066, 0.140)], 1.0, "rim_cold", 2,
           stipple=0.4, seed=67)

    # окклюзия: под повязкой, под челюстью, под грудью, между рукой и корпусом
    stroke([(-0.032, band_v1 + 0.004), (0.032, band_v1 + 0.004)], 1.0, "skin", 1,
           stipple=0.3, seed=71)
    stamp(lambda x, y: sdf_ellipse(x, y, X(0.0), Y(face_v1 + 0.006), 0.026 * H, 0.008 * H),
          "skin", 1, stipple=0.35, seed=73)
    stroke([(-0.018, 0.344), (-0.062, 0.334)], 1.0, "skin", 1, stipple=0.4, seed=79)
    stroke([(0.018, 0.344), (0.062, 0.334)], 1.0, "skin", 1, stipple=0.4, seed=83)
    stroke([(-0.072, 0.348), (-0.060, 0.402)], 1.0, "skin", 1, stipple=0.35, seed=89)
    stroke([(0.074, 0.346), (0.062, 0.402)], 1.0, "skin", 1, stipple=0.35, seed=91)
    # отделение руки от корпуса (мягко, чтобы не читалось дырой)
    stroke([(0.096, 0.300), (0.108, 0.380), (0.112, 0.440)], 1.0, "skin", 1, stipple=0.45,
           seed=97)
    stroke([(-0.094, 0.296), (-0.104, 0.372)], 1.0, "skin", 1, stipple=0.5, seed=99)
    # тень на штанах под кушаком
    stamp(lambda x, y: sdf_round_box(x, y, X(0.0), Y(sash_v1 + 0.018), 0.090 * H,
                                     0.008 * H, 0.004 * H), "pants", 0, stipple=0.3,
          seed=101)

    # тёплый отблеск земли снизу-слева
    # тёплый отблеск земли — только на кожу левой руки, не на ткань
    pass
    if detail >= 1:
        stroke([(-0.118, 0.404), (-0.122, 0.442)], 1.0, "skin_warm", 2, stipple=0.4,
               seed=109)

    canvas.outline()
    return canvas


# --- контур силуэта для LightOccluder2D (динамическая тень героя) ----------


def silhouette_polygon(image: Image.Image, tolerance: float = 0.9) -> list[list[float]]:
    """Внешний контур по границам пикселей, затем упрощение Дугласа—Пекера."""
    alpha = np.asarray(image.convert("RGBA"))[..., 3] > 0
    h, w = alpha.shape
    edges: dict[tuple[int, int], tuple[int, int]] = {}
    # ориентированные единичные рёбра вдоль границы силуэта (обход по часовой)
    for y in range(h):
        for x in range(w):
            if not alpha[y, x]:
                continue
            if y == 0 or not alpha[y - 1, x]:
                edges[(x, y)] = (x + 1, y)              # верх
            if x == w - 1 or not alpha[y, x + 1]:
                edges[(x + 1, y)] = (x + 1, y + 1)      # право
            if y == h - 1 or not alpha[y + 1, x]:
                edges[(x + 1, y + 1)] = (x, y + 1)      # низ
            if x == 0 or not alpha[y, x - 1]:
                edges[(x, y + 1)] = (x, y)              # лево
    loops: list[list[tuple[int, int]]] = []
    unused = dict(edges)
    while unused:
        start = next(iter(unused))
        loop = [start]
        cur = start
        while True:
            nxt = unused.pop(cur, None)
            if nxt is None:
                break
            loop.append(nxt)
            cur = nxt
            if cur == start:
                break
        if len(loop) > 4:
            loops.append(loop)
    if not loops:
        return []

    def area(loop):
        pts = np.array(loop, dtype=np.float64)
        return 0.5 * abs(np.dot(pts[:, 0], np.roll(pts[:, 1], -1)) -
                         np.dot(pts[:, 1], np.roll(pts[:, 0], -1)))

    best = max(loops, key=area)
    pts = np.array(best, dtype=np.float64)

    def rdp(points: np.ndarray, eps: float) -> np.ndarray:
        if len(points) < 3:
            return points
        a, b = points[0], points[-1]
        ab = b - a
        norm = float(np.hypot(ab[0], ab[1])) or 1.0
        dx = points[:, 0] - a[0]
        dy = points[:, 1] - a[1]
        dist = np.abs(ab[0] * dy - ab[1] * dx) / norm
        idx = int(np.argmax(dist))
        if dist[idx] > eps:
            left = rdp(points[: idx + 1], eps)
            right = rdp(points[idx:], eps)
            return np.vstack([left[:-1], right])
        return np.vstack([a, b])

    simplified = rdp(pts, tolerance)
    return [[round(float(px) - w / 2.0, 2), round(float(py) - h / 2.0, 2)]
            for px, py in simplified]


# --- анализ силуэта (объективная проверка пропорций) ----------------------


def analyse(image: Image.Image, height_px: int) -> dict:
    alpha = np.asarray(image.convert("RGBA"))[..., 3] > 0
    ys, xs = np.nonzero(alpha)
    top, bottom = int(ys.min()), int(ys.max())
    height = bottom - top + 1
    rows = []
    for y in range(top, bottom + 1):
        row = np.nonzero(alpha[y])[0]
        runs = 1
        if len(row) > 1:
            runs = 1 + int((np.diff(row) > 1).sum())
        rows.append((y, int(row.min()), int(row.max()), int(row.max() - row.min() + 1), runs))
    widths = np.array([r[3] for r in rows], dtype=np.float32)
    v = (np.array([r[0] for r in rows]) - top) / height

    def at(vv: float) -> tuple[int, int]:
        i = int(np.argmin(np.abs(v - vv)))
        return int(widths[i]), rows[i][4]

    result = {"height_px": height, "width_px": int(xs.max() - xs.min() + 1)}
    for label, vv in [("head", 0.10), ("shoulders", 0.28), ("waist", 0.38),
                      ("hips", 0.47), ("thigh", 0.60), ("knee", 0.68),
                      ("hem", 0.79), ("calf", 0.84), ("feet", 0.96)]:
        i = int(np.argmin(np.abs(v - vv)))
        result[label] = {"v": round(float(v[i]), 3), "width": int(widths[i]),
                         "runs": rows[i][4],
                         "width_over_height": round(float(widths[i]) / height, 3)}
    return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    report = {}
    for key, height in VARIANTS.items():
        canvas = draw(height)
        image = canvas.to_image()
        target = OUT / f"hero34_{height}.png"
        image.save(target)
        image.save(SOURCE / f"hero34_{height}.png")
        polygon = silhouette_polygon(image)
        (OUT / f"hero34_{height}_occluder.json").write_text(
            json.dumps({"height": height, "points": polygon}, indent=1), encoding="utf-8")
        stats = analyse(image, height)
        report[key] = {"height": height, "polygon_points": len(polygon),
                       "colours": len(canvas.palette()),
                       "opaque": int(canvas.alpha.sum()), "silhouette": stats}
        print(f"{key.upper()} {image.width}x{image.height} цветов={len(canvas.palette())} "
              f"непрозрачных={int(canvas.alpha.sum())} контур={len(polygon)} точек")
        for name, data in stats.items():
            if isinstance(data, dict):
                print(f"   {name:10s} v={data['v']:.2f} ширина={data['width']:3d}px "
                      f"({data['width_over_height']:.3f} H) разрывов={data['runs']}")
    (REPORTS / "stage3d_silhouette.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    tiles = []
    for key, height in VARIANTS.items():
        img = Image.open(OUT / f"hero34_{height}.png").convert("RGBA")
        img = img.crop(img.getbbox())
        tiles.append(img.resize((img.width * 6, img.height * 6), Image.NEAREST))
    gap = 28
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + gap * (len(tiles) + 1),
                              max(t.height for t in tiles) + gap * 2), (22, 20, 24))
    x = gap
    for tile in tiles:
        sheet.paste(tile, (x, gap), tile)
        x += tile.width + gap
    path = REPORTS / "stage3d_hero34_x6.png"
    sheet.save(path)
    print(f"лист: {path.relative_to(ROOT).as_posix()} {sheet.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
