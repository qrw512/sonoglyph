# Примеры

Запускаемые примеры, показывающие, как пользоваться Sonoglyph —
от анализа одной строкой до сборки плейлистов по настроению и работы
с REST API.

[English](README.md) · [Русский](README.ru.md)

---

## Содержание

| № | Файл | Что показывает |
|---|---|---|
| 01 | [`01_basic_library.py`](01_basic_library.py) | Анализ одного трека через Python API |
| 02 | [`02_choose_features.py`](02_choose_features.py) | Запуск только нужных анализаторов (быстрее) |
| 03 | [`03_batch_and_export.py`](03_batch_and_export.py) | Пакетный анализ папки, экспорт в CSV + HTML |
| 04 | [`04_mood_deep_dive.py`](04_mood_deep_dive.py) | Детальный разбор valence / arousal / тегов |
| 05 | [`05_playlist_builder.py`](05_playlist_builder.py) | Сборка `.m3u` плейлистов по настроению |
| 06 | [`06_custom_analyzer.py`](06_custom_analyzer.py) | Свой собственный анализатор |
| 07 | [`07_server_client.py`](07_server_client.py) | Обращение к REST API из Python |
| — | [`basic_usage.py`](basic_usage.py) | Минимальный HTTP-клиент |

---

## Требования

Установи Sonoglyph с extras, которые используют примеры:

```bash
pip install "sonoglyph[html,server]"
```

- `[html]` — подтягивает `matplotlib` для спектрограммы в HTML-отчёте
- `[server]` — подтягивает `fastapi` + `uvicorn` для REST-примеров

---

## Запуск

Большинство примеров ожидают `.mp3`-файл в этой папке. Возьми любой
свой трек, положи его в `examples/` и запусти:

```bash
python examples/01_basic_library.py my_track.mp3
```

Примеры `03` и `05` сканируют папку по `*.mp3` и обрабатывают
всё, что найдут:

```bash
python examples/03_batch_and_export.py
python examples/05_playlist_builder.py
```

Для `07_server_client.py` и `basic_usage.py` сначала запусти сервер
в отдельном терминале:

```bash
sonoglyph serve
```

Затем во втором терминале:

```bash
python examples/07_server_client.py
```

---

## Что показывает каждый пример

### `01_basic_library.py` — первое знакомство

Самый простой вариант: `analyze(path)` возвращает типизированный
`AnalysisResult` с полями `.tempo`, `.key`, `.spectral`, `.energy`
и `.mood`. Показывает, как читать каждое из них.

### `02_choose_features.py` — выборочный анализ

Полный анализ запускает все анализаторы. Для скорости запрашивай
только то, что нужно:

```python
analyze(path, features=["tempo"])                 # ~2 сек
analyze(path, features=["mood"])                  # ~5 сек
analyze(path, features=["tempo", "key", "mood"])  # что-то среднее
```

### `03_batch_and_export.py` — вся библиотека

Параллельный анализ всех треков в папке и экспорт в:

- `library.csv` — плоская таблица, открывается в Excel / pandas
- `report.html` — интерактивный отчёт с тёмной темой и модалкой на каждый трек

### `04_mood_deep_dive.py` — эмоциональная карта

Объясняет модель настроения: valence (грусть ↔ радость),
arousal (спокойствие ↔ энергия), split arousal (ритмический vs
гармонический) и теги (`atmospheric`, `dark` и др.).

### `05_playlist_builder.py` — практический сценарий

Классифицирует каждый трек по настроению и пишет по одному `.m3u`
плейлисту на каждую категорию: `01_happy.m3u`, `03_melancholic.m3u` и т. д.
Открываются в любом плеере (VLC, foobar2000, MusicBee).

### `06_custom_analyzer.py` — расширяемость

Показывает, как унаследоваться от `BaseAnalyzer` и реализовать свой
извлекатель признаков. В примере строим `LoudnessAnalyzer`, который
возвращает приблизительную громкость в dBFS.

Чтобы подключить свой анализатор к `analyze()`, зарегистрируй его
в `src/sonoglyph/analyzers/__init__.py`.

### `07_server_client.py` — REST-интеграция

Демонстрирует все три основных эндпоинта:

- `GET  /api/health`           — проверка версии
- `POST /api/analyze-by-path`  — анализ файла по серверному пути
- `POST /api/analyze`          — загрузка + анализ одним запросом
- `GET  /api/features`         — список доступных анализаторов

---

## Решение проблем

**`File not found: ...`** — проверь путь. Большинство примеров по умолчанию
берут `ginseng_strip.mp3`; замени на трек, который у тебя реально есть.

**`httpx.ReadTimeout`** — анализ полного трека на CPU занимает 5–10 секунд.
В примерах уже стоит таймаут 60 секунд, но если твоя машина медленная —
увеличь ещё.

**`Cannot connect to http://127.0.0.1:8000`** — сервер не запущен.
Открой второй терминал и выполни `sonoglyph serve`.

**`ModuleNotFoundError: matplotlib`** — установи extras:
`pip install "sonoglyph[html]"`.

---

## Добавить свой пример

Если ты сделал что-то интересное с Sonoglyph — будем рады включить
это в проект. Открывай PR, который добавляет `examples/NN_твоя_идея.py`
и одну строчку в таблицу выше. Пример должен быть самодостаточным —
без хардкода путей и внешних сервисов.
