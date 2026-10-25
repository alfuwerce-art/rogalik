# tools/stage3_hero — герой (Этап 3)

Инструменты задачи 3.1: рисунок силуэта героя 48 px, сборка исходника Pixelorama, экспорт, проверки и лист сравнения.

## Порядок (реальный пайплайн, не «похожий писатель PNG»)

```powershell
$py = "<python 3.12 из docs/ROGALIK_DEV_ENVIRONMENT.md>"
$env:PYTHONPATH = "<repo>/tools"
$env:PYTHONIOENCODING = "utf-8"

# 1. рисунок + лист-источник + .pxo
& $py tools\stage3_hero\author_hero.py --out tools\stage3_hero\source --json reports\stage3_hero_build.json

# 2. экспорт PNG самим Pixelorama CLI
& $py -m pixel_pipeline.cli export tools\stage3_hero\source\hero_idle_48.pxo `
    --out game\prototype\art\sprites --sheet --name hero_idle_48

# 3. проверки кадров (экспорт == .pxo, привязка, прозрачность, палитра)
& $py tools\stage3_hero\check_hero_frames.py `
    --sheet game\prototype\art\sprites\hero_idle_48.png `
    --project tools\stage3_hero\source\hero_idle_48.pxo `
    --json reports\stage3_hero_frames_check.json --report reports\stage3_hero_frames_check.txt

# 4. лист сравнения (референс → спрайт → игровые кадры)
& $py tools\stage3_hero\make_compare.py `
    --reference assets\references\hero\hero_reference_front_back.png `
    --sheet game\prototype\art\sprites\hero_idle_48.png `
    --frames reports\stage3_hero_frame_down.png reports\stage3_hero_frame_up.png `
             reports\stage3_hero_frame_left.png reports\stage3_hero_frame_right.png `
    --out reports\stage3_hero_compare.png --scale 6
```

## Файлы

| Файл | Назначение |
|---|---|
| `author_hero.py` | рисунок четырёх направлений и двух кадров `idle` явными пиксельными таблицами; сборка `.pxo` пайплайном |
| `make_preview.py` | увеличенное превью листа с подписями (артефакт, не ассет) |
| `check_hero_frames.py` | проверки: экспорт == `.pxo`, геометрия 32×48, привязка стоп, отсутствие полупрозрачных пикселей, палитра |
| `make_compare.py` | лист сравнения «референс → спрайт → игра»; кадрирование игрового кадра считается из геометрии камеры |
| `source/hero_idle_48.pxo` | исходник Pixelorama (8 кадров, теги `idle_down/up/left/right`) |

## Раскладка листа

`256×48`, один ряд, 8 кадров `32×48`:

```
0 down A | 1 down B | 2 up A | 3 up B | 4 left A | 5 left B | 6 right A | 7 right B
```

Кадр = `направление * 2 + кадр_idle` (направления: down=0, up=1, left=2, right=3). В Godot это `hframes = 8`, `vframes = 1` (`pixel_profiles.gd`, профиль B).

## Границы

- Спрайт — `ASSET_DRAFT`: технические проверки не являются художественной приёмкой.
- Полной анимации движения/боя здесь нет: задача 3.1 делает силуэт и `idle`.
- Правый профиль — зеркало левого (на референсе боковых видов нет).
