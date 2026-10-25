# Структура репозитория Rogalik (план и порядок импорта)

> Обновление 2026-10-25: **визуальный канон изменён на 2D Pixel Art** (см. [PIXEL_ART_STYLE_GUIDE.md](PIXEL_ART_STYLE_GUIDE.md)). Перечисленные ниже пути `sources/3D models`, `FBX/GLB` и схема `game/[unity-or-unreal]` — **унаследованный предварительный план, не обязательная структура для нового 2D-проекта**. После выбора движка уточнить 2D-каталоги `sprites/tilesets/atlases/animations` и `game/`. Фактическое наличие файлов и директорий не заявлено; репозиторий сейчас в основном документальный.

## 1. Корневая структура

```text
rogalik/
├── README.md
├── .gitignore
├── .gitattributes                # добавить при реальном подключении Git LFS
├── LICENSE
├── docs/
│   ├── ART_DIRECTION.md          # художественный канон
│   ├── BESTIARY.md               # состав и роли врагов
│   ├── BOSS_REFERENCES.md        # утверждённые образы боссов
│   ├── CONCEPT_ART_INDEX.md      # индекс оригинальных изображений и статусов
│   ├── WEAPON_REFERENCES.md      # семейства оружия
│   ├── SKILLS_AND_BOONS.md       # системы прогрессии
│   ├── FIRST_LOCATION_CONCEPT.md # кандидат концепции первой локации
│   ├── FIRST_LOCATION_ART_RULES.md # обязательные правила первого окружения
│   ├── REPOSITORY_STRUCTURE.md   # этот файл
│   ├── DEEPSEEK_GAME_DEV_RULES.md
│   ├── AI_STUDIO_PLAYBOOK.md
│   ├── AI_HINT_LIBRARY.md
│   ├── CHARACTER_PRODUCTION_PIPELINE.md
│   ├── GLOBAL_ASSET_PASSES.md
│   └── tasks/                   # задания и рубежи по мере запуска разработки
├── assets/
│   ├── references/              # ИСХОДНЫЕ концепт-арты, не игровые ассеты
│   │   ├── bosses/
│   │   ├── enemies/
│   │   │   ├── fallen_warriors/
│   │   │   ├── bellringers/
│   │   │   ├── morovoi_volkhv/
│   │   │   └── dead_archer/
│   │   ├── locations/
│   │   │   └── first_location/
│   │   ├── weapons/
│   │   ├── hero/
│   │   └── gameplay/
│   ├── sources/                 # исходники моделей/анимаций при наличии прав
│   │   ├── characters/
│   │   ├── environments/
│   │   └── animations/
│   └── exports/                 # переносимые FBX/GLB, текстуры; не билд
│       ├── characters/
│       ├── environments/
│       └── animation_clips/
├── tools/                       # скрипты сборки, импорта, QA; после выбора движка
├── reports/                     # проверяемые отчёты, без огромных логов в Git
└── game/                        # будущий ОДИН движковый проект
    └── [unity-or-unreal]        # ПЛАН, не буквальное имя папки и не два движка сразу
```

В Git папки без файлов не сохраняются. В локальном пакете могут быть `.gitkeep` для их фиксации. **Не помещать Unity и Unreal проекты одновременно:** после решения владельца выбирается один движок, под него адаптируется `game/` и соответствующие `.gitignore`/`.gitattributes`.

## 2. Уже подготовленные оригинальные концепты для импорта

**Боссы (`assets/references/bosses/`):**
- `koschei_bessmertny.png` — УТВЕРЖДЁН
- `zmey_gorynych.png` — УТВЕРЖДЁН
- `likho_odnoglazoe.png` — УТВЕРЖДЁН
- `poludnitsa.png` — УТВЕРЖДЁН
- `utoplennitsa.png` — УТВЕРЖДЁН

**Рядовые враги:** `fallen_warriors/{fallen_warrior_base,fallen_warrior_variants_triptych}.png`, `bellringers/{bellringer_base,bellringer_variants_triptych}.png`, `morovoi_volkhv/{morovoi_volkhv_base,morovoi_volkhv_variants_triptych}.png`, `dead_archer/dead_archer_base.png` — УТВЕРЖДЕНЫ; `dead_archer/dead_archer_variants_triptych_candidate.png` — только кандидат.

**Оружие — пять оригинальных референс-листов, 20 разновидностей (2026-10-25):**
- `weapons/01_two_handed_weapons.png`
- `weapons/02_magic_staves.png`
- `weapons/03_dual_weapons.png`
- `weapons/04_bows.png`
- `weapons/05_combat_staves.png`

Указанные пути относительны к `assets/references/`; источники предоставлены владельцем и включены в импортный ZIP. Подробные SHA-256 и статус загрузки — в [WEAPON_REFERENCES.md](WEAPON_REFERENCES.md).

**Первая локация (ПОКА КАНДИДАТЫ):**
- `locations/first_location/first_location_master_candidate.png` — ранняя сводка.
- `locations/first_location/cursed_sloboda_master_concept.png` — единый общий вид.
- `locations/first_location/village_interior_01.png` — центр/колодец.
- `locations/first_location/village_interior_02.png` — улица поселения.
- `locations/first_location/village_interior_03.png` — святилище.

Все пути относительны к `assets/references/`. **Физическое наличие в GitHub подтверждается только после реального импорта файлов, а не появлением пути в этом документе.**

**Главный герой и игровой look (переданы владельцем 2026-10-25, вне ZIP-архива):**
- `hero/hero_reference_front_back.png` — утверждённый референс внешности героя (`VISUAL_APPROVED` для дизайна, спрайт не создан): [HERO_REFERENCE.md](HERO_REFERENCE.md).
- `gameplay/gameplay_look_reference.png` — ориентир игрового вида (`LOOK_REFERENCE`, не утверждённая локация): [ART_DIRECTION.md](ART_DIRECTION.md).

## 3. Правила именования и контроля

- В файловых путях ASCII `snake_case`; стабильные имена, без «финал2_последний» и без перезаписи утверждённых референсов без явного разрешения.
- Каждая строка `CONCEPT_ART_INDEX.md`: путь, название, утверждение, назначение, источник, SHA-256 и `PNG_IN_REPO` после проверки.
- `APPROVED` / `CANDIDATE` / `TODO` не путать со статусом импорта и готовностью к игре.
- Оригиналы референсов храним отдельно от рабочих моделей; файлы `.blend`, `.fbx`, анимационные клипы, игровые префабы — другие классы артефактов.
- Репозиторий публичный: не публиковать исходники платных/сторонних моделей, анимаций и ассетов без подтверждённых прав на распространение; лицензии фиксировать отдельно.
- Для крупных бинарных игровых файлов настроить Git LFS перед массовой загрузкой; LFS не заменяет лицензирование и резервные копии.

## 4. Передача DeepSeek

В начале задачи агент читает `docs/DEEPSEEK_GAME_DEV_RULES.md`, затем релевантные канонические документы и `docs/GLOBAL_ASSET_PASSES.md`. По работе с первой локацией **обязателен** `docs/FIRST_LOCATION_ART_RULES.md`.

Все модели/элементы окружения проходят глобальные стадии **для всего утверждённого объёма**, а не одну модель до финала. Любой новый арт — `CANDIDATE` до утверждения владельцем. Подсказки и блокеры оформляются по `docs/AI_HINT_LIBRARY.md` и `docs/AI_STUDIO_PLAYBOOK.md`.

## 5. Как импортировать локальный архив

Архив `rogalik_ready_structure_and_location_rules.zip` содержит папку `rogalik/`. Копировать **содержимое этой папки** в корень клона `alfuwerce-art/rogalik`, сохраняя уже существующие документы; не удалять и не заменять остальные файлы. Перед коммитом проверить `git status`, затем `git diff --stat`, выборочно изображения и индексы. Коммитить отдельно docs и изображения удобно для проверки.

Держать `docs/CONCEPT_ART_INDEX.md` синхронизированным с реальными файлами. Внешние ссылки и Markdown записи **не** являются фактическим импортом PNG.
