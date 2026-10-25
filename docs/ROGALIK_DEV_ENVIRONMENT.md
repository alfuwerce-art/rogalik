# Rogalik — рабочая среда разработки (отчёт и инструкция)

> Статус: **инструменты установлены, проверены и использованы**. Дата: 2026-10-25.
> Ветки: проверка выполнялась в `rogalik-dev`; текущая работа идёт в `stage1-playable-combat`. Базовый документ-задание: [tasks/DSH_PLUGIN_BOOTSTRAP.md](tasks/DSH_PLUGIN_BOOTSTRAP.md).
> Этот документ описывает фактическое состояние, а не план. Всё, что не проверено запуском, помечено `NOT_VERIFIED`.

## 1. Итог одной таблицей

| Компонент | Версия / путь | Статус |
|---|---|---|
| Godot Engine (Standard, GDScript) | 4.7.2.stable.official.ed1daf0bf, WinGet | PASS |
| Pixelorama | 1.2.3-stable, `%APPDATA%\Orama Interactive\Pixelorama\Pixelorama.exe` | PASS (CLI-экспорт проверен) |
| Git | 2.55.0.windows.1 | PASS |
| Node.js (встроенный в DSH) | 24.21.0 через `DeepSeek Harness.exe` с `ELECTRON_RUN_AS_NODE=1` | PASS |
| pnpm (встроенный в DSH) | 11.28.5 | PASS |
| MCP-клиент DSH | `@deepseek-ai/dsh-mcp-client`, входит в поставку DSH | PASS (пресет смонтирован) |
| Godot MCP Server | `@tugcantopaloglu/godot-mcp` v3.1.0, MIT, локальная сборка | PASS (157 инструментов, `get_godot_version` → 4.7.2) |
| `rogalik-env-check` | собственный Cordis-плагин, инструмент `rogalik_env_check` | PASS (реальный вызов) |
| `rogalik-pixel-pipeline` | собственный Cordis-плагин, инструмент `rogalik_pixel_pipeline` | PASS (реальный вызов) |
| Тестовая сцена Godot | `game/prototype`, герой + пол + препятствие | PASS (запуск, коллизия, скриншот) |
| `mcp__godot__*` в живой сессии | только в пресете `rogalik-dev` | PASS 2026-10-25: `get_godot_version` → 4.7.2, `read_scene` читает `main.tscn`. `run_project`/`game_screenshot` в этой проверке не запускались |

Скриншот реально запущенной игры: [reports/godot-prototype.png](../reports/godot-prototype.png).

## 2. Аудит окружения

Точные команды и результаты:

```powershell
# Godot (консольная сборка — та, что отвечает на stdout)
& "C:\Users\bow\AppData\Local\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe\Godot_v4.7.2-stable_win64_console.exe" --headless --version
# 4.7.2.stable.official.ed1daf0bf

# Pixelorama: команда не в PATH, EXE лежит в профиле пользователя
& "$env:APPDATA\Orama Interactive\Pixelorama\Pixelorama.exe" --headless --quit -- --version
# v1.2.3-stable

# Git
git --version            # 2.55.0.windows.1
```

Инструмент `rogalik_env_check` выполняет эти же проверки сам и возвращает JSON
(версии берутся запуском бинарников, а не из конфигов).

### Особенности, найденные на практике

1. **Pixelorama CLI требует `--quit`.** Без него headless-процесс висит после
   выполнения команды. Рабочая форма:
   `Pixelorama.exe --headless --quit -- -e <project.pxo>`.
2. **Pixelorama пишет в `user://`** (логи, бэкапы, конфиг) — на Windows это
   `%APPDATA%`. В ограниченной песочнице это падало с `Could not create
   directory: 'user://backups'`; обёртка `tools/pixel_pipeline/pixelorama.py`
   перенаправляет `APPDATA` во временный каталог. Так же поступает
   `rogalik_env_check`.
3. **`-o/--output` в Pixelorama CLI фактически игнорируется**: `set_output`
   применяется к проекту, захваченному до загрузки файла, поэтому имя результата
   берётся из имени `.pxo`. Обёртка копирует проект в staging-каталог и сама
   переименовывает результат.
4. **Headless-экспорт Pixelorama может завершиться с access violation уже после
   записи PNG.** Поэтому успех определяется наличием файлов, а не кодом выхода.
5. **`APPDATA`-редирект нужен и Godot** для `user://`; иначе редактор не может
   создать каталог данных.
6. **Git в Windows-песочнице** иногда не может взять сертификат через schannel:
   `SEC_E_NO_CREDENTIALS`. Обход без изменения глобального конфига:
   `git -c http.sslBackend=openssl <command>`.

## 3. Установленные компоненты DeepSeek Harness

Все три бандла установлены штатным `plugin_manager` (install_bundle) и включены.
Пресеты других проектов и встроенные плагины не изменялись — только добавлены
новые строки.

### 3.1 `@local/rogalik-env-check` — профиль

- Инструмент: `rogalik_env_check` (`deep`, `workspace`).
- Только чтение: версии Godot/Pixelorama/Git/Python, наличие репозитория,
  тестового проекта, пайплайна и каталога плагинов. Секреты и `.env` не читает.
- Схема параметров: корневой `type: "object"` (см. §7 — исправленная ошибка).

### 3.2 `@local/rogalik-pixel-pipeline` — профиль

- Инструмент: `rogalik_pixel_pipeline` (`action`: `check` | `build` | `export` |
  `atlas` | `demo`, плюс параметры конкретного действия).
- Вызывает Python CLI `tools/pixel_pipeline/cli.py` (Pillow из комплекта DSH) и
  настоящий бинарник Pixelorama. Возвращает `PASS/FAIL`, метрики и пути артефактов.

### 3.3 `@local/rogalik-dev-preset` — пресет

- Добавляет пресет **`rogalik-dev`** (персона разработчика + инструменты + MCP).
- Внутри пресета смонтирован `@deepseek-ai/dsh-mcp-client` с сервером `godot`.
- Тяжёлые MCP-инструменты (157) доступны **только** в сессиях этого пресета,
  поэтому другие проекты профиля не получают лишний контекст.

Откат любого бандла: `plugin_manager` → `remove_bundle` с именем пакета.

## 4. Godot MCP Server

- Источник: <https://github.com/tugcantopaloglu/godot-mcp>, тег **v3.1.0**, лицензия MIT.
- Зависимости: Node.js ≥ 18 и сам Godot 4.4+; .NET нужен только для C#-режима
  (не используется).
- Системный Node.js **не устанавливался**: сервер работает на Node 24.21.0,
  встроенном в DeepSeek Harness (`ELECTRON_RUN_AS_NODE=1`), сборка — встроенным pnpm.
- Сборка воспроизводится скриптом [tools/setup-godot-mcp.ps1](../tools/setup-godot-mcp.ps1)
  (клон, `pnpm install --ignore-scripts --node-linker=hoisted`, `tsc`, копирование GDScript).
- Проверка протокола: [tools/godot-mcp/probe-mcp.ps1](../tools/godot-mcp/probe-mcp.ps1)
  (initialize → tools/list → `get_godot_version` → опционально `read_scene`).

Фактический прогон:

```text
PASS initialize: godot-mcp 0.1.0 protocol 2024-11-05
PASS tools/list: 157 tools (get_godot_version present: True)
PASS get_godot_version: 4.7.2.stable.official.ed1daf0bf
PASS read_scene: { ... узлы и свойства res://scenes/main.tscn ... }
[SERVER] Using Godot at: ...\Godot_v4.7.2-stable_win64_console.exe
```

> Запускать `probe-mcp.ps1` нужно вне ограниченной песочницы: сервер запускает
> Godot дочерним процессом с pipe, а такой `spawn` в песочнице даёт `EPERM`.

## 5. Пресет `rogalik-dev`

1. В DeepSeek Harness создайте новую сессию и выберите пресет **Rogalik Dev**
   (список пресетов, порядок 200).
2. В сессии должны появиться инструменты `mcp__godot__*` (157 штук) рядом с
   `rogalik_env_check` и `rogalik_pixel_pipeline`.
3. Проверка в один шаг: попросить агента вызвать `mcp__godot__get_godot_version`,
   затем `mcp__godot__read_scene` для `game/prototype/scenes/main.tscn`
   (**`scenePath` — путь относительно проекта, без префикса `res://`**: рабочая форма
   `scenePath: "scenes/main.tscn"`; вариант `res://scenes/main.tscn` возвращает
   `Scene file does not exist` — проверено 2026-10-25),
   затем `mcp__godot__run_project` и `mcp__godot__game_screenshot`.

Регистрация проверена 2026-10-25 после переноса папки: строка
`include:preset-rogalik-dev` присутствует в живой композиции Host ровно один раз
(`cordis_inspect_query` → Host `Config.listConfigs`). Дубликата нет, другие
пресеты не затронуты — в списке ровно 6 записей: `standard`, `ptc`, `minimal`,
`cordis`, `ai-freelancer-v1`, `rogalik-dev`. Все 24 пакета плагинов пресета
резолвятся в поставке DSH 0.2.1-rc.3 (сверено с каталогом
`@deepseek-ai/dsh-agent-preset/skills/cordis-composition-reference/references/packages.md`).

Что подтверждено фактически:

- пресет смонтирован и проходит валидацию схемы;
- Host запускает MCP-сервер из конфигурации пресета: процесс
  `DeepSeek Harness.exe --expose-internals C:\Users\bow\Desktop\Rogalik\tools\godot-mcp\build\index.js`
  — путь берётся из `cordis.patch.yml` пресета, а не из профиля;
- протокол сервера проверен напрямую: 157 инструментов, `get_godot_version` →
  4.7.2, `read_scene` читает `game/prototype/scenes/main.tscn`,
  `run_project` + `game_screenshot` дают реальный кадр 960×540 (см. §11.5).

Шаг вызова `mcp__godot__*` из чата **проверен 2026-10-25** в рабочей сессии:
`get_godot_version` вернул 4.7.2, `read_scene` прочитал
`game/prototype/scenes/main.tscn` (путь без `res://`). Инструменты доступны
только в сессиях пресета `rogalik-dev`; в других сессиях профиля их нет — 157
MCP-инструментов намеренно не попадают в контекст других проектов. Запуск
GUI-игры (`run_project` + `game_screenshot`) в этой проверке не выполнялся,
чтобы не смешивать проверку правил с разработкой.

## 6. Пиксельный пайплайн

Состав: `tools/pixel_pipeline/`

| Файл | Назначение |
|---|---|
| `pxo.py` | сборка `.pxo` (Pixelorama 1.2.x, `pxo_version 7`) из RGBA-кадров |
| `pixelorama.py` | обёртка CLI: экспорт кадров или спрайт-листа, APPDATA-редирект |
| `validate.py` | проверки PNG, спрайт-листа, тайлсета; отчёт `PASS/FAIL` |
| `atlas.py` | упаковка листа в атлас + JSON-метаданные для Godot |
| `cli.py` | команды `check` / `build` / `export` / `atlas` / `demo` |
| `examples/make_test_sprite.py` | детерминированный плейсхолдер-спрайт (палитра из гайда) |
| `tests/` | 12 тестов (`unittest`), включая опциональный интеграционный |

Формат `.pxo`, восстановленный по файлу Pixelorama и исходникам v1.2.3:
ZIP с `mimetype` (`application/x-pixelorama`), `data.json`, `preview.png` и
`image_data/frames/<n>/layer_<i>` (сырые RGBA-байты). Pixelorama открывает такой
проект и экспортирует его своим CLI — то есть арт действительно проходит через
редактор, а не подменяется записью PNG.

Команды:

```powershell
$env:PYTHONPATH = "tools"
python -m pixel_pipeline.cli demo --out game/prototype/art/demo-tool
python -m pixel_pipeline.cli check game/prototype/art/sprites/hero_walk.png --frame 32 --frames 4
python -m pixel_pipeline.cli build out/hero.pxo --sheet art/hero.png --frame 32 --tag walk
python -m pixel_pipeline.cli export out/hero.pxo --out art/export --sheet
python -m pixel_pipeline.cli atlas art/export/hero.png --frame 32 --columns 2 --out art/atlas
```

Проверки `check`: существование файла, декодирование, прозрачность, число цветов,
делимость на кадры, ожидаемое число кадров, отсутствие пустых кадров, общая
нижняя граница кадров (отсутствие вертикального дрожания), а для тайлсета —
бесшовность краёв.

Тесты:

```powershell
$env:PYTHONPATH = "tools"
python -m unittest discover -s tools/pixel_pipeline/tests -v
# Ran 12 tests ... OK (skipped=1)  — интеграционный тест включается ROGALIK_SLOW_TESTS=1
```

## 7. Исправленная ошибка регистрации инструмента

При первой установке `rogalik_env_check` ломал запросы к модели:

```text
Invalid schema for function 'rogalik_env_check':
schema must be a JSON Schema of 'type: "object"', got 'type: null'
```

Причина: в `ctx.tools.register()` поле `parameters` было картой свойств без
корневого `type: "object"`. `defineTool()` из `@deepseek-ai/dsh-tools` такую
форму нормализует, а прямая регистрация — нет: описание уходило модели как есть.

Исправление (оба инструмента):

```js
parameters: {
  type: 'object',
  additionalProperties: false,
  required: ['action'],            // только у pixel_pipeline
  properties: { /* ... */ },
}
```

Дополнительно устранена вторая проблема, найденная при первом же вызове:
`value is not lossless JSON`. Сообщения внешних программ содержат байты консоли
Windows, которые превращаются в одиночные суррогаты и ломают строгий JSON.
Оба плагина прогоняют результат через `toJsonValue()` (JSON round-trip +
`toWellFormed()`).

Локальные проверки перед включением:

```powershell
node plugins/_schema-check.mjs   # корневой object, корректные типы, required, output.schema
node plugins/_selftest.mjs       # регистрация + lossless-JSON + реальные вызовы
```

После исправления инструмент вызван в живой сессии и вернул `PASS` с версиями
Godot 4.7.2, Pixelorama 1.2.3, Git 2.55.0.

## 8. Тестовый Godot-проект

`game/prototype/` — техническая сцена, **не** утверждённый уровень:

- `scenes/main.tscn` — пол, стены, препятствие, `CharacterBody2D` с `Sprite2D`
  (спрайт-лист из Pixelorama, 4 кадра), `Camera2D`, подсказка;
- `scripts/player.gd` — движение на WASD/стрелках без InputMap, анимация кадров,
  режим `--auto=<dir>` для автоматического прогона;
- `scripts/capture.gd` (autoload) — скриншот по `--shot=<path> --shot-frames=N`.

Запуск:

```powershell
$env:APPDATA = "$PWD\.cache\godot-appdata"   # чтобы user:// был записываемым
$env:APPDATA = "$PWD\..\.cache\godot-appdata"
& $godot --headless --path game\prototype --fixed-fps 60 --quit-after 400 -- --auto=1
# PLAYER_BLOCKED x=269.0 y=160.0   ← коллизия с препятствием (левый край 276, полуширина 7)

& $godot_gui --path game\prototype --log-file reports\godot-run.log --resolution 960x540 `
  --fixed-fps 60 --quit-after 1200 -- --shot="$PWD\reports\godot-prototype.png" --shot-frames=260
# SHOT_SAVED ... err=0 size=960x540
```

Почему скриншот снимается только в оконном режиме: в `--headless` используется
dummy-рендерер, изображения нет. Скриншот сделан из реально запущенной игры.

### Runtime-мост MCP

Для инструментов `mcp__godot__run_project` / `game_screenshot` / `game_*` в проект
добавлен автолоад `McpInteractionServer`
(`game/prototype/scripts/mcp_interaction_server.gd`, MIT, из поставки godot-mcp).
Он слушает **только** `127.0.0.1:9090`, внешние порты не открываются.

Проверено на запущенной игре (оконный режим):

```text
McpInteractionServer: Listening on 127.0.0.1:9090
McpInteractionServer: Client connected
get_scene_tree -> {"success":true,"tree":{"children":[Capture, McpInteractionServer,
                  Floor, Ground, Walls, Obstacle, Player, Camera2D, HUD]...}}
screenshot -> {"success":true,"width":960,"height":540,"data":"<base64 PNG>"}
```

Кадр, снятый по этому протоколу: [reports/godot-runtime-shot.png](../reports/godot-runtime-shot.png)
(декодирован из ответа `screenshot`).

После чистки `.godot/` (каталог импорта в Git не хранится) нужно один раз выполнить
`godot --headless --path game/prototype --import`, иначе сцена не найдёт
`res://art/sprites/hero_walk.png`.

## 9. Что не подтверждено

- `mcp__godot__*` в живой сессии пресета `rogalik-dev` — см. §5 (нужна сессия с пресетом).
- Художественное качество спрайта: это процедурный плейсхолдер 32×32, а не
  финальный арт. Автотесты подтверждают геометрию и прозрачность, не «красоту».
- Поведение Pixelorama GUI-режима (использовался только CLI).
- `.pxo`-формат проверен на Pixelorama 1.2.3; для другой версии возможны отличия
  (`pxo_version`).

## 10. Воспроизведение с нуля

```powershell
git clone https://github.com/alfuwerce-art/rogalik.git
cd rogalik
git checkout rogalik-dev

# 1. Godot MCP Server (без системного Node.js)
powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup-godot-mcp.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\godot-mcp\probe-mcp.ps1

# 2. Плагины и пресет — только через штатный Plugin Manager:
#    install_bundle для plugins\rogalik-env-check, plugins\rogalik-pixel-pipeline,
#    plugins\rogalik-dev-preset

# 3. Пайплайн и тесты
$env:PYTHONPATH = "tools"
python -m pixel_pipeline.cli demo --out game/prototype/art/demo-tool
python -m unittest discover -s tools/pixel_pipeline/tests -v

# 4. Тестовая сцена
godot --headless --path game/prototype --import
godot --headless --path game/prototype --fixed-fps 60 --quit-after 400 -- --auto=1
```

## 11. Повторная проверка после переноса папки (2026-10-25)

Проект перенесён из `C:\Users\bow\Desktop\AI-Freelancer\rogalik` в
`C:\Users\bow\Desktop\Rogalik`. Ниже — что реально проверено уже на новом месте.

### 11.1 Устаревшие абсолютные пути

В истории (`c9e5626` и раньше) конфигурации указывали на старый путь. В рабочем
дереве они уже были заменены; при повторной проверке ни одного вхождения
`AI-Freelancer` в файлах проекта не осталось.

| Файл | Что ссылалось на старый путь |
|---|---|
| `plugins/rogalik-env-check/cordis.patch.yml` | `config.workspace` |
| `plugins/rogalik-pixel-pipeline/cordis.patch.yml` | `config.workspace` |
| `plugins/rogalik-env-check/index.js` | `DEFAULT_WORKSPACE` |
| `plugins/rogalik-pixel-pipeline/index.js` | `DEFAULT_WORKSPACE` |
| `plugins/rogalik-dev-preset/cordis.patch.yml` | `mcp-godot.args[1]`, `cwd`, `GODOT_MCP_ALLOWED_DIRS` |

Отдельно исправлены артефакты прошлого прогона пайплайна
(`game/prototype/art/demo-tool/demo.json` и `report.json`): они сохраняли
абсолютные пути старой папки. Пересобраны вызовом `rogalik_pixel_pipeline` с
`action: demo`; теперь там пути `C:\Users\bow\Desktop\Rogalik\...`.

### 11.2 Переустановка бандлов

После переноса в профиле `desktop` не осталось ни одного бандла Rogalik: в
`package.json` были только `dsh-base`, `dsh-web-app` и browser-use, а строки
`rogalik-*` в композиции отсутствовали. Все три бандла восстановлены штатным
`plugin_manager` → `install_bundle` по локальному пути
(`plugins\rogalik-env-check`, `plugins\rogalik-pixel-pipeline`,
`plugins\rogalik-dev-preset`). Профиль вручную не редактировался, дубликатов строк
нет: в `dsh.profile.bundles` каждый бандл встречается один раз.

### 11.3 Проверка схем инструментов

```powershell
node plugins/_schema-check.mjs   # PASS rogalik_env_check: root object, 2 properties
                                 # PASS rogalik_pixel_pipeline: root object, 15 properties
node plugins/_selftest.mjs       # env-check PASS, pipeline PASS (4 кадра 32x32)
```

`node` здесь — встроенный в DSH 24.21.0
(`.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`).

### 11.4 Реальные вызовы инструментов в живой сессии

| Инструмент | Аргументы | Результат |
|---|---|---|
| `rogalik_env_check` | `deep: true` | PASS: Godot 4.7.2, Pixelorama v1.2.3-stable, Git 2.55.0, Python 3.12.14, все 6 проверок workspace `ok` |
| `rogalik_pixel_pipeline` | `action: check`, `frame: 32`, `frames: 4` | PASS: 128×32 RGBA, 4 кадра 32×32, 8 цветов, прозрачность 78.6%, все 8 проверок PASS |
| `rogalik_pixel_pipeline` | `action: demo` | PASS: пересобран `.pxo`, экспорт через Pixelorama CLI, атлас + JSON |

### 11.5 Godot MCP: протокол и живая игра

Добавлены два диагностических скрипта рядом с существующим `probe-mcp.ps1`:

- `tools/godot-mcp/probe-schemas.ps1` — печатает схемы выбранных инструментов;
- `tools/godot-mcp/probe-runtime.ps1` — полный игровой цикл по MCP
  (`run_project` → `game_screenshot` → `get_debug_output` → `stop_project`).

> Каталог `tools/godot-mcp/` целиком в `.gitignore`: это локальный клон
> стороннего сервера, который пересоздаётся из `tools/setup-godot-mcp.ps1`.
> Все три probe-скрипта лежат там же и, как и раньше, не попадают в коммит.

Фактический прогон:

```text
PASS initialize: godot-mcp 0.1.0 protocol 2024-11-05
PASS tools/list: 157 tools
PASS get_godot_version: 4.7.2.stable.official.ed1daf0bf
PASS read_scene: дерево game/prototype/scenes/main.tscn (Floor, Ground, Walls, Obstacle, Player, Camera2D, HUD)

PASS run_project: Godot project started in debug mode
PASS game_screenshot: Screenshot captured: 960x540 after 3 attempt(s)
PASS screenshot file: reports/godot-mcp-runtime.png (14140 bytes)
PASS get_debug_output: 5 stdout lines, 10 stderr lines
PASS stop_project
```

Схемы четырёх инструментов (из `tools/list`):

| Инструмент | Схема входа |
|---|---|
| `get_godot_version` | `{"type":"object","properties":{},"required":[]}` |
| `read_scene` | `projectPath`, `scenePath` (оба required) |
| `run_project` | `projectPath` (required), `scene` |
| `game_screenshot` | `{"type":"object","properties":{},"required":[]}` |

Лог игры: `Godot Engine v4.7.2 ... OpenGL API 3.3.0 NVIDIA 610.47`,
`McpInteractionServer: Listening on 127.0.0.1:9090`, `PLAYER_READY`,
`McpInteractionServer: Client connected`. Кадр:
[reports/godot-mcp-runtime.png](../reports/godot-mcp-runtime.png).

Ошибок нет, но в `stderr` есть 10 предупреждений компилятора GDScript из
вендорного `scripts/mcp_interaction_server.gd` (затенение `name` в цикле на
строках 2566/2573/2579 и integer вместо enum на 2945/3102). Файл сторонний
(из godot-mcp v3.1.0), править его без пересборки не стоит; на работу моста они
не влияют.

### 11.6 Запуск тестовой сцены без MCP

```powershell
godot --headless --path game/prototype --import          # реимпорт после demoTool
godot --headless --path game/prototype --fixed-fps 60 --quit-after 400 -- --auto=1
# PLAYER_READY pos=96.0,160.0 / PLAYER_POS x=186.0 / PLAYER_BLOCKED x=269.0
# далее кадры анимации 3 и остановка: коллизия с препятствием работает
```

### 11.7 Мелкие особенности, найденные при этой проверке

1. **`pwsh` отсутствует в PATH** — оболочка инструмента работает на Windows
   PowerShell 5.1. Скрипты запускать так:
   `powershell -NoProfile -ExecutionPolicy Bypass -File <script>`.
2. **`run_project` кладёт копию моста в корень проекта.** `injectInteractionServer`
   видит автолоад в `project.godot` и больше ничего не меняет, но проверяет
   наличие скрипта по пути `game/prototype/mcp_interaction_server.gd`, а не по
   фактическому `res://scripts/...`. В результате при каждом запуске появляется
   неиспользуемый дубликат 193 КБ. Он добавлен в `.gitignore`
   (`game/**/mcp_interaction_server.gd`) и удаляется вручную; ссылка автолоада
   по-прежнему указывает на `scripts/`.
3. **После `rogalik_pixel_pipeline demo` нужен реимпорт** Godot
   (`--headless --import`), иначе изменённые PNG подхватятся со старым кэшем.
4. **Лишний процесс MCP-сервера.** Установка бандла пресета оставляет в дереве
   процессов Host дочерний `DeepSeek Harness.exe --expose-internals
   ...\tools\godot-mcp\build\index.js`, который ждёт stdio и портов не держит.
   Он безвреден и не конфликтует с сессиями: каждая сессия с пресетом поднимает
   свой экземпляр.
