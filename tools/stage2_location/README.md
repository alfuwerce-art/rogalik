# tools/stage2_location — инструменты каркаса локации (Этап 2)

Статус всех созданных здесь изображений — **`PROXY_TECHNICAL`** (D8): это процедурные
заготовки для проверки пиксельных констант (D9), а не финальный арт. Художественная
приёмка не проводилась и автотестом не подтверждается.

## Сценарий

1. `make_proxies.py` — рисует по одной «рецептуре» тайлсет, спрайт-лист героя, дерево,
   ворота и текстуру света в трёх сетках: 16, 24 и 32 px. Результат — в
   `game/prototype/art/`, перечень с размерами — `proxy_manifest.json`.
2. `make_layout.py` — собирает ASCII-карту технической локации (40×24) и записывает её
   в `game/prototype/scripts/world/location_layout.gd` как константу. Скрипт гарантирует
   одинаковую ширину строк.
3. `make_preview.py` — превью всех сеток в один PNG для просмотра человеком
   (`reports/stage2_2_1_assets_preview.png`).
4. `check_pixel_scale.py` — проверяет кадр реально запущенной игры: пиксель арта обязан
   занимать блок N×N пикселей окна одного цвета (N = zoom камеры × масштаб окна).
   Любая интерполяция, дробный zoom или дробное смещение камеры/спрайта делают блоки
   неодноцветными. Дополнительно проверяется, что фон вне карты не виден.
5. `check_tile_seams.py` — проверяет, что у тайлов земли крайние пиксели сторон
   одноцветны и совпадают у вариантов материала (иначе земля читается «шахматкой»).
   Для дорожки и настила линия на границе — часть рисунка, для них критерий
   информационный.

## Запуск

```powershell
python tools/stage2_location/make_proxies.py
python tools/stage2_location/make_layout.py
python tools/stage2_location/make_preview.py

godot --path game/prototype --headless --import
godot --path game/prototype -- --profile=b --stats --shot=C:/tmp/shot.png --shot-frames=400

python tools/stage2_location/check_pixel_scale.py C:/tmp/shot.png --block 2 --exclude-bottom 88 --tolerance 8
python tools/stage2_location/check_tile_seams.py game/prototype/art/tilesets/tileset_24.png --tile 24
```

`--block` — N (для полосы A: 4, для B и C: 2). `--exclude-bottom 88` исключает полосу HUD:
текст HUD рисуется в нативном разрешении окна и намеренно не кратен блоку арта.
`--tolerance 0` — строгий режим (используется на кадрах без источников света),
`--tolerance 8` — допускает мягкое свечение.

Отчёт задачи 2.1 с таблицей констант и результатами — [reports/stage2_task21_report.md](../../reports/stage2_task21_report.md).
