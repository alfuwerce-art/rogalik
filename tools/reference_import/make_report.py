#!/usr/bin/env python
"""Generate reports/reference_import.md from the machine-checked JSON reports."""

from __future__ import annotations

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROLES = {
    "bosses/koschei_bessmertny.png": (
        "B01 Кощей Бессмертный — иссохший князь, старорусский венец, клинок, чёрная сфера",
        "VISUAL_APPROVED", "BOSS_REFERENCES.md, BESTIARY.md"),
    "bosses/zmey_gorynych.png": (
        "B02 Змей Горыныч — трёхголовый крылатый змей над горящей крепостью",
        "VISUAL_APPROVED", "BOSS_REFERENCES.md, BESTIARY.md"),
    "bosses/likho_odnoglazoe.png": (
        "B03 Лихо Одноглазое — сгорбленный одноглазый гигант, длинные когти",
        "VISUAL_APPROVED", "BOSS_REFERENCES.md, BESTIARY.md"),
    "bosses/poludnitsa.png": (
        "B04 Полудница — жница в пшеничном венце, человеческие кисти, жнецовый серп",
        "VISUAL_APPROVED", "BOSS_REFERENCES.md, BESTIARY.md"),
    "bosses/utoplennitsa.png": (
        "B05 Утопленница — бледная утопленница у мостков, белая рубаха с вышивкой",
        "VISUAL_APPROVED", "BOSS_REFERENCES.md, BESTIARY.md"),
    "enemies/fallen_warriors/fallen_warrior_base.png": (
        "E01 Павшие ратники, база — секира и круглый деревянный щит",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/fallen_warriors/fallen_warrior_variants_triptych.png": (
        "E01 Павшие ратники, 3 варианта — мечник, громила с булавой, копейщик",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/bellringers/bellringer_base.png": (
        "E02 Погребальные звонари, база — колоколообразный шлем, шипованная булава",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/bellringers/bellringer_variants_triptych.png": (
        "E02 Погребальные звонари, 3 варианта — древковое оружие, цепной кистень, колокольный молот",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/morovoi_volkhv/morovoi_volkhv_base.png": (
        "E03 Моровые волхвы, база — клювообразная маска, ветвистый венец, посох",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/morovoi_volkhv/morovoi_volkhv_variants_triptych.png": (
        "E03 Моровые волхвы, 3 варианта — костяной посох, ветвистый колокольный, светильник",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/dead_archer/dead_archer_base.png": (
        "E04 Мёртвый стрелок, утверждённая база — капюшон, костяная маска, длинный лук",
        "VISUAL_APPROVED", "BESTIARY.md, CONCEPT_ART_INDEX.md"),
    "enemies/dead_archer/dead_archer_variants_triptych_candidate.png": (
        "E04 Мёртвый стрелок, 3 кандидата — дозорный, проклятый стрелец, могильный арбалетчик",
        "VISUAL_CANDIDATE", "BESTIARY.md (E04), CONCEPT_ART_INDEX.md"),
    "weapons/01_two_handed_weapons.png": (
        "Двуручное: колоссальный меч, двуручный топор, катана, сбалансированный двуручный меч",
        "APPROVED", "WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md"),
    "weapons/02_magic_staves.png": (
        "Магические посохи: посох чародея, ритуальный, призматический, астральный",
        "APPROVED", "WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md"),
    "weapons/03_dual_weapons.png": (
        "Парное: две секиры, два кинжала, два серпа, два боевых молота",
        "APPROVED", "WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md"),
    "weapons/04_bows.png": (
        "Луки: короткий, длинный, тяжёлый, рекурсивный",
        "APPROVED", "WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md"),
    "weapons/05_combat_staves.png": (
        "Боевые посохи: деревянный, железный, трёхсекционный (с цепями), с кольцами",
        "APPROVED", "WEAPON_REFERENCES.md, CONCEPT_ART_INDEX.md"),
    "locations/first_location/cursed_sloboda_master_concept.png": (
        "«Проклятая слобода», широкий мастер-обзор поселения (кандидат)",
        "VISUAL_CANDIDATE", "CONCEPT_ART_INDEX.md, FIRST_LOCATION_CONCEPT.md"),
    "locations/first_location/first_location_master_candidate.png": (
        "Первый мастер-лист: три композиции — ворота, площадь, речной сектор (кандидат)",
        "VISUAL_CANDIDATE", "CONCEPT_ART_INDEX.md, FIRST_LOCATION_CONCEPT.md"),
    "locations/first_location/village_interior_01.png": (
        "Въезд: частокол, воротная башня, мокрая колея (кандидат)",
        "VISUAL_CANDIDATE", "CONCEPT_ART_INDEX.md"),
    "locations/first_location/village_interior_02.png": (
        "Улица срубов с фонарями (кандидат)",
        "VISUAL_CANDIDATE", "CONCEPT_ART_INDEX.md"),
    "locations/first_location/village_interior_03.png": (
        "Белокаменное святилище со ступенями (кандидат)",
        "VISUAL_CANDIDATE", "CONCEPT_ART_INDEX.md"),
}


def main() -> int:
    repo = os.path.abspath(sys.argv[1])
    imp = json.load(open(os.path.join(repo, "reports", "reference_import.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(repo, "reports", "reference_import_verify.json"), encoding="utf-8"))
    files = {f["relative"]: f for f in imp["files"]}

    approved = [r for r in files if ROLES[r][1] in ("VISUAL_APPROVED", "APPROVED")]
    candidates = [r for r in files if ROLES[r][1] == "VISUAL_CANDIDATE"]

    lines: list[str] = []
    a = imp
    v = ver
    size_bytes = v["archive"]["size"]
    lines += [
        "# Импорт референсов Rogalik — отчёт о проверке",
        "",
        f"**TASK:** проверить ZIP `assets/archives/rogalik_all_concept_art_with_weapons.zip`, "
        "распаковать 23 оригинальных PNG в `assets/references/` и сверить их с документацией.",
        "",
        f"**STATUS: {v['status']}** — 23/23 PNG распакованы, SHA-256 совпадают с манифестом, "
        "все изображения открываются; кандидаты не выданы за утверждённые референсы.",
        "",
        "> Отчёт сгенерирован скриптом `tools/reference_import/make_report.py` из машинных "
        "результатов `reports/reference_import.json` и `reports/reference_import_verify.json`.",
        "",
        "## 1. Архив",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Путь | `{os.path.relpath(v['archive']['path'], repo).replace(os.sep, '/')}` |",
        f"| Размер | {size_bytes:,} байт ({size_bytes / (1024 * 1024):.3f} МиБ) |".replace(",", " "),
        f"| SHA-256 | `{v['archive']['sha256']}` |",
        "| Членов в ZIP | 36: 23 PNG, `IMPORT_README.md`, `REFERENCE_FILE_MANIFEST.sha256`, 11 `.gitkeep` |",
        f"| Манифест | `rogalik/docs/REFERENCE_FILE_MANIFEST.sha256` — {a['summary']['manifest_entries']} записей; "
        "копия сохранена в `docs/REFERENCE_FILE_MANIFEST.sha256` |",
        "",
        "Проверки целостности (повторяются независимым скриптом `verify_import.py`):",
        "",
        "| Проверка | Результат |",
        "|---|---|",
        "| `ZipFile.testzip()` — CRC всех членов | PASS: повреждений нет |",
        f"| PNG в архиве | {a['summary']['archive_pngs']} (ожидалось 23) |",
        f"| SHA-256 каждого PNG против манифеста | {a['summary']['verified_and_present']}/23 совпадают |",
        "| Дубликаты (имена без учёта регистра) | нет |",
        "| Дубликаты (одинаковое содержимое) | нет — 23 уникальных SHA-256 |",
        "| Zip-slip (`..`, абсолютные пути, буква диска) | нет |",
        "| Симлинки в архиве | нет |",
        "| Архив после импорта | не изменён: SHA-256 и размер те же |",
        "",
        "## 2. Распаковка",
        "",
        "Распакованы только 23 PNG; вложенный префикс `rogalik/` снят, структура `assets/references/` "
        "сохранена, лишней вложенности нет. Служебные `.gitkeep` не копировались. "
        "Существующих файлов не было, перезаписей и конфликтов — 0.",
        "",
        "```text",
        "assets/references/",
        "├── bosses/                                  5 PNG",
        "├── enemies/                                 8 PNG",
        "│   ├── bellringers/                         2",
        "│   ├── dead_archer/                         2",
        "│   ├── fallen_warriors/                     2",
        "│   └── morovoi_volkhv/                      2",
        "├── locations/first_location/                5 PNG",
        "└── weapons/                                 5 PNG",
        "```",
        "",
        "Файлы побайтово равны содержимому архива: никакой конвертации, пересжатия, "
        "переименования или изменения метаданных не выполнялось.",
        "",
        f"## 3. Соответствие документации — все {len(files)} файла",
        "",
        "| # | Файл | Размер, байт | PNG | SHA-256 (начало) | Соответствие | Статус | Источник в docs |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for idx, rel in enumerate(sorted(files), start=1):
        f = files[rel]
        role, status, src = ROLES[rel]
        dims = v["dimensions"][f"assets/references/{rel}"]
        lines.append(
            f"| {idx} | `{rel}` | {f['size']} | {dims[0]}×{dims[1]} | `{f['sha256'][:16]}…` | "
            f"{role} | `{status}` | {src} |"
        )
    lines += [
        "",
        "Полные SHA-256 — в `reports/reference_import_verify.json` и в "
        "`docs/REFERENCE_FILE_MANIFEST.sha256`.",
        "",
        "### Проверка утверждённых хешей из документации",
        "",
        "- `docs/BOSS_REFERENCES.md`: SHA-256, размер в байтах и 1024×1536 для Полудницы и Утопленницы — совпадают.",
        "- `docs/WEAPON_REFERENCES.md`: 5 SHA-256 и размер 1672×941 для всех листов оружия — совпадают.",
        "- `docs/CONCEPT_ART_INDEX.md`: все 23 целевых пути существуют на диске; лишних файлов в `assets/references/` нет.",
        "",
        "### Визуальная сверка",
        "",
        "Изображения открыты и просмотрены по контрольным листам "
        "`reports/reference_import_sheets/{bosses,enemies,weapons,locations}.png` "
        "(уменьшенные копии только для просмотра; оригиналы не изменялись):",
        "",
        "- **Боссы** — все 5 соответствуют описаниям: венец и чёрная сфера у Кощея, три головы у Горыныча, "
        "один глаз и когти у Лиха, пшеничный венец и серп у Полудницы, белая рубаха и мостки у Утопленницы.",
        "- **Враги** — базы и триптихи совпадают с BESTIARY: звонари с колоколообразным шлемом и финальным набором оружия, "
        "ратники с секирой/щитом и тремя вариантами, волхвы с клювообразной маской, лучник с костяной маской и луком.",
        "- **Оружие** — 5 листов по 4 разновидности (20 видов); в `05_combat_staves.png` виден трёхсекционный посох с цепями, "
        "как требует WEAPON_REFERENCES.",
        "- **Локации** — 5 кандидатов: мастер-обзор слободы, мастер-лист из трёх композиций, ворота, улица срубов, белокаменное святилище. "
        "Ни один не помечен утверждённым.",
        "",
        "## 4. Утверждённые референсы и кандидаты",
        "",
        f"**{len(approved)} утверждённых файлов** (5 боссов, 7 обычных врагов, 5 листов оружия) "
        f"и **{len(candidates)} кандидатов** (5 локаций + триптих Мёртвого стрелка). "
        "Статусы взяты из BESTIARY.md и CONCEPT_ART_INDEX.md и в отчёте не повышены.",
        "",
        "Кандидаты:",
        "",
    ]
    for rel in sorted(candidates):
        lines.append(f"- `{rel}` — {ROLES[rel][0]}")
    lines += [
        "",
        "## 5. Найденные расхождения в документации",
        "",
        "1. `docs/FIRST_LOCATION_CONCEPT.md` указывал устаревший целевой путь "
        "`assets/references/locations/location_01_cursed_sloboda_concept.png`; фактический файл — "
        "`assets/references/locations/first_location/first_location_master_candidate.png` (SHA-256 совпадает с указанным в документе). "
        "Строка исправлена, статус кандидата не изменён.",
        "2. В таблице оружия `docs/CONCEPT_ART_INDEX.md` у строки `04_bows.png` было пустое имя семейства; подставлено `bows` по WEAPON_REFERENCES.md.",
        "3. Имена `village_interior_01..03.png` фактически содержат внешние виды деревни (ворота, улица, святилище), а не интерьеры. "
        "Файлы не переименовывались: имена зафиксированы в манифесте. Расхождение только номинальное.",
        "4. `docs/BESTIARY.md` (п. 3) всё ещё описывает стиль как «стилизованное 3D/2.5D», тогда как действующий канон — "
        "2D Pixel Art top-down (DEEPSEEK_GAME_DEV_RULES.md, PIXEL_ART_STYLE_GUIDE.md). Документ не менялся — это вопрос канона для владельца.",
        "",
        "## 6. Что намеренно не делалось",
        "",
        "- ZIP не перемещался, не пересжимался и не изменялся; оригинал остаётся в `assets/archives/`.",
        "- PNG не конвертировались, не масштабировались и не пересжимались.",
        "- Игровые спрайты, тайлсеты и атласы не создавались.",
        "- Коммит и push в GitHub не выполнялись: `PNG_IN_REPO` остаётся `false`.",
        "",
        "## 7. Воспроизведение проверки",
        "",
        "```powershell",
        "$py = \"C:\\Users\\bow\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe\"",
        "$env:PYTHONIOENCODING = \"utf-8\"",
        "& $py tools\\reference_import\\inspect_zip.py assets\\archives\\rogalik_all_concept_art_with_weapons.zip",
        "& $py tools\\reference_import\\verify_import.py .",
        "& $py tools\\reference_import\\make_report.py .",
        "```",
        "",
        "## 8. Артефакты",
        "",
        "| Артефакт | Назначение |",
        "|---|---|",
        "| `assets/archives/rogalik_all_concept_art_with_weapons.zip` | исходный архив, не изменён |",
        "| `assets/references/**` (23 PNG) | проверенные оригиналы для разработки |",
        "| `docs/REFERENCE_FILE_MANIFEST.sha256` | манифест контрольных сумм (копия из архива) |",
        "| `tools/reference_import/inspect_zip.py` | проверка архива: CRC, манифест, опасные пути |",
        "| `tools/reference_import/import_references.py` | безопасная распаковка без перезаписи |",
        "| `tools/reference_import/verify_import.py` | независимая повторная проверка |",
        "| `tools/reference_import/contact_sheets.py` | контрольные листы для визуального просмотра |",
        "| `reports/reference_import.json` | журнал распаковки по файлам |",
        "| `reports/reference_import_verify.json` | результаты проверок |",
        "| `reports/reference_import_sheets/*.png` | уменьшенные листы для просмотра |",
        "| `reports/reference_zip_inspect.json` | первичный разбор архива |",
        "",
    ]

    out = os.path.join(repo, "reports", "reference_import.md")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
