<div align="center">

# 🎵 Sonoglyph

**Извлекай музыкальные признаки из аудио — темп, тональность, настроение, спектр и многое другое.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-18%20passed-brightgreen.svg)]()

[English](README.md) · [Русский](README.ru.md)

</div>

---

## Что это?

**Sonoglyph** — Python-библиотека и CLI-утилита, которая анализирует аудиофайлы и извлекает музыкальные признаки: **темп**, **тональность**, **настроение**, **спектральные характеристики**, **энергию** и многое другое. Работает из коробки без ML-зависимостей, опционально подключает нейросетевые бэкенды для повышенной точности.

Применения:

- 🎧 Умные плейлисты по темпу, тональности или настроению
- 📊 Пакетный анализ музыкальной библиотеки (CSV/HTML отчёты)
- 🤖 Встраивание в приложение через REST API
- 🔬 Исследования в области Music Information Retrieval (MIR)

---

## Возможности

| Возможность | Описание |
|---|---|
| 🥁 **Темп / BPM** | Beat tracking с оценкой уверенности |
| 🎼 **Тональность** | Профили Крамхансля, тоника + лад |
| 🎨 **Спектр** | Centroid, rolloff, ZCR, 13 коэффициентов MFCC |
| ⚡ **Энергия** | RMS mean/std, динамический диапазон в дБ |
| 😊 **Настроение** | Valence/Arousal + метки + теги |
| 🎭 **Расширенная карта** | Отличает `melancholic` от `angry` через spectral flatness |
| 💾 **Дисковый кэш** | Ключ по SHA-256, не пересчитывает дважды |
| ⚡ **Параллельный batch** | `ProcessPoolExecutor`, использует все ядра CPU |
| 📤 **Экспорт в CSV** | Плоская таблица, дружелюбна к Excel (utf-8-sig) |
| 🌐 **HTML-отчёт** | Тёмная тема, сортировка, фильтры, модалка со спектрограммой |
| 🚀 **REST API** | FastAPI-сервер для интеграции на любом языке |

---

## Установка

Базовая:

```bash
pip install sonoglyph
```

С HTML-отчётами:

```bash
pip install "sonoglyph[html]"
```

С REST API-сервером:

```bash
pip install "sonoglyph[server]"
```

Всё сразу:

```bash
pip install "sonoglyph[html,server,ml]"
```

Из исходников:

```bash
git clone https://github.com/qrw512/sonoglyph.git
cd sonoglyph
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,html,server]"
```

На Windows активируй venv командой `.venv\Scripts\activate`.

---

## Быстрый старт

### CLI — один файл

```bash
sonoglyph analyze track.mp3
```

Вывод:

```
╭────────────────────────────── Sonoglyph ─────────────────────────────╮
│  track.mp3                                                           │
│  2:34  ·  22050 Hz  ·  1ch  ·  MP3                                   │
╰──────────────────────────────────────────────────────────────────────╯
╭─────── 🥁 Tempo ────────╮           ╭──────── 🎼 Key ─────────╮
│  117.5 BPM              │           │ D# minor                 │
│ 292 beats  ·  conf 0.97 │           │ ♭ minor  ·  conf 0.55    │
╰─────────────────────────╯           ╰──────────────────────────╯
╭────────────────────────── 😊 Mood ───────────────────────────╮
│ MELANCHOLIC   (backend: heuristic)                           │
│   #atmospheric  #dark                                        │
│                                                              │
│ Valence  ██████████░░░░░░░░░░░░░░  0.40                      │
│ Arousal  ███████████████░░░░░░░░░  0.63                      │
│                                                              │
│ Flatness ████░░░░░░░░░░░░  0.0425                            │
╰──────────────────────────────────────────────────────────────╯
╭────── 🎨 Spectral ──────╮      ╭───────── ⚡ Energy ──────────╮
│ Centroid     2260 Hz    │      │ RMS       0.1900 ± 0.1015     │
│ Rolloff      4650 Hz    │      │ Dynamic         69.6 dB       │
│ ZCR           0.0963    │      ╰───────────────────────────────╯
╰─────────────────────────╯
```

### CLI — пакетный анализ папки

```bash
sonoglyph batch ./music/ --pattern "*.mp3" --html report.html --csv library.csv
```

Создаёт: прогресс-бар, сводную таблицу в терминале, `report.html` (тёмная тема, модалка) и `library.csv`.

### Python API

```python
from sonoglyph import analyze, analyze_batch
from sonoglyph.exporters import to_csv, to_html


def main() -> None:
    # Одиночный файл
    result = analyze("PockyBoy.mp3")
    print(f"BPM:   {result.tempo.bpm:.1f}")
    print(f"Key:   {result.key.name}")
    print(f"Mood:  {result.mood.label}")
    print(f"Tags:  {result.mood.tags}")
    print(f"Valence: {result.mood.valence:.2f}")
    print()

    # Пакетный — должен находиться внутри main() в Windows
    results = analyze_batch(
        ["PockyBoy.mp3", "GinsengStrip.mp3", "LongTime.mp3"],
        features=["tempo", "mood"],
    )

    to_csv(results, "library.csv")
    to_html(results, "report.html", include_spectrograms=True)
    print(f"Done: {len(results)} tracks analyzed.")


if __name__ == "__main__":
    main()
```

### REST API

```bash
sonoglyph serve --host 127.0.0.1 --port 8000
```

Затем:

```bash
curl http://127.0.0.1:8000/api/health

curl -X POST http://127.0.0.1:8000/api/analyze-by-path -H "Content-Type: application/json" -d '{"path": "track.mp3", "features": ["tempo", "mood"]}'

curl -X POST http://127.0.0.1:8000/api/analyze -F "file=@track.mp3" -F "features=tempo,mood"
```

Интерактивная документация: <http://127.0.0.1:8000/docs>

---

## Реальные примеры

### Пример 1 — Cloud rap, меланхолия

```json
{
  "tempo": { "bpm": 117.45, "confidence": 0.97, "beat_count": 292 },
  "key":   { "name": "D# minor", "confidence": 0.55 },
  "mood":  {
    "label": "melancholic",
    "valence": 0.40,
    "arousal": 0.63,
    "tags": ["atmospheric", "dark"],
    "spectral_flatness": 0.0425
  }
}
```

**Почему «melancholic», а не «angry»:** в треке энергичный 808-бас и резкие хэты, но также размытая, реверберированная атмосфера. Sonoglyph использует **spectral flatness** (p90-перцентиль), чтобы отделить квадрант «атмосферное + энергичное» от «агрессивного» — классическая ошибка наивных классификаторов valence/arousal.

### Пример 2 — Trap, энергичный

```json
{
  "tempo": { "bpm": 143.55, "confidence": 0.96, "beat_count": 501 },
  "key":   { "name": "E minor", "confidence": 0.59 },
  "mood":  {
    "label": "happy",
    "valence": 0.57,
    "arousal": 0.82,
    "arousal_rhythmic": 0.66,
    "arousal_harmonic": 0.71,
    "tags": ["upbeat"],
    "spectral_flatness": 0.0204
  }
}
```

**Анализ стабильности битов** (из модалки HTML-отчёта):

| Метрика | Значение |
|---|---|
| Средний интервал | 418.0 мс |
| Медианный интервал | 417.9 мс |
| Стандартное отклонение | 33.2 мс |
| CV (стабильность) | 0.0793 |
| BPM из интервалов | 143.52 (совпадает с `bpm` 143.55 ✅) |

### Пример 3 — HTML-отчёт

```bash
sonoglyph batch ./music/ --html report.html
```

Открыть `report.html` в браузере. Возможности:

- Фильтр по имени трека, тональности, тегу
- Сортировка по BPM, настроению, valence, arousal
- Клик по треку → модалка: waveform + маркеры битов, mel-спектрограмма, гистограмма интервалов, таймлайн позиций битов и все статы

---

## Конфигурация

| Переменная | По умолчанию | Описание |
|---|---|---|
| `SONOGLYPH_CACHE_DIR` | `~/.cache/sonoglyph` | Директория кэша |
| `SONOGLYPH_MOOD_BACKEND` | `auto` | `auto` / `heuristic` / `vibenet` |

```bash
export SONOGLYPH_CACHE_DIR=/tmp/sonoglyph-cache
export SONOGLYPH_MOOD_BACKEND=heuristic
```

---

## Структура проекта

```
sonoglyph/
├── src/sonoglyph/
│   ├── analyzers/          # Tempo, key, spectral, energy, mood
│   ├── exporters/          # CSV, HTML
│   ├── server/             # FastAPI
│   ├── api.py              # Публичный API
│   ├── cache.py            # Дисковый кэш
│   ├── cli.py              # CLI на Typer
│   ├── io.py               # Загрузка аудио
│   └── schemas.py          # Pydantic-модели
├── tests/                  # 18 тестов
├── examples/
├── benchmarks/
└── pyproject.toml
```

---

## Лицензия

MIT — см. [LICENSE](LICENSE).

---

## Благодарности

Построено на: [librosa](https://librosa.org/) · [soundfile](https://python-soundfile.readthedocs.io/) · [pydantic](https://docs.pydantic.dev/) · [Typer](https://typer.tiangolo.com/) · [Rich](https://rich.readthedocs.io/) · [FastAPI](https://fastapi.tiangolo.com/) · [uvicorn](https://www.uvicorn.org/) · [matplotlib](https://matplotlib.org/)

Профили Крамхансля-Кесслера — из *Cognitive Foundations of Musical Pitch* (1990).
