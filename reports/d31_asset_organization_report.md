# Отчёт D31 — организация локальной библиотеки игровых ассетов, спрайтов и текстур

> **TASK:** привести локальные папки ассетов/спрайтов/текстур/анимаций в соответствие с D31 — без потери файлов и без поломки работающей игры.
> **STATUS: PASS** (организация и проверки выполнены; два пункта вынесены как `NEEDS_OWNER_DECISION`, ни один файл не перемещён и не удалён).
> **Ветка:** `stage3-hero`. **База:** `e4241b5` (= `origin/stage3-hero`). **Дата:** 2026-11-01.

## 1. Исходное состояние и расхождение (`DISCREPANCY`)

| Проверка | Факт |
|---|---|
| Локальная ветка на старте | `stage3-hero` = `2faa771`, **на 104 коммита позади** `origin/stage3-hero` |
| `origin/stage3-hero` на старте | `e4241b5` — «docs(D31): lock asset file tree and safe DeepSeek reorganization» |
| Рабочее дерево на старте | 1 удалённый отслеживаемый файл + 1 неотслеживаемый PNG |

**Причина расхождения:** D23–D31 были опубликованы только в `origin`; локальная копия оставалась на состоянии задачи 3.1e. Локальное удаление `assets/references/hero/hero_reference_front_back.png` **совпало по смыслу** с удалённым коммитом `92402e0` («art(D25): remove superseded hero master image»), то есть рабочая копия не теряла файл — она уже отражала решение D25.

**Действие:** `git merge --ff-only origin/stage3-hero` → `e4241b5`. Ни `reset`, ни `clean`, ни force не применялись. После fast-forward `git status` чист, кроме одного неотслеживаемого PNG (см. §4).

## 2. Созданные каталоги

Категории `characters`, `enemies`, `bosses`, `weapons`, `props`, `environment`, `tilesets`, `textures`, `vfx`, `ui` **уже существовали локально** (пустые) — пересоздание не требовалось.

Для H01 создана структура `assets/references/gpt_asset_library/characters/H01_hero/`:

```text
master/            sources/            frames/
frames/idle/{down,down_right,right,up_right,up,up_left,left,down_left}/
atlases/
```

Каталоги `move/attack/dodge/hurt/death` **намеренно не созданы**: D22 `ART_PRODUCTION_GATE` не пройден, а пустая папка визуально подменяет готовность (README библиотеки §2). Пустые каталоги Git не хранит — это локальная структура, а не закоммиченное содержимое; фиктивных PNG и `.gitkeep` не добавлялось.

## 3. Инвентаризация (фактические файлы)

Инструмент: `python tools/art/inventory_assets.py` (только чтение) → [reports/d31_asset_inventory.json](d31_asset_inventory.json) + [reports/d31_asset_inventory.md](d31_asset_inventory.md).

| Зона | Записей | PNG |
|---|---|---|
| `assets/references/` (включая библиотеку и мастер H01) | 25 | 25 |
| `assets/archives/` | 1 | ZIP 68 551 781 байт |
| `game/prototype/art/` | 78 | 37 |
| `game/experiments/` | 33 | 11 |
| библиотека (метаданные) | 4 | 0 |
| **всего** | **141** | **73** |

Для каждого файла зафиксированы путь, зона, тип, байты, SHA-256, признак «в Git», признак «в `origin/stage3-hero`», PNG-размеры/режим/alpha-статистика и ссылки из Godot. **Перемещено/переименовано/удалено: 0 файлов.**

**Целостность оригиналов:** `docs/REFERENCE_FILE_MANIFEST.sha256` → **23/23 совпали**, отсутствующих и расхождений нет. Архив владельца не распаковывался и не изменялся.

**Кандидатов с однозначной безопасной миграцией не оказалось.** Все 25 файлов в `assets/references/` — исторические референсы владельца (D31 прямо запрещает автоматический перенос), все 48 PNG в Godot-зонах уже используются проектом либо требуют отдельного решения.

## 4. Главный герой H01

| Что | Факт |
|---|---|
| Целевой игровой кадр `.../frames/idle/down_right/H01_idle_down_right_000.png` | **`NOT_IMPORTED`** — файла нет ни в рабочей копии, ни в `origin/stage3-hero`. Поиск по именам `H01_idle_down_right_000`, `*H01*`, `*idle_down*`, `*down_right*` не дал совпадений; файлов с суффиксом `(1)`/`(2)` в репозитории нет. Замена не создавалась (D24/D26 запрещают изготовление игрового кадра в DeepSeek). |
| Утверждённый мастер D25 | `assets/references/hero/H01_approved_visual_master_2026-11-01.png` — **физически есть**, `LOCAL_ONLY` (не закоммичен) |
| SHA-256 мастера | `5748b3f218294cd8ee158ae282ff1e4bf50f69907f983bc300dee4e723cb0217` — **совпал** с записью D25 и с `master.sha256` карточки |
| Измерения мастера | 1536×1024, режим `RGB`, **альфа-канала нет**, 1 674 973 байта — совпало с D25 |
| Куда положен | оставлен по месту: D25 и README библиотеки §7 фиксируют этот путь как канонический, перенос в `master/` не выполнялся |

Мастер — визуальный эталон дизайна, **не** игровой спрайт: у него нет alpha-канала, поэтому он в принципе не может быть сценой подключён как прозрачный спрайт.

## 5. Машинный каталог

| Файл | Изменение |
|---|---|
| `assets/references/gpt_asset_library/characters/H01_hero/asset.json` | `master.presence` = `LOCAL_ONLY`, добавлены `bytes`, `measured` (1536×1024 RGB), `verified_at/verified_by`, `library_tree.created_locally`, `absent_exports[]` (`NOT_IMPORTED`), блок `verification`. `files[]` **остался пустым** — реальных игровых PNG нет |
| `asset_index.json` | добавлены `master_presence: LOCAL_ONLY`, `game_export_present: false`; `presence` по-прежнему `NOT_IMPORTED`, `readiness` = `NOT_GAME_READY` |
| `_templates/asset.template.json` | не изменялся |

`ART_APPROVED` не присвоен нигде. Несуществующие кадры в `files[]` не записаны. `PUSHED` не проставлялся.

**Зарегистрировано по ID:** 1 ассет (`H01`), 0 игровых файлов. Это соответствует фактическому состоянию, а не «заполненной библиотеке».

## 6. Godot-структура и ссылки

Новых подготовленных игровых экспортов нет → `game/prototype/art/gpt/...` не создавался. Сцены, контроллеры, `.tscn/.tres/.gd` **не изменялись**, D16/D28/D29 не затронуты.

Проверка ссылок (инвентаризация, `.import`-файлы из подсчёта исключены как самоописание, чтобы не получать ложный «exact»):

| Категория | Кол-во | Вывод |
|---|---|---|
| PNG с точной ссылкой `res://art/...` в сцене/скрипте/ресурсе | 14 | ссылки живые |
| PNG, подключаемые динамически по имени файла (`const ART := "res://art/calibration/"`, `layout.json` эксперимента) | 31 | ссылки живые |
| PNG **без ссылок вообще** | 3 | `game/prototype/art/sprites/hero_proxy_48.png`, `game/experiments/res_study/art/a/world_24_ns.png`, `game/experiments/res_study/art/c/world_48_ns.png` — оставлены на месте, см. §8 |

**Битых ссылок в игре: 0.** Ни одна сцена/скрипт не обращаются внутрь `gpt_asset_library`, поэтому её реорганизация не могла сломать игру.

## 7. Выполненные проверки

| Проверка | Команда | Результат |
|---|---|---|
| Инвентаризация | `python tools/art/inventory_assets.py` | 141 файл, 73 изображения, 0 перемещений |
| Целостность оригиналов | (внутри инвентаризации) `REFERENCE_FILE_MANIFEST.sha256` | **23/23 MATCH**, absent 0, mismatch 0 |
| Валидация каталога | `python tools/art/validate_asset_library.py` | **PASS**: 1 ассет в индексе, 1 карточка, 0 записей `files[]`, 0 failures, 0 warnings |
| Негативный тест валидатора | `--library <испорченная копия>` | **FAIL**, 7 failures: отсутствующий PNG в `files[]`, неверный SHA мастера, дубль ID, выход пути за корень (`../../../README.md`), незарегистрированная карточка. Валидатор не «всегда PASS» |
| Godot smoke-test | `godot --path game/prototype -- --shot=reports/d31_smoke_location.png --shot-frames=150` | `SHOT_SAVED err=0 size=960x540`, `PROFILE_READY b approved=YES tile_px=24 hero_height_px=48`, `TILESET_READY tiles=12`, `PLAYER_SPAWN sheet=res://art/sprites/hero_idle_48.png`, `FPS 119` — реальный кадр [d31_smoke_location.png](d31_smoke_location.png) |

## 8. Оставлено на месте намеренно

- **Все 25 исторических референсов** в `assets/references/{bosses,enemies,weapons,locations,gameplay,hero}` — D31 запрещает автоперенос; D25 не позволяет трогать мастер.
- **Все 48 PNG в Godot-зонах** — используются сценами/скриптами либо требуют решения владельца; перенос «для красоты» запрещён.
- **`assets/archives/rogalik_all_concept_art_with_weapons.zip`** (68,5 MB) — архив владельца, не распаковывался, не перемещался.
- **Экспериментальный проект `game/experiments/res_study/`** — не трогался.

**Обнаруженные дефекты, которые я не стал исправлять самостоятельно:**

1. **4 «осиротевших» `.import`-файла** (отслеживаются в Git, PNG удалены предыдущими коммитами D25): `game/experiments/res_study/art/hero34/hero34_48.png.import`, `hero34_96.png.import`, `art/hero_master/hero_master_48.png.import`, `hero_master_96.png.import`. Удаление файлов требует отдельного разрешения (AGENTS §2).
2. **3 PNG без ссылок** (§6) — фактически неиспользуемые игровые/экспериментальные файлы; удалять или переносить их — решение владельца.
3. Кэш `game/experiments/res_study/.godot/` содержит импорты удалённых PNG — это gitignored-кэш, на Git не влияет.

## 9. `NEEDS_OWNER_DECISION`

| # | Вопрос | Варианты |
|---|---|---|
| D31-1 | Публиковать ли утверждённый мастер D25 в GitHub (1,67 MB, сейчас `LOCAL_ONLY`)? | а) закоммитить как есть по пути `assets/references/hero/...`; б) перенести в `characters/H01_hero/master/` с обновлением D25/HERO_REFERENCE; в) оставить локально |
| D31-2 | Судьба 4 осиротевших `.import` и 3 PNG без ссылок | удалить / оставить / перенести в архив |
| D31-3 | Нужны ли `.gitkeep` в 10 категориях библиотеки, чтобы пустая структура переживала клон | да / нет (README §2 рекомендует «нет») |
| D31-4 | Когда мигрировать исторические референсы в библиотеку (D31 их запрещает без прямого решения) | сейчас / после Этапа 4 |

## 10. Что не подтверждено (`NOT_VERIFIED`)

- **Художественное качество** мастера и любого H01-кадра — `REFERENCE_FIDELITY_GATE` этой задачей не проходился; `ART_APPROVED` не присваивался.
- **`GODOT_PASS` для H01** невозможен: игрового PNG нет (`GODOT_NOT_TESTED`).
- Экспериментальный проект `game/experiments/res_study/` не запускался; его 4 осиротевших `.import` могут давать предупреждения при открытии в редакторе — не проверялось.
- Соответствие мастера D25 «эталону владельца» — визуальное утверждение остаётся за владельцем.

## 11. Публикация

Коммит **`1d3b91a766f378786ec83d48413c90cef1c58021`** опубликован в рабочую ветку `stage3-hero` (`git push origin stage3-hero`); `git ls-remote --heads origin stage3-hero` → `1d3b91a…`, 7 blob-ов сверены с локальными (`inventory_assets.py` `50372624…`, `validate_asset_library.py` `82ebf292…`, `d31_asset_inventory.json` `089c0bf1…`, `d31_library_validation.json` `71bd441c…`, `d31_asset_organization_report.md` `a1fb4d50…`, `H01_hero/asset.json` `3a1a8b2c…`, `asset_index.json` `6d3687fa…`). Удалённая ветка содержит 490 файлов. `main` не затрагивался.

**Мастер D25 в коммит не входит:** `git ls-tree -r origin/stage3-hero -- assets/references/hero` → пусто. Файл остаётся `LOCAL_ONLY` до решения владельца (D31-1).
