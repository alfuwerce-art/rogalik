# Каталог исходных концепт-артов (импорт из локального пакета)

> Версия 2026-10-25. **Внимание: все приведённые пути — целевые при импорте.** Пока реальные PNG не проверены в GitHub, `PNG_IN_REPO = false`. Индекс фиксирует статус художественного решения, но не заменяет бинарное изображение.

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

## Первая локация — пять кандидатов, пока НЕ утверждены

- `assets/references/locations/first_location/first_location_master_candidate.png`
- `assets/references/locations/first_location/cursed_sloboda_master_concept.png`
- `assets/references/locations/first_location/village_interior_01.png`
- `assets/references/locations/first_location/village_interior_02.png`
- `assets/references/locations/first_location/village_interior_03.png`

Названия и композиции описаны в [FIRST_LOCATION_CONCEPT.md](FIRST_LOCATION_CONCEPT.md). При разработке обязательно учитывать [FIRST_LOCATION_ART_RULES.md](FIRST_LOCATION_ART_RULES.md).

## Обращение с файлами

- Имена в GitHub латиницей `snake_case`. Исходные изображения хранить неизменными; любые модификации — отдельные имена/версии.
- Триптихи — изображения для визуального направления, а не три готовые 3D-модели.
- Перед присвоением `PNG_IN_REPO` убедиться, что GitHub реально содержит PNG с ожидаемым размером/хешем.
- Источник и контрольные суммы оригиналов хранятся в приложенном локальном пакете (`REFERENCE_FILE_MANIFEST.sha256`).
- Сам факт записи этого Markdown **не загружает графику в GitHub**.
