# D13/D14 — отчёт о первой публикации ветки

> **STATUS: `IN_PROGRESS`** — отчёт обновлён под решение D14: публикация выполняется автоматически, без предварительного подтверждения. Итоговый SHA и результат проверки удалённой ветки добавляются в §10 сразу после `push`.
> Решения: [DECISIONS.md D13/D14](../docs/DECISIONS.md) · Правила: [GITHUB_WORKFLOW.md](../docs/GITHUB_WORKFLOW.md) §5.
> Ветка публикации: **`stage1-playable-combat`** (новая удалённая ветка, не `main`).

## 1. Что публикуется

| Поле | Значение |
|---|---|
| Ветка | `stage1-playable-combat` |
| Ветка на GitHub сейчас | отсутствует (`git ls-remote --heads origin` → только `main`, `rogalik-dev`) |
| Коммит-родитель | `7538d5b` (D13) |
| SHA публикуемого коммита | коммит D14, содержащий этот отчёт — `git log -1 --format=%H` |
| База | `origin/main` = `e9f9128` — предок рабочей ветки (merge `be0d099`), история `main` не переписывается |
| Новых коммитов для origin | 12 (10 существующих + D13 + D14) |
| Строки истории не переписываются | `force` не применяется; `main` и `rogalik-dev` не затрагиваются |

## 2. Состав первой публикации (по индексу)

| Каталог | Файлов | Объём | Что это |
|---|---:|---:|---|
| `assets/references/` | 25 | 71,10 MB | 23 оригинала из ZIP владельца + `hero_reference_front_back.png` + `gameplay_look_reference.png` |
| `assets/archives/` | 1 | 65,38 MB | ZIP владельца `rogalik_all_concept_art_with_weapons.zip` (68 551 781 байт) |
| `reports/` | 21 | 7,75 MB | 13 PNG-снимков (контакт-листы, кадры Godot, превью спрайтов), JSON/MD-отчёты, этот отчёт и манифест |
| `tools/` | 28 | 0,31 MB | пайплайн `pixel_pipeline`, `reference_import`, `stage1_art`, `git/check-memory-sync.ps1`, `setup-godot-mcp.ps1` |
| `docs/` | 27 | 0,35 MB | канон, план, решения, память этапов, отчёты среды |
| `game/` | 20 | 0,20 MB | Godot-проект `prototype`: сцена, скрипты, `PROXY_TECHNICAL` спрайты, `.import` |
| `plugins/` | 19 | 0,04 MB | локальные бандлы DSH: `rogalik-env-check`, `rogalik-pixel-pipeline`, `rogalik-dev-preset` |
| корень | 5 | 0,03 MB | `AGENTS.md`, `README.md`, `LICENSE`, `.gitignore`, `.gitattributes` |
| **Итого** | **146** | **145,16 MB** (152 214 798 байт) | включая этот отчёт и `d13_publication_manifest.txt` (8 111 байт) |

Полный пофайловый список с размерами — [`d13_publication_manifest.txt`](d13_publication_manifest.txt) (генерируется из индекса; сам себя не перечисляет).

## 3. Бинарники

| Тип | Файлов | Объём |
|---|---:|---:|
| PNG всего | 46 | 78,94 MB (82 773 859 байт) |
| — `assets/references/` | 25 | 71,10 MB |
| — `reports/` (снимки-доказательства) | 13 | 7,67 MB |
| — `game/prototype/art/` | 4 | < 0,01 MB |
| — `tools/stage1_art/` (превью `PROXY_TECHNICAL`) | 4 | 0,16 MB |
| ZIP владельца | 1 | 65,38 MB |
| `.pxo` (демо-пайплайн) | 1 | 3 158 байт |
| **Бинарники итого** | **48** | **144,32 MB** |
| Текст (md/gd/py/json/yml/js/ps1/…) | 98 | 0,84 MB |

## 4. ZIP и Git LFS — решение

Факты:

- ZIP уже находится в истории коммита `61d1bda`; blob в `HEAD` (`9b4977a3c0aa1a4a3b13dd0561074daab711432b`) побайтово равен рабочему файлу.
- Размер 65,38 MB: **меньше** жёсткого лимита GitHub (100 MB на файл), **больше** порога предупреждения (50 MB). Файл пройдёт обычным объектом Git.
- `git-lfs 3.7.1` установлен в системе, но **не настроен и не используется**.
- Перевод уже закоммиченного blob в LFS требует перезаписи истории (`git lfs migrate`), что запрещено D13. Для новых файлов LFS можно включить только отдельным решением владельца и без переписывания прошлого.

**Предлагаемый способ загрузки ZIP:** обычный `git push` вместе с веткой, без LFS. ZIP не удаляется и не изменяется. Ожидаемое поведение GitHub — предупреждение о файле > 50 MB, не ошибка.

Альтернатива, если владелец захочет облегчить репозиторий (решение за ним, агент не выполняет сам): приложить ZIP как asset GitHub Release и убрать его из индекса **новым** коммитом, сохранив файл локально и в отчёте.

## 5. Что исключено и почему

| Исключено | Объём | Причина |
|---|---:|---|
| `tools/godot-mcp/` | ≈80,88 MB | сторонний клон с `node_modules`; восстанавливается `tools/setup-godot-mcp.ps1` |
| `.cache/` | 0,21 MB | локальный кэш инструментов |
| `game/prototype/.godot/` | 0,01 MB | импорт-кэш Godot, пересоздаётся |
| `__pycache__/` (4 каталога) | < 0,01 MB | байткод Python |
| `*.import~*.TMP` (2 файла) | < 0,01 MB | временные файлы импорта Godot |
| `build/` | 0 MB | производная сборка (пусто) |
| `*.log`, `.env*`, `*.pem`, `*.key`, `id_rsa*` | — | журналы и секреты не публикуются |

Секретов в индексе нет (проверка по именам файлов). Кэши, `node_modules`, виртуальные окружения и чужие репозитории не добавлялись.

## 6. Выполненные проверки

| Проверка | Команда | Результат |
|---|---|---|
| Ветка и чистота дерева | `git status`, `git branch -vv` | `stage1-playable-combat`, до задачи дерево чистое |
| Коммиты сверх `origin/main` | `git rev-list --count origin/main..HEAD` | 10 до коммита D13 |
| `origin/main` в истории ветки | `git merge-base --is-ancestor origin/main HEAD` | да |
| Совпадение ветки на GitHub | `git ls-remote --heads origin` | ветки нет → это первая публикация |
| Целостность оригиналов | `Get-FileHash -Algorithm SHA256` по `docs/REFERENCE_FILE_MANIFEST.sha256` | **23/23 совпадают** |
| ZIP не изменён | `git hash-object` vs `git rev-parse HEAD:assets/archives/…` | `9b4977a3…` = `9b4977a3…` |
| Исключения после правки `.gitignore` | `git status --ignored --porcelain` | набор совпадает с прежним, лишнего не появилось |
| Память и правила синхронны | `tools/git/check-memory-sync.ps1` | `PASS` |
| Секреты и крупные файлы | тот же скрипт | `FAIL` нет, `WARN` нет |

Не проверено на момент подготовки: авторизация GitHub на запись (см. §7), фактический ответ GitHub на push, отображение ZIP в веб-интерфейсе. Результат — §10.

## 7. Риски и ограничения

1. **Авторизация на запись.** Первый `git push --dry-run` вернул `could not read Username for 'https://github.com'` — сохранённого доступа не было. По D14 используется штатный Git Credential Manager (интерактивный вход); токен в чат и файлы не передаётся. Результат попытки — §10.
2. **Вес публикации ≈145 MB.** GitHub примет (лимит на файл 100 MB, рекомендация — до 1 GB на репозиторий), но push будет долгим, а клон — тяжёлым из-за ZIP. Решение о LFS/Release — за владельцем (§4).
3. **Предупреждение GitHub о файле > 50 MB** ожидаемо и не является ошибкой.
4. **Push не даёт права на `force`.** При отказе (авторизация, защита, размер) причина выясняется, история не переписывается.
5. После успешного push наличие файлов в [CONCEPT_ART_INDEX.md](../docs/CONCEPT_ART_INDEX.md) и [BESTIARY.md](../docs/BESTIARY.md) переводится в `PUSHED` только после проверки `git ls-tree -r origin/stage1-playable-combat`, а SHA публикации фиксируется в [PROJECT_STATE.md](../docs/progress/PROJECT_STATE.md).

## 8. Команды публикации

```powershell
git status --short                                   # должно быть пусто
powershell -NoProfile -ExecutionPolicy Bypass -File tools/git/check-memory-sync.ps1 -Staged
git push -u origin stage1-playable-combat
git rev-parse HEAD origin/stage1-playable-combat      # SHA должны совпасть
git ls-tree -r origin/stage1-playable-combat -- assets/archives/ assets/references/bosses/ docs/ game/
```

Затем: обновить `PUSHED` по трём осям D3, записать SHA в `PROJECT_STATE.md`, сделать коммит памяти и отправить его тем же автоматическим push-циклом (D14).

## 9. Публикация без предварительного согласования (D14)

Решение владельца от 2026-10-25 отменило требование подтверждать публикацию: этот отчёт — информационный, push не ждёт одобрения. Сохранены запреты на прямой push в `main`, force push, переписывание истории, обход защиты веток и самостоятельный merge в `main`.

## 10. Результат публикации

Заполняется после `push`: удалённый SHA, совпадение с локальным `HEAD`, наличие ZIP и ключевых каталогов в удалённой ветке, способ авторизации.
