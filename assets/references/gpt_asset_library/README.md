# Rogalik — GPT Asset Library (D30)

**Расположение в репозитории:** `assets/references/gpt_asset_library/`  
**На ПК владельца:** `C:\Users\bow\Desktop\Rogalik\assets\references\gpt_asset_library\`

Это единая **исходная библиотека художественной графики, созданной ChatGPT**: персонажи, враги, боссы, оружие, props, окружение, тайлы/тайлсеты, текстуры, VFX и UI, включая кадры анимаций. **Интегрированные файлы Godot живут отдельно** — в игровом каталоге `game/prototype/art/` (или согласованном каталоге соответствующей Godot-сцены). Библиотека — источник и каталог, а не автоматически подключённый Godot ресурс.

## 1. Категории и дерево (создавать папки по мере поступления ассетов)

```text
gpt_asset_library/
├── README.md
├── asset_index.json                 # единый поиск по ID → asset.json, не утверждение готовности
├── _templates/
│   └── asset.template.json          # образец манифеста; НЕ реальный ассет
├── characters/
│   └── H01_hero/
│       ├── asset.json               # запись о H01; изображения пока NOT_IMPORTED
│       ├── master/                  # утверждённые исходные мастера по факту передачи
│       ├── sources/                 # неизменённые оригиналы генераций GPT
│       ├── frames/
│       │   ├── idle/
│       │   │   ├── down/
│       │   │   ├── down_right/
│       │   │   ├── right/
│       │   │   ├── up_right/
│       │   │   ├── up/
│       │   │   ├── up_left/
│       │   │   ├── left/
│       │   │   └── down_left/
│       │   ├── move/                # те же направления
│       │   ├── attack/
│       │   ├── dodge/
│       │   ├── hurt/
│       │   └── death/
│       └── atlases/                 # производные атласы и метаданные
├── enemies/                         # <ID>_<slug>/asset.json + master/sources/frames/atlases
├── bosses/                          # <ID>_<slug>/...
├── weapons/                         # <ID>_<slug>/master/sources/frames/asset.json
├── props/                           # <ID>_<slug>/master/sources/frames/asset.json
├── environment/                     # <ID>_<slug>/master/sources/layers/asset.json
├── tilesets/                         # <ID>_<slug>/sources/tiles/atlases/asset.json
├── textures/                         # <ID>_<slug>/sources/exports/asset.json
├── vfx/                              # <ID>_<slug>/sources/frames/asset.json
└── ui/                               # <ID>_<slug>/sources/exports/asset.json
```

`enemies` и `bosses` вынесены из `characters` для однозначной категории и поиска. **Не дублировать один и тот же ID в разных категориях.** Папки без файлов Git не сохраняет: пустые каталоги допускается создавать при первом поступлении конкретного ассета.

## 2. Идентификация и имена файлов

- **ID — из существующего [реестра](../../../docs/ART_ASSET_ANIMATION_REGISTRY.md)** или новый ID после проверки его уникальности; slug короткий ASCII `snake_case`. Никогда не переименовывать утверждённый ID из-за нового кадра. Примеры `H01_hero`, `<ID>_barrel` — последний только шаблон, **не присвоенный ID**.
- Для кадров: `<ID>_<animation>_<direction>_<frame:03d>.png`, например `H01_idle_down_right_000.png`. У персонажей D29 восемь ID направлений: `down`, `down_right`, `right`, `up_right`, `up`, `up_left`, `left`, `down_left`. `idle`, `move`, `attack`, `dodge`, `hurt`, `death` — идентификаторы клипов; другие только по актуальному игровому ТЗ.
- Статика: `<ID>_static_000.png`; тайл: `<ID>_<surface>_<variant:03d>.png`; VFX: `<ID>_<effect>_<frame:03d>.png`. Для каждого файла — путь и SHA-256 в `asset.json`; не выдавать примеры за существующие файлы.
- **Один художественный кадр = один PNG**. Общий лист/GIF — лишь необязательное превью. Атласы — производные от отдельных кадров, не заменяют оригиналы.
- **master/** — только реально полученный и утверждённый эталон, без перезаписи; **sources/** — неизменённые GPT-оригиналы с SHA; **frames/** / `tiles/` / `exports/` — технически подготовленные `GAME_EXPORT`. По возможности не смешивать исходники с экспортами.
- При изменении художественного содержания новой генерацией — новая версия исходника; не затирать опубликованный и утверждённый исходник. `_v02` у версии мастера допустим, `final_final2` нет.

## 3. Контракт поиска для DeepSeek

1. Прочитать `asset_index.json` и найти запись по `asset_id`/типу. **Это индекс путей, не гарантия наличия PNG.**
2. Открыть указанный относительный `manifest_path` (`asset.json`); проверить `asset_id`, `profile_id`, `direction`, `animation`, `frame_index`, `canvas_px`, `pivot_px`, `world_footprint_tiles`, `file_sha256` и статусы.
3. Проверить **фактическое наличие каждого PNG**, контрольную сумму, `TECHNICAL_EXPORT_PASS`, актуальный профиль ([HD4X](../../../config/art_profiles/hd4x_pilot.json)), художественную приёмку и готовность интеграции. Если графика не поступила — `NOT_IMPORTED`; не подменять её старым прокси или автоматически созданной иллюстрацией.
4. Скопировать или подготовить **отдельный производный игровой файл** в Godot (`game/prototype/art/`) с корректными трансформами/слоями и импортировать сцену. В манифесте записать `godot_resource_path` и результат запуска. Не подключать произвольные архивные мастер-листы как кадры.
5. После проверенного обновления синхронизировать **оба индекса** — локальный `asset.json` + корневой `asset_index.json` — и [ART_ASSET_ANIMATION_REGISTRY.md](../../../docs/ART_ASSET_ANIMATION_REGISTRY.md), [PROJECT_STATE.md](../../../docs/progress/PROJECT_STATE.md), [STAGE_03.md](../../../docs/progress/STAGE_03.md). Commit/push **только текущей рабочей ветки**, проверить удалённый SHA.

Для генерации файлов сама библиотека **не имеет** подключения к чату GPT: владелец передаёт PNG фактически. Не присваивать `PUSHED` до удалённой проверки файла. Публикация метаданных **не означает**, что PNG загружен.

## 4. Требования к импорту и приёмке

- D24 — GPT рисует художественные изображения; DeepSeek только технически готовит и интегрирует.
- D25 — единственный утверждённый визуальный герой H01, исходный мастер описан в `docs/HERO_REFERENCE.md`. **Уже документированный путь старого утверждённого master PNG не перемещать автоматически.** Если мастер вне библиотеки — сохранять `external_master_path`, проверять наличие и SHA; миграция только отдельной задачей со всеми ссылками.
- D28–D29 — `ROGALIK_HD4X_PILOT`: 192 **исходных** px фигуры H01, 96px тайл, восемь направлений; world-физика D16 остаётся прежней до отдельной приёмки.
- D22 — до художественного гейта не производить весь цикл анимаций. Первый кандидат — `H01_idle_down_right_000.png`; нельзя записать восемь готовых направлений, если реально имеется лишь один.
- `TECHNICAL_EXPORT_PASS`, `GODOT_PASS`, `ART_APPROVED`, `PUSHED` — **разные** факты. `NULL` или `NOT_VERIFIED` не считать положительным статусом.

## 5. Структура манифестов

Корневой `asset_index.json`: `schema_version`, `library_root`, список `assets` с `asset_id`, `category`, `manifest_path`, `presence` и `readiness`.

В каждом `asset.json`: `asset_id`, `category`, `display_name`, `profile_id`, `master` (source-path+SHA+проверенный статус), `files` (массив реальных файлов или `[]`), `animations` (индексы реально присутствующих кадров), `status` (раздельно наличие/технический/художественный/Godot), `godot_resource_path`, `updated_at`. Дополнительные поля `world_footprint_tiles`, `canvas_px`, `pivot_px` только по реальным данным. Смотри `_templates/asset.template.json`.

**Если файл не существует — не создавать фальшивую запись `files` о нём.** Пример записи H01 в библиотеке специально начинается с пустого `files: []` и `NOT_IMPORTED`: это шаблон адресации, а не принятие PNG.

**Синхронизация GitHub ≠ доступность файла на ПК:** агент проверяет, что локальная рабочая копия обновлена. Истинность `PUSHED` проверяется по GitHub, а `LOCAL_PRESENT` — по диску.
