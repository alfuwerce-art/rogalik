# Каталог исходных концепт-артов (импорт из локального пакета)

> Версия 2026-10-25. **Статусы ведутся по трём осям** ([AGENTS.md §7](../AGENTS.md)): художественное решение (`VISUAL_APPROVED` / `VISUAL_CANDIDATE` / `LOOK_REFERENCE` / `NO_REFERENCE`), наличие файла (`ABSENT` / `LOCAL_ONLY` / `COMMITTED_LOCAL` / `PUSHED`), готовность ассета (`NONE` / `PROXY_TECHNICAL` / `ASSET_DRAFT` / `ASSET_APPROVED`).
> Индекс фиксирует статус художественного решения и наличие файла, но не заменяет бинарное изображение.

## Состояние локального импорта — 2026-10-25

> Наличие файлов: `COMMITTED_LOCAL` для локальных коммитов и `PUSHED` для файлов, подтверждённых в удалённой ветке `origin/stage1-playable-combat` (2026-10-25, SHA `b0db47e`).

- Источник: `assets/archives/rogalik_all_concept_art_with_weapons.zip`, 68 551 781 байт, SHA-256 `e900eaad8806b881eb91d51ea649d9f2ad1131974a3687bd67628a3515169b23` (архив не изменялся).
- Распаковано 23 из 23 PNG в `assets/references/` с сохранением структуры `bosses/`, `enemies/`, `weapons/`, `locations/`; вложенная папка `rogalik/` снята.
- Все 23 SHA-256 совпадают с `REFERENCE_FILE_MANIFEST.sha256`; файлы побайтово равны содержимому архива (без пересжатия и конвертации).
- Разделение статусов сохранено: **17 файлов утверждённых референсов** (5 боссов, 7 обычных врагов, 5 листов оружия) и **6 кандидатов** (5 концептов первой локации + триптих Мёртвого стрелка).
- Проверка и отчёт: `tools/reference_import/`, `reports/reference_import.md`.
- Дополнительно вне архива получены 2 референса от владельца (герой и игровой look) — см. разделы ниже; в 23 PNG из ZIP они не входят.

## Реестр доступности референсов

> Боссы и враги детально — [BESTIARY.md](BESTIARY.md), раздел 0. Нет статуса `VISUAL_APPROVED` — визуальная разработка единицы не начинается: сообщить `BLOCKED_NEEDS_REFERENCE` и ждать референс ([DEEPSEEK_GAME_DEV_RULES.md](DEEPSEEK_GAME_DEV_RULES.md)).

| Категория | `VISUAL_APPROVED` | `VISUAL_CANDIDATE` | Нет референса |
|---|---|---|---|
| Главный герой | 1 (референс дизайна, `hero/hero_reference_front_back.png`) | — | — |
| Оружие | 5 листов, 20 видов | — | — |
| Боссы | 5 (B01–B05) | — | 4 (B06–B09) — `BLOCKED_NEEDS_REFERENCE` |
| Обычные враги | 7 файлов (E01–E03, база E04) | 1 (3 варианта E04) | 6 семейств (E05–E10) — `BLOCKED_NEEDS_REFERENCE` |
| Первая локация | 0 | 5 концептов | утверждённой локации нет; финальный арт заблокирован до утверждения кандидата |
| Игровые спрайты/ассеты | 0 | — | герой — только `PROXY_TECHNICAL` (D8); утверждённых игровых ассетов нет |

Техническая тестовая сцена-серый бокс и работа с механиками не требуют утверждённого арта; финальные визуальные ассеты — требуют.

## Утверждённые боссы

| Название | Целевой путь |
|---|---|
| Кощей Бессмертный | `assets/references/bosses/koschei_bessmertny.png` |
| Змей Горыныч | `assets/references/bosses/zmey_gorynych.png` |
| Лихо Одноглазое | `assets/references/bosses/likho_odnoglazoe.png` |
| Полудница (с нормальными пальцами) | `assets/references/bosses/poludnitsa.png` |
| Утопленница | `assets/references/bosses/utoplennitsa.png` |

Другие боссы утверждены **по составу**, но пока без утверждённых изображений. Полный перечень: [BESTIARY.md](BESTIARY.md).

## Утверждённые враги

| Семейство | Базовый PNG | PNG вариантов |
|---|---|---|
| Павшие ратники | `assets/references/enemies/fallen_warriors/fallen_warrior_base.png` | `assets/references/enemies/fallen_warriors/fallen_warrior_variants_triptych.png` |
| Погребальные звонари | `assets/references/enemies/bellringers/bellringer_base.png` | `assets/references/enemies/bellringers/bellringer_variants_triptych.png` |
| Моровые волхвы | `assets/references/enemies/morovoi_volkhv/morovoi_volkhv_base.png` | `assets/references/enemies/morovoi_volkhv/morovoi_volkhv_variants_triptych.png` |
| Мёртвый стрелок | `assets/references/enemies/dead_archer/dead_archer_base.png` | `assets/references/enemies/dead_archer/dead_archer_variants_triptych_candidate.png` — **КАНДИДАТ**, не утверждён |

Остальные враги утверждены по составу, не по картинке. Не выдумывать им статус `VISUAL_APPROVED`.


## Оружие — 5 утверждённых концепт-листов (20 разновидностей)

Все оригиналы получены повторно от владельца 2026-10-25 и сохранены без пересжатия в обновлённом локальном архиве. **Статус наличия: `PUSHED`** — подтверждено в `origin/stage1-playable-combat` (SHA `b0db47e`).

| Семейство | Целевой путь | Художественный статус |
|---|---|---|
| two handed | `assets/references/weapons/01_two_handed_weapons.png` | APPROVED |
| magic | `assets/references/weapons/02_magic_staves.png` | APPROVED |
| dual | `assets/references/weapons/03_dual_weapons.png` | APPROVED |
| bows | `assets/references/weapons/04_bows.png` | APPROVED |
| combat | `assets/references/weapons/05_combat_staves.png` | APPROVED |

Подробная расшифровка 20 видов и хеши: [WEAPON_REFERENCES.md](WEAPON_REFERENCES.md).

## Первая локация — пять кандидатов, пока НЕ утверждены

- `assets/references/locations/first_location/first_location_master_candidate.png`
- `assets/references/locations/first_location/cursed_sloboda_master_concept.png`
- `assets/references/locations/first_location/village_interior_01.png`
- `assets/references/locations/first_location/village_interior_02.png`
- `assets/references/locations/first_location/village_interior_03.png`

Названия и композиции описаны в [FIRST_LOCATION_CONCEPT.md](FIRST_LOCATION_CONCEPT.md). При разработке обязательно учитывать [FIRST_LOCATION_ART_RULES.md](FIRST_LOCATION_ART_RULES.md).

## Главный герой — референс передан владельцем 2026-10-25

| Файл | Статус | Источник | SHA-256 |
|---|---|---|---|
| `assets/references/hero/hero_reference_front_back.png` | `VISUAL_APPROVED` (дизайн, D7) | чат владельца, 2026-10-25; PNG 1536×1024, 2 110 834 байта | `53c9ace7a25dd16916c2cd7dfbba7ef7410a8a701090b3a2fe042f788c99f985` |

Подробно: [HERO_REFERENCE.md](HERO_REFERENCE.md). Утверждённого пиксельного спрайта героя **нет**; в `game/prototype/art/` и `tools/stage1_art/` есть только `PROXY_TECHNICAL` (D8), утверждён исключительно референс внешности.

## Игровой look-референс — ориентир, не финальный канон

| Файл | Статус | Источник | SHA-256 |
|---|---|---|---|
| `assets/references/gameplay/gameplay_look_reference.png` | `LOOK_REFERENCE` (ориентир) | чат владельца, 2026-10-25; PNG 1672×941, 3 051 027 байт | `c04d11f71ae2d2c98e8199ee654040b57dd3d451fa2d07943fb8556a744d9ae2` |

Владелец обозначил кадр как ориентир «как примерно должна выглядеть игра». Он показывает ночную слободу, героя и врагов, телеграф атаки и HUD, но не является утверждённой локацией, раскладкой уровня или финальным UI. Целевой рендер остаётся 2D Pixel Art — см. [ART_DIRECTION.md](ART_DIRECTION.md).

## Обращение с файлами

- Имена в GitHub латиницей `snake_case`. Исходные изображения хранить неизменными; любые модификации — отдельные имена/версии.
- Триптихи — изображения для визуального направления, а не три готовых игровых ассета.
- Перед присвоением `PUSHED` убедиться, что удалённая ветка GitHub реально содержит PNG с ожидаемым размером/хешем. Локальный коммит и публикация — разные состояния.
- Источник и контрольные суммы оригиналов хранятся в приложенном локальном пакете (`REFERENCE_FILE_MANIFEST.sha256`).
- Сам факт записи этого Markdown **не загружает графику в GitHub**.
