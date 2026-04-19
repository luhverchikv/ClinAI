# ClinAI

**RAG-пайплайн для семантического поиска по клиническим протоколам лечения**

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Pipeline](https://img.shields.io/badge/Pipeline-Ingestion→Chunking→Embeddings→VectorDB-orange.svg)

## Описание

ClinAI — это инструмент для автоматической индексации и семантического поиска медицинских клинических протоколов. Система использует RAG-подход (Retrieval-Augmented Generation) для создания векторной базы данных, позволяющей находить релевантные протоколы по естественным запросам.

### Возможности

- **Автоматическая обработка протоколов** — загрузка и валидация Markdown файлов с YAML-метаданными
- **Интеллектуальный чанкинг** — разбиение протоколов по секциям и подразделам
- **Многомодельные эмбеддинги** — выбор между легковесными и высококачественными моделями
- **ICD-10 классификация** — индексация по кодам Международной классификации болезней
- **ChromaDB** — быстрая и масштабируемая векторная база данных

## Архитектура пайплайна

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingestion     │───▶│    Chunking     │───▶│   Embeddings    │───▶│    VectorDB     │
│                 │    │                 │    │                 │    │   (ChromaDB)    │
│  YAML + Markdown│    │  По секциям ### │    │  Sentence-Trans. │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │                      │
    Валидация             Chunk ID + ICD-10       3 модели на выбор         Поиск
    Метаданные            Метаданные               CPU/GPU               similarity_search()
```

## Установка

### Требования

- Python 3.9+
- pip или poetry

### Из исходников

```bash
# Клонирование репозитория
git clone https://github.com/luhverchikv/ClinAI.git
cd ClinAI

# Установка зависимостей
pip install -e .

# Или через poetry
poetry install
```

### Минимальные зависимости

```bash
pip install pyyaml python-frontmatter pydantic tqdm
pip install sentence-transformers chromadb
```

## Быстрый старт

### 1. Подготовка протоколов

Создайте Markdown файл в папке `clinical_protocols/` с YAML-метаданными:

```markdown
---
icd10_code: "I47.1"
diagnosis: "Наджелудочковая тахикардия"
tags:
  - кардиология
  - аритмия
---

## Диагностика

### Обязательные исследования
- ЭКГ в 12 отведениях
- Холтеровское мониторирование

## Лечение

### Купирование приступа
1. Вагусные пробы
2. Верапамил 5-10 мг в/в
```

### 2. Запуск пайплайна

```bash
# Базовый запуск (легкая модель)
python run_pipeline.py

# С выбором модели качества
python run_pipeline.py --model balanced --recreate-db

# Полный набор параметров
python run_pipeline.py \
    --config config/embeddings.yaml \
    --model high_quality \
    --chunk-dir data/chunks_simple \
    --db-path data/chromadb \
    --recreate-db \
    --log-level DEBUG
```

### 3. Поиск в CLI

```python
from src.embeddings.vector_db import ChromaManager
from src.embeddings.model_loader import load_embedding_model

# Загрузка
model, _ = load_embedding_model("config/embeddings.yaml", "light")
db = ChromaManager(persist_dir="data/chromadb")
collection = db.get_collection()

# Поиск
query = "Как купировать приступ тахикардии?"
results = collection.query(
    query_embeddings=model.encode([query]).tolist(),
    n_results=5
)

for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
    print(f"{meta['icd10_code']}: {doc[:200]}...")
```

## Структура проекта

```
ClinAI/
├── clinical_protocols/     # Исходные протоколы (Markdown + YAML)
│   ├── I47.1.md            # Пример: наджелудочковая тахикардия
│   └── I20.md              # Пример: стенокардия
├── config/                  # Конфигурация
│   ├── embeddings.yaml     # Настройки моделей эмбеддингов
│   └── validation_rules.yaml # Правила валидации
├── data/                    # Данные пайплайна
│   ├── chunks_simple/       # Результат чанкинга
│   └── chromadb/           # Векторная база данных
├── src/                     # Исходный код
│   ├── ingestion/           # Загрузка и валидация
│   ├── chunking/           # Чанкинг протоколов
│   ├── embeddings/         # Модели и векторизация
│   ├── models/             # Pydantic модели данных
│   └── utils/              # Утилиты
├── run_pipeline.py          # Главный скрипт запуска
└── pyproject.toml           # Зависимости проекта
```

## Конфигурация моделей

В файле `config/embeddings.yaml`:

| Модель | Репозиторий | RAM | GPU | Применение |
|--------|-------------|-----|-----|------------|
| `light` | paraphrase-multilingual-MiniLM-L12-v2 | 500MB | Нет | CPU, VPS, ограниченные ресурсы |
| `balanced` | multilingual-e5-base | 2GB | Да | Коллаб, хорошее качество |
| `high_quality` | multilingual-e5-large | 4GB | Да | Максимальное качество |

```yaml
embeddings:
  default: "light"
  models:
    light:
      repo: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
      device: "cpu"
      batch_size: 4
    balanced:
      repo: "intfloat/multilingual-e5-base"
      device: "auto"
      batch_size: 8
    high_quality:
      repo: "intfloat/multilingual-e5-large"
      device: "auto"
      batch_size: 16
```

## Создание VectorDB в Google Colab

Если серверные ресурсы ограничены:

1. Загрузите `all_chunks.json` на Google Drive
2. Откройте [VectorDB.ipynb](./VectorDB.ipynb) в Google Colab
3. Укажите пути к файлам и запустите
4. Скачайте созданную папку `chromadb` обратно на сервер

Подробности см. в [ClinAI_Colab_Setup.md](./ClinAI_Colab_Setup.md).

## Типы секций

Чанкер автоматически классифицирует секции протокола:

| Тип | Ключевые слова | Описание |
|-----|----------------|----------|
| `general` | общая информация, описание | Общие сведения о заболевании |
| `diagnostics` | диагност, обследован | Диагностические процедуры |
| `treatment` | лечение, терап, профилакт | Методы лечения |
| `treatment_acute` | купир, неотлож, остр | Неотложная помощь |
| `monitoring` | наблюд, монитор | Требования к мониторингу |
| `contraindications` | противопоказ | Противопоказания |
| `side_effects` | осложн | Побочные эффекты |

## CLI-параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--config` | Путь к конфигу эмбеддингов | `config/embeddings.yaml` |
| `--model` | Ключ модели: light/balanced/high_quality | Из конфига |
| `--chunk-dir` | Папка для чанков | `data/chunks_simple` |
| `--db-path` | Путь к VectorDB | `data/chromadb` |
| `--recreate-db` | Очистить существующую БД | False |
| `--log-level` | Уровень логирования | INFO |

## Разработка

### Тесты

```bash
# Тест чанкинга
python -m pytest test_chunking.py -v

# Тест ingestion
python -m pytest test_ingestion.py -v
```

### Логирование

```python
from src.utils.logger import setup_logger
setup_logger("ClinAI", level="DEBUG")
```

## Лицензия

MIT License — свободное использование в личных и коммерческих проектах.

## Контрибьюция

1. Fork репозитория
2. Создайте ветку для фичи (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

**Примечание**: ClinAI предоставляется как есть. Медицинские решения должны приниматься квалифицированными специалистами. Система предназначена для информационной поддержки, а не для замены профессиональной медицинской консультации.
