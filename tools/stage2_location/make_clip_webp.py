"""Сборка компактной версии клипа из AVI, записанного Godot Movie Maker.

Зачем: MP4/WebM-энкодера в среде нет (ffmpeg не установлен), а AVI/MJPEG весит
десятки мегабайт. Скрипт разбирает RIFF/AVI, вытаскивает JPEG-кадры (Movie Maker
пишет MJPEG), уменьшает их до логического разрешения 480x270 (ровно 2x вниз,
nearest) и складывает анимированный WebP — он открывается в браузере и в
просмотрщиках изображений и остаётся пиксельно-точным.

Это ТОЛЬКО упаковка уже записанного реального геймплея: новых кадров скрипт
не создаёт.

    python tools/stage2_location/make_clip_webp.py reports/stage2_clip.avi reports/stage2_clip.webp
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image

AVI_VIDEO_CHUNKS = (b"00dc", b"00db")


def read_avi_frames(path: Path) -> tuple[list[bytes], int, int, int]:
    """Возвращает (кадры JPEG, ширина, высота, fps) из AVI, записанного Godot."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"AVI ":
        raise ValueError("не RIFF/AVI файл")
    width = height = fps = 0
    frames: list[bytes] = []
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        body = data[pos + 8 : pos + 8 + size]
        if chunk_id == b"LIST":
            pos += 12  # LIST + size + тип списка
            continue
        if chunk_id == b"avih" and size >= 40:
            microseconds = struct.unpack("<I", body[0:4])[0]
            fps = int(round(1_000_000 / microseconds)) if microseconds else 0
            width = struct.unpack("<I", body[32:36])[0]
            height = struct.unpack("<I", body[36:40])[0]
        elif chunk_id in AVI_VIDEO_CHUNKS:
            frames.append(body)
        pos += 8 + size + (size & 1)
    return frames, width, height, fps


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("avi", type=Path)
    parser.add_argument("webp", type=Path)
    parser.add_argument("--target", default="480x270", help="логическое разрешение кадра")
    parser.add_argument("--keep-every", type=int, default=2, help="прореживание кадров (2 = 30 fps из 60)")
    parser.add_argument("--duration-ms", type=int, default=33)
    parser.add_argument("--quality", type=int, default=82)
    args = parser.parse_args(argv)

    frames_raw, width, height, fps = read_avi_frames(args.avi)
    print(f"avi={args.avi.name} size={args.avi.stat().st_size} bytes frames={len(frames_raw)} {width}x{height} @ {fps} fps")
    if not frames_raw:
        print("FAIL: в AVI нет видеокадров")
        return 1

    target_w, target_h = (int(v) for v in args.target.lower().split("x"))
    if width % target_w or height % target_h:
        print(f"WARN: {width}x{height} не кратно {target_w}x{target_h}; уменьшение не целочисленное")

    images: list[Image.Image] = []
    for index, raw in enumerate(frames_raw):
        if index % args.keep_every:
            continue
        import io

        frame = Image.open(io.BytesIO(raw)).convert("RGB")
        images.append(frame.resize((target_w, target_h), Image.NEAREST))

    args.webp.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        args.webp,
        format="WEBP",
        save_all=True,
        append_images=images[1:],
        duration=args.duration_ms,
        loop=0,
        quality=args.quality,
        method=6,
    )
    size = args.webp.stat().st_size
    fps_out = int(round(1000.0 / max(1, args.duration_ms)))
    print(f"webp={args.webp.name} source_frames={len(images)} {target_w}x{target_h} {fps_out} fps size={size} bytes")

    check = Image.open(args.webp)
    total_ms = 0
    for index in range(getattr(check, "n_frames", 1)):
        check.seek(index)
        total_ms += int(check.info.get("duration", 0))
    print(
        "webp_reopen frames=%d size=%s total_duration_ms=%d (ожидалось ~%d)"
        % (getattr(check, "n_frames", 1), check.size, total_ms, len(images) * args.duration_ms)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
