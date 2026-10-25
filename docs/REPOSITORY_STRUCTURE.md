# Структура репозитория Rogalik (план и порядок импорта)

> Обновление 2026-10-25: **визуальный канон — 2D Pixel Art** ([PIXEL_ART_STYLE_GUIDE.md](PIXEL_ART_STYLE_GUIDE.md)), **движок утверждён — Godot 4.7.2** (D1). Дерево ниже описывает **фактическое** состояние рабочей ветки. Устаревшие пути `sources/3D models`, `exports/` FBX/GLB и схема `game/[unity-or-unreal]` — `ARCHIVED`, в проекте не используются.

## 1. Корневая структура

```text
rogalik/
├── README.md
├── .gitignore
├── .gitattributes                # бинарные типы (PNG/PXO/ZIP); Git LFS не подключён (D13)
├── LICENSE
├── AGENTS.md                     # правила для ИИ-разработчиков (основной вход)
├── docs/
│   ├── DEVELOPMENT_PLAN.md       # утверждённый порядок этапов 0–6
│   ├── DECISIONS.md              # журнал решений владельца
│   ├── DEEPSEEK_GAME_DEV_RULES.md
│   ├── AI_STUDIO_PLAYBOOK.md
│   ├── AI_HINT_LIBRARY.md
│   ├── GITHUB_WORKFLOW.md
│   ├── ROGALIK_DEV_ENVIRONMENT.md   # проверенная среда: Godot 4.7.2, Pixelorama 1.2.3, MCP
│   ├── DEV_ENVIRONMENT_SETUP.md
│   ├── PIXEL_ART_STYLE_GUIDE.md     # стандарт графики
│   ├── ART_DIRECTION.md             # художественное направление
│   ├── HERO_REFERENCE.md            # утверждённый референс героя
│   ├── BESTIARY.md                  # состав и роли врагов + §0 реестр доступности
│   ├── BOSS_REFERENCES.md
│   ├── WEAPON_REFERENCES.md
│   ├── SKILLS_AND_BOONS.md
│   ├── CONCEPT_ART_INDEX.md         # статусы файлов и артефактов
│   ├── REFERENCE_FILE_MANIFEST.sha256
│   ├── FIRST_LOCATION_CONCEPT.md    # кандидат
│   ├── FIRST_LOCATION_ART_RULES.md
│   ├── GLOBAL_ASSET_PASSES.md       # пакетные проходы (внутри Этапа 6)
│   ├── CHARACTER_PRODUCTION_PIPELINE.md  # ARCHIVED
│   ├── VISUAL_REFERENCES.md              # ARCHIVED
│   └── tasks/                   # задания и рубежи
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
│   └── archives/                # исходный ZIP владельца (не изменять, не удалять)
├── tools/                       # пайплайн, импорт референсов, локальные скрипты
│   ├── pixel_pipeline/          # .pxo → Pixelorama CLI → PNG/атлас, валидация
│   ├── reference_import/        # импорт и проверка оригиналов
│   ├── stage1_art/              # PROXY_TECHNICAL: процедурный автор спрайтов героя
│   ├── git/                     # check-memory-sync.ps1 — синхронность памяти и правил
│   └── setup-godot-mcp.ps1
├── plugins/                     # локальные бандлы DSH (env-check, pixel-pipeline, dev-preset)
├── reports/                     # проверяемые отчёты и снимки
└── game/
    └── prototype/                # технический Godot-проект (Этап 1), не утверждённая игра
        ├── project.godot
        ├── scenes/main.tscn
        ├── scripts/             # player.gd, capture.gd, mcp_interaction_server.gd
        └── art/                 # sprites/, demo-tool/ — PROXY_TECHNICAL
```

В Git папки без файлов не сохраняются. **Движок один — Godot** (D1); Unity/Unreal в проекте не используются. 2D-ассеты (спрайты, тайлсеты, атласы, анимации) живут в `assets/references/` (оригиналы) и `game/prototype/art/` (игровые заготовки); оригиналы никогда не смешиваются с игровыми файлами.

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
- Каждая строка `CONCEPT_ART_INDEX.md`: путь, название, утверждение, назначение, источник, SHA-256 и наличие файла (`COMMITTED_LOCAL` / `PUSHED`).
- `APPROVED` / `CANDIDATE` / `TODO` не путать со статусом импорта и готовностью к игре.
- Оригиналы референсов храним отдельно от игровых файлов; игровые спрайты/листы/атласы — другой класс артефактов, чем концепт-арт.
- Репозиторий публичный: не публиковать исходники платных/сторонних моделей, анимаций и ассетов без подтверждённых прав на распространение; лицензии фиксировать отдельно.
- Для крупных бинарных игровых файлов проверять лимиты GitHub до коммита: файл < 100 MB, предупреждение с 50 MB. Git LFS включается только по решению владельца и только для **новых** файлов: перевод уже закоммиченного ZIP (65,38 MB) требует перезаписи истории и запрещён (D13). LFS не заменяет лицензирование и резервные копии.

## 4. Передача DeepSeek

В начале задачи агент читает [AGENTS.md](../AGENTS.md) и [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), затем релевантные канонические документы и `docs/GLOBAL_ASSET_PASSES.md`. По работе с первой локацией **обязателен** `docs/FIRST_LOCATION_ART_RULES.md`.

Все модели/элементы окружения проходят глобальные стадии **для всего утверждённого объёма**, а не одну модель до финала. Любой новый арт — `CANDIDATE` до утверждения владельцем. Подсказки и блокеры оформляются по `docs/AI_HINT_LIBRARY.md` и `docs/AI_STUDIO_PLAYBOOK.md`.

## 5. Как импортировать локальный архив

Архив `rogalik_ready_structure_and_location_rules.zip` содержит папку `rogalik/`. Копировать **содержимое этой папки** в корень клона `alfuwerce-art/rogalik`, сохраняя уже существующие документы; не удалять и не заменять остальные файлы. Перед коммитом проверить `git status`, затем `git diff --stat`, выборочно изображения и индексы. Коммитить отдельно docs и изображения удобно для проверки.

Держать `docs/CONCEPT_ART_INDEX.md` синхронизированным с реальными файлами. Внешние ссылки и Markdown записи **не** являются фактическим импортом PNG.
