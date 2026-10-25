# Этап 1 — технический фундамент Godot

> Память этапа (D12). Обновлено: 2026-10-25. Статус: **`NEEDS_REVIEW`** (собран и проверен, ждёт приёмки владельцем).
> Замечание: фундамент построен **до** утверждения регламента (Этап 0), поэтому его артефакты имеют статус техники, а не арта.

## 1. Название и цель

**Этап 1 — технический фундамент.** Цель: доказать, что на этом ПК реально работают Godot 4.7.2, Pixelorama и пайплайн PNG → игра, и что агент может запускать игру, управлять ею и снимать кадр. Игрового контента этап не создаёт.

## 2. Начальное состояние

- Репозиторий был фактически документальным: ни проекта движка, ни проверенного инструментария, ни пайплайна.
- Установлены: Godot 4.7.2 (WinGet), Pixelorama 1.2.3, Git 2.55.0; система DeepSeek Harness с профилем `desktop`.
- Требовалось: подтвердить версии запуском, поднять Godot MCP, проверить CLI Pixelorama, собрать тестовую сцену и все проверки делать реальными кадрами.

## 3. Выполненные задачи

1. Аудит окружения: фактические пути и версии Godot/Pixelorama/Git/Python.
2. Установка и проверка Godot MCP Server `@tugcantopaloglu/godot-mcp` v3.1.0 (MIT), локальная сборка на встроенном Node DSH; протокол проверен (`initialize` → `tools/list` → `get_godot_version`).
3. Три собственных бандла DSH: `rogalik-env-check`, `rogalik-pixel-pipeline`, `rogalik-dev-preset` (пресет с MCP).
4. Тестовый Godot-проект `game/prototype`: сцена с полом, стенами, препятствием, игроком и камерой.
5. Контроллер игрока (`player.gd`), автолоад скриншота (`capture.gd`), MCP-мост (`mcp_interaction_server.gd`, vendor).
6. Пайплайн пиксель-арта `tools/pixel_pipeline`: сборка `.pxo`, экспорт через Pixelorama CLI, валидация, атлас + JSON, CLI-команды, тесты.
7. Проверка реального запуска: скриншоты, лог коллизии, чтение сцены через MCP, живой кадр из запущенной игры.
8. Документ фактической среды — [ROGALIK_DEV_ENVIRONMENT.md](../ROGALIK_DEV_ENVIRONMENT.md).

## 4. Принятые решения

- Движок — Godot 4.7.2 / GDScript (позже закреплено как D1).
- Pixelorama используется **через CLI**, GUI-режим не автоматизируется.
- MCP-мост слушает только `127.0.0.1:9090`, внешние порты не открываются.
- Спрайт героя на этом этапе — процедурный плейсхолдер, позже помечен `PROXY_TECHNICAL` (D8).
- Пиксельные константы не фиксируются (позже закреплено как D9 — выбор на Этапе 2).

## 5. Созданные и изменённые файлы

- `game/prototype/project.godot`, `scenes/main.tscn`, `scripts/player.gd`, `scripts/capture.gd`, `scripts/mcp_interaction_server.gd`
- `game/prototype/art/sprites/hero_walk.png` (128×32, 4 кадра 32×32) и `.import`
- `game/prototype/art/demo-tool/` (`.pxo`, PNG, атлас, JSON, отчёты)
- `tools/pixel_pipeline/*` (pxo, pixelorama, validate, atlas, cli, examples, tests)
- `tools/reference_import/*`, `tools/setup-godot-mcp.ps1`
- `plugins/rogalik-env-check/*`, `plugins/rogalik-pixel-pipeline/*`, `plugins/rogalik-dev-preset/*`
- `reports/godot-prototype.png`, `reports/godot-runtime-shot.png`, `reports/godot-mcp-runtime.png`
- `docs/ROGALIK_DEV_ENVIRONMENT.md`, `docs/tasks/DSH_PLUGIN_BOOTSTRAP.md`

## 6. Локальные Git-коммиты

| Коммит | Описание |
|---|---|
`3b46b44` | рабочая среда: Godot/Pixelorama/MCP-пресет и два локальных плагина |
`04a91f1` | документирование живого MCP-процесса |
`c9e5626` | MCP runtime-мост и проверка управления живой игрой |
`61d1bda` | сохранение проверенной работы по референсам перед этапом 1
`D13` | организационная задача: GitHub как общий репозиторий, правила публикации, `.gitignore`/`.gitattributes`, `tools/git/check-memory-sync.ps1`, отчёт о первой публикации (SHA — `git log -1`) |

Push не выполнялся: первый push ожидает подтверждения владельцем отчёта о составе публикации (D13).

## 7. Результаты технических проверок

| Проверка | Результат |
|---|---|
Версии инструментов | Godot 4.7.2, Pixelorama 1.2.3, Git 2.55.0, Python 3.12.14 (`rogalik_env_check`) |
Импорт проекта | `--headless --import` без ошибок |
Запуск и коллизия | лог `PLAYER_READY` → `PLAYER_POS x=186` → `PLAYER_BLOCKED x=269` |
Реальный кадр игры | 960×540, оконный режим ([reports/godot-mcp-runtime.png](../../reports/godot-mcp-runtime.png)) |
MCP | 157 инструментов; `get_godot_version` → 4.7.2; `read_scene` отдаёт дерево `main.tscn` |
Спрайт-лист | `rogalik_pixel_pipeline check` → PASS (4 кадра, 8 цветов, прозрачность 78.6 %) |
Тесты пайплайна | 12 тестов, 1 пропускается без `ROGALIK_SLOW_TESTS=1` (по отчёту среды; в сессии Этапа 0 не перезапускались) |

## 8. Известные ошибки и ограничения

1. Pixelorama CLI требует `--quit`, иначе headless-процесс висит.
2. `-o/--output` в Pixelorama CLI игнорируется — имя результата берётся из `.pxo`; обёртка сама переименовывает.
3. Headless-экспорт Pixelorama может завершиться access violation **после** записи PNG — успех определяется файлами, а не кодом выхода.
4. Нужен редирект `APPDATA` для `user://` у Pixelorama и Godot в ограниченной среде.
5. Скриншот возможен только в оконном режиме: `--headless` даёт dummy-рендерер.
6. `run_project` копирует мост в корень проекта — дубликат добавлен в `.gitignore`.
7. `mcp__godot__read_scene` принимает путь без `res://`.
8. После `pixel_pipeline demo` нужен реимпорт Godot (`--headless --import`).
9. В вендорном `mcp_interaction_server.gd` есть 10 предупреждений компилятора; на работу не влияют, файл сторонний.
10. `git` в песочнице иногда требует `-c http.sslBackend=openssl`.

## 9. Незавершённая работа

- **Приёмка этапа владельцем** — не выполнена (это единственная причина статуса `NEEDS_REVIEW`).
- Не проверялось в последней сессии: `run_project` + `game_screenshot` end-to-end; Pixelorama GUI.
- Заведомо за пределами этапа: пиксельные константы (Этап 2), арт героя и врагов (Этапы 3–4), боевая система (Этап 5).

## 10. Итоговый статус

**`NEEDS_REVIEW`** — все заявленные проверки выполнены, технический результат воспроизводим; ждёт решения владельца `ACCEPTED` / `FIX_REQUIRED`.

## 11. Что должен знать агент в следующем чате

- Как запускать: `--headless --import` → `--headless --fixed-fps 60 --quit-after 400 -- --auto=1` (движение/коллизия) → оконный запуск с `--shot=… --shot-frames=…` для кадра.
- Пайплайн: `$env:PYTHONPATH="tools"; python -m pixel_pipeline.cli check <png> --frame 32 --frames 4`; тесты — `python -m unittest discover -s tools/pixel_pipeline/tests -v`.
- **Не перезапускать** уже подтверждённые проверки из §7 без технической необходимости; доказательства переиспользуются.
- В `game/prototype` **нет игрового контента**: спрайт — `PROXY_TECHNICAL`, сцена — техническая комната.
- Этап 2 не начат; начинать его можно только после `ACCEPTED` от владельца и в новом чате (D12).
- **Публикация (D13):** рабочая ветка — `stage1-playable-combat`; первый push — после подтверждения [reports/d13_publication_report.md](../../reports/d13_publication_report.md). Перед push: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/git/check-memory-sync.ps1 -Staged`. После push проверить `git rev-parse origin/stage1-playable-combat` и только затем ставить `PUSHED` в [CONCEPT_ART_INDEX.md](../CONCEPT_ART_INDEX.md).
