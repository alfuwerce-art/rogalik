# Импорт референсов Rogalik — отчёт о проверке

**TASK:** проверить ZIP `assets/archives/rogalik_all_concept_art_with_weapons.zip`, распаковать 23 оригинальных PNG в `assets/references/` и сверить их с документацией.

**STATUS: PASS** — 23/23 PNG распакованы, SHA-256 совпадают с манифестом, все изображения открываются; кандидаты не выданы за утверждённые референсы.

> Отчёт сгенерирован скриптом `tools/reference_import/make_report.py` из машинных результатов `reports/reference_import.json` и `reports/reference_import_verify.json`.

## 1. Архив

| Параметр | Значение |
|---|---|
| Путь | `assets/archives/rogalik_all_concept_art_with_weapons.zip` |
| Размер | 68 551 781 байт (65.376 МиБ) |
| SHA-256 | `e900eaad8806b881eb91d51ea649d9f2ad1131974a3687bd67628a3515169b23` |
| Членов в ZIP | 36: 23 PNG, `IMPORT_README.md`, `REFERENCE_FILE_MANIFEST.sha256`, 11 `.gitkeep` |
| Манифест | `rogalik/docs/REFERENCE_FILE_MANIFEST.sha256` — 23 записей; копия сохранена в `docs/REFERENCE_FILE_MANIFEST.sha256` |

Проверки целостности (повторяются независимым скриптом `verify_import.py`):

| Проверка | Результат |
|---|---|
| `ZipFile.testzip()` — CRC всех членов | PASS: повреждений нет |
| PNG в архиве | 23 (ожидалось 23) |
| SHA-256 каждого PNG против манифеста | 23/23 совпадают |
| Дубликаты (имена без учёта регистра) | нет |
| Дубликаты (одинаковое содержимое) | нет — 23 уникальных SHA-256 |
| Zip-slip (`..`, абсолютные пути, буква диска) | нет |
| Симлинки в архиве | нет |
| Архив после импорта | не изменён: SHA-256 и размер те же |

## 2. Распаковка

Распакованы только 23 PNG; вложенный префикс `rogalik/` снят, структура `assets/references/` сохранена, лишней вложенности нет. Служебные `.gitkeep` не копировались. Существующих файлов не было, перезаписей и конфликтов — 0.

```text
assets/references/
├── bosses/                                  5 PNG
├── enemies/                                 8 PNG
│   ├── bellringers/                         2
│   ├── dead_archer/                         2
│   ├── fallen_warriors/                     2
│   └── morovoi_volkhv/                      2
├── locations/first_location/                5 PNG
└── weapons/                                 5 PNG
```

Файлы побайтово равны содержимому архива: никакой конвертации, пересжатия, переименования или изменения метаданных не выполнялось.

## 3. Соответствие документации — все 23 файла

| # | Файл | Размер, байт | PNG | SHA-256 (начало) | Соответствие | Статус | Источник в docs |
|---|---|---|---|---|---|---|---|
| 1 | `bosses/koschei_bessmertny.png` | 2695734 | 1122×1402 | `c58d792f38cd05a2…` | B01 Кощей Бессмертный — иссохший князь, старорусский венец, клинок, чёрная сфера | `VISUAL_APPROVED` | BOSS_REFERENCES.md, BESTIARY.md |
| 2 | `bosses/likho_odnoglazoe.png` | 2928980 | 1024×1536 | `11d5a37f2b4ca784…` | B03 Лихо Одноглазое — сгорбленный одноглазый гигант, длинные когти | `VISUAL_APPROVED` | BOSS_REFERENCES.md, BESTIARY.md |
| 3 | `bosses/poludnitsa.png` | 2716015 | 1024×1536 | `fb1bf760eaee8b6a…` | B04 Полудница — жница в пшеничном венце, человеческие кисти, жнецовый серп | `VISUAL_APPROVED` | BOSS_REFERENCES.md, BESTIARY.md |
| 4 | `bosses/utoplennitsa.png` | 2725848 | 1024×1536 | `2e160986e5cd9be0…` | B05 Утопленница — бледная утопленница у мостков, белая рубаха с вышивкой | `VISUAL_APPROVED` | BOSS_REFERENCES.md, BESTIARY.md |
| 5 | `bosses/zmey_gorynych.png` | 3075120 | 1122×1402 | `3e4c8ebe2b493157…` | B02 Змей Горыныч — трёхголовый крылатый змей над горящей крепостью | `VISUAL_APPROVED` | BOSS_REFERENCES.md, BESTIARY.md |
| 6 | `enemies/bellringers/bellringer_base.png` | 2756353 | 1024×1536 | `eea463f705ba9611…` | E02 Погребальные звонари, база — колоколообразный шлем, шипованная булава | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 7 | `enemies/bellringers/bellringer_variants_triptych.png` | 3166858 | 1536×1024 | `999ca3299ad0f1f5…` | E02 Погребальные звонари, 3 варианта — древковое оружие, цепной кистень, колокольный молот | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 8 | `enemies/dead_archer/dead_archer_base.png` | 2865919 | 1024×1536 | `da07ef6e26385251…` | E04 Мёртвый стрелок, утверждённая база — капюшон, костяная маска, длинный лук | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 9 | `enemies/dead_archer/dead_archer_variants_triptych_candidate.png` | 3057234 | 1536×1024 | `e6f0a7a4b4840456…` | E04 Мёртвый стрелок, 3 кандидата — дозорный, проклятый стрелец, могильный арбалетчик | `VISUAL_CANDIDATE` | BESTIARY.md (E04), CONCEPT_ART_INDEX.md |
| 10 | `enemies/fallen_warriors/fallen_warrior_base.png` | 2615419 | 1024×1536 | `7b456d24e0ed5244…` | E01 Павшие ратники, база — секира и круглый деревянный щит | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 11 | `enemies/fallen_warriors/fallen_warrior_variants_triptych.png` | 3153633 | 1536×1024 | `ac1d31adef7122c2…` | E01 Павшие ратники, 3 варианта — мечник, громила с булавой, копейщик | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 12 | `enemies/morovoi_volkhv/morovoi_volkhv_base.png` | 2880261 | 1024×1536 | `54883ab8abe1c33a…` | E03 Моровые волхвы, база — клювообразная маска, ветвистый венец, посох | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 13 | `enemies/morovoi_volkhv/morovoi_volkhv_variants_triptych.png` | 3159833 | 1448×1086 | `e1ed8bdbad444d7b…` | E03 Моровые волхвы, 3 варианта — костяной посох, ветвистый колокольный, светильник | `VISUAL_APPROVED` | BESTIARY.md, CONCEPT_ART_INDEX.md |
| 14 | `locations/first_location/cursed_sloboda_master_concept.png` | 3193111 | 1672×941 | `8a34019a59123922…` | «Проклятая слобода», широкий мастер-обзор поселения (кандидат) | `VISUAL_CANDIDATE` | CONCEPT_ART_INDEX.md, FIRST_LOCATION_CONCEPT.md |
| 15 | `locations/first_location/first_location_master_candidate.png` | 2903510 | 1672×941 | `e701db0a8f1b44e4…` | Первый мастер-лист: три композиции — ворота, площадь, речной сектор (кандидат) | `VISUAL_CANDIDATE` | CONCEPT_ART_INDEX.md, FIRST_LOCATION_CONCEPT.md |
| 16 | `locations/first_location/village_interior_01.png` | 3082139 | 1672×941 | `8ea7f8d2d54ec9cb…` | Въезд: частокол, воротная башня, мокрая колея (кандидат) | `VISUAL_CANDIDATE` | CONCEPT_ART_INDEX.md |
| 17 | `locations/first_location/village_interior_02.png` | 3151708 | 1672×941 | `002892f1f4c0eff9…` | Улица срубов с фонарями (кандидат) | `VISUAL_CANDIDATE` | CONCEPT_ART_INDEX.md |
| 18 | `locations/first_location/village_interior_03.png` | 2892984 | 1672×941 | `49b8a5d93c5de3b3…` | Белокаменное святилище со ступенями (кандидат) | `VISUAL_CANDIDATE` | CONCEPT_ART_INDEX.md |
| 19 | `weapons/01_two_handed_weapons.png` | 3286880 | 1672×941 | `a95f7e606b6a40bd…` | Двуручное: колоссальный меч, двуручный топор, катана, сбалансированный двуручный меч | `APPROVED` | WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md |
| 20 | `weapons/02_magic_staves.png` | 3284487 | 1672×941 | `861774fb7fcabc8d…` | Магические посохи: посох чародея, ритуальный, призматический, астральный | `APPROVED` | WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md |
| 21 | `weapons/03_dual_weapons.png` | 3418979 | 1672×941 | `f82ce5d88d888cba…` | Парное: две секиры, два кинжала, два серпа, два боевых молота | `APPROVED` | WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md |
| 22 | `weapons/04_bows.png` | 3195264 | 1672×941 | `d28986462a987d62…` | Луки: короткий, длинный, тяжёлый, рекурсивный | `APPROVED` | WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md |
| 23 | `weapons/05_combat_staves.png` | 3185219 | 1672×941 | `f7c53ef5c76990ef…` | Боевые посохи: деревянный, железный, трёхсекционный (с цепями), с кольцами | `APPROVED` | WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md |

Полные SHA-256 — в `reports/reference_import_verify.json` и в `docs/REFERENCE_FILE_MANIFEST.sha256`.

### Проверка утверждённых хешей из документации

- `docs/BOSS_REFERENCES.md`: SHA-256, размер в байтах и 1024×1536 для Полудницы и Утопленницы — совпадают.
- `docs/WEAPON_REFERENCES.md`: 5 SHA-256 и размер 1672×941 для всех листов оружия — совпадают.
- `docs/CONCEPT_ART_INDEX.md`: все 23 целевых пути существуют на диске; лишних файлов в `assets/references/` нет.

### Визуальная сверка

Изображения открыты и просмотрены по контрольным листам `reports/reference_import_sheets/{bosses,enemies,weapons,locations}.png` (уменьшенные копии только для просмотра; оригиналы не изменялись):

- **Боссы** — все 5 соответствуют описаниям: венец и чёрная сфера у Кощея, три головы у Горыныча, один глаз и когти у Лиха, пшеничный венец и серп у Полудницы, белая рубаха и мостки у Утопленницы.
- **Враги** — базы и триптихи совпадают с BESTIARY: звонари с колоколообразным шлемом и финальным набором оружия, ратники с секирой/щитом и тремя вариантами, волхвы с клювообразной маской, лучник с костяной маской и луком.
- **Оружие** — 5 листов по 4 разновидности (20 видов); в `05_combat_staves.png` виден трёхсекционный посох с цепями, как требует WEAPON_REFERENCES.
- **Локации** — 5 кандидатов: мастер-обзор слободы, мастер-лист из трёх композиций, ворота, улица срубов, белокаменное святилище. Ни один не помечен утверждённым.

## 4. Утверждённые референсы и кандидаты

**17 утверждённых файлов** (5 боссов, 7 обычных врагов, 5 листов оружия) и **6 кандидатов** (5 локаций + триптих Мёртвого стрелка). Статусы взяты из BESTIARY.md и CONCEPT_ART_INDEX.md и в отчёте не повышены.

Кандидаты:

- `enemies/dead_archer/dead_archer_variants_triptych_candidate.png` — E04 Мёртвый стрелок, 3 кандидата — дозорный, проклятый стрелец, могильный арбалетчик
- `locations/first_location/cursed_sloboda_master_concept.png` — «Проклятая слобода», широкий мастер-обзор поселения (кандидат)
- `locations/first_location/first_location_master_candidate.png` — Первый мастер-лист: три композиции — ворота, площадь, речной сектор (кандидат)
- `locations/first_location/village_interior_01.png` — Въезд: частокол, воротная башня, мокрая колея (кандидат)
- `locations/first_location/village_interior_02.png` — Улица срубов с фонарями (кандидат)
- `locations/first_location/village_interior_03.png` — Белокаменное святилище со ступенями (кандидат)

## 5. Найденные расхождения в документации

1. `docs/FIRST_LOCATION_CONCEPT.md` указывал устаревший целевой путь `assets/references/locations/location_01_cursed_sloboda_concept.png`; фактический файл — `assets/references/locations/first_location/first_location_master_candidate.png` (SHA-256 совпадает с указанным в документе). Строка исправлена, статус кандидата не изменён.
2. В таблице оружия `docs/CONCEPT_ART_INDEX.md` у строки `04_bows.png` было пустое имя семейства; подставлено `bows` по WEAPON_REFERENCES.md.
3. Имена `village_interior_01..03.png` фактически содержат внешние виды деревни (ворота, улица, святилище), а не интерьеры. Файлы не переименовывались: имена зафиксированы в манифесте. Расхождение только номинальное.
4. `docs/BESTIARY.md` (п. 3) всё ещё описывает стиль как «стилизованное 3D/2.5D», тогда как действующий канон — 2D Pixel Art top-down (DEEPSEEK_GAME_DEV_RULES.md, PIXEL_ART_STYLE_GUIDE.md). Документ не менялся — это вопрос канона для владельца.

## 6. Что намеренно не делалось

- ZIP не перемещался, не пересжимался и не изменялся; оригинал остаётся в `assets/archives/`.
- PNG не конвертировались, не масштабировались и не пересжимались.
- Игровые спрайты, тайлсеты и атласы не создавались.
- Коммит и push в GitHub не выполнялись: `PNG_IN_REPO` остаётся `false`.

## 7. Воспроизведение проверки

```powershell
$py = "C:\Users\bow\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONIOENCODING = "utf-8"
& $py tools\reference_import\inspect_zip.py assets\archives\rogalik_all_concept_art_with_weapons.zip
& $py tools\reference_import\verify_import.py .
& $py tools\reference_import\make_report.py .
```

## 8. Артефакты

| Артефакт | Назначение |
|---|---|
| `assets/archives/rogalik_all_concept_art_with_weapons.zip` | исходный архив, не изменён |
| `assets/references/**` (23 PNG) | проверенные оригиналы для разработки |
| `docs/REFERENCE_FILE_MANIFEST.sha256` | манифест контрольных сумм (копия из архива) |
| `tools/reference_import/inspect_zip.py` | проверка архива: CRC, манифест, опасные пути |
| `tools/reference_import/import_references.py` | безопасная распаковка без перезаписи |
| `tools/reference_import/verify_import.py` | независимая повторная проверка |
| `tools/reference_import/contact_sheets.py` | контрольные листы для визуального просмотра |
| `reports/reference_import.json` | журнал распаковки по файлам |
| `reports/reference_import_verify.json` | результаты проверок |
| `reports/reference_import_sheets/*.png` | уменьшенные листы для просмотра |
| `reports/reference_zip_inspect.json` | первичный разбор архива |
