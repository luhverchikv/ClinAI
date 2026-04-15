# Клинический парсер для RAG-системы

## Обзор

Инструмент для извлечения и структурирования клинических протоколов в формат, готовый для векторной базы данных. Помогает врачам находить рекомендации по диагностике и лечению на основе запросов.

## Структура проекта

```
clinical_parser/
├── extractors/
│   ├── __init__.py
│   ├── base_extractor.py      # Базовый класс для экстракторов
│   ├── pdf_extractor.py       # Экстрактор для PDF файлов
│   └── image_extractor.py     # Экстрактор для изображений (OCR)
├── parser.py                   # Главный парсер
├── vector_db.py               # Экспорт для векторных БД
├── search_engine.py           # Поисковая система
├── demo.py                    # Пример использования
└── requirements.txt           # Зависимости
```

## Установка

```bash
pip install -r requirements.txt
```

Для OCR (распознавание текста из изображений):
```bash
# Вариант 1: Tesseract OCR
pip install pytesseract
# Требует установки Tesseract OCR на систему

# Вариант 2: EasyOCR (без системных зависимостей)
pip install easyocr
```

## Использование

### 1. Парсинг PDF файла

```bash
python -m parser <путь_к_pdf> -o output.json
```

### 2. Парсинг директории

```bash
python -m parser ./clinical_protocols/ -r -o all_chunks.json
```

### 3. Парсинг из текста

```bash
python -m parser -t "Наджелудочковая тахикардия I47.1 лечение" -o text_chunks.json
```

### 4. Экспорт для векторных БД

```bash
# Pinecone
python -m vector_db ./chunks.json -o pinecone_format.json --format pinecone

# Qdrant
python -m vector_db ./chunks.json -o qdrant_format.json --format qdrant

# ChromaDB
python -m vector_db ./chunks.json -o chromadb_format.json --format chromadb

# С OpenAI эмбеддингами
python -m vector_db ./chunks.json -o embedded.json --format openai --api-key YOUR_KEY
```

### 5. Поиск

```bash
# Поиск по запросу
python -m search_engine --data chunks.json -q "тахикардия диагностика"

# Поиск по коду МКБ
python -m search_engine --data chunks.json --icd I47.1

# Поиск препарата
python -m search_engine --data chunks.json --med "Верапамил"
```

## Структура данных

### ClinicalChunk

```json
{
  "chunk_id": "uuid",
  "diagnosis": "Наджелудочковая тахикардия",
  "icd_code": "I47.1",
  "section_type": "emergency|prophylaxis|diagnosis|treatment",
  "title": "Купирование приступа: Верапамил",
  "content": "Полный текст фрагмента...",
  "medications": [
    {
      "name": "Верапамил",
      "dosage": "5-10 мг",
      "dosage_form": "0,25% раствор 2-4 мл",
      "route": "внутривенно медленно"
    }
  ],
  "contraindications": ["Острый коронарный синдром", "Бронхиальная астма"],
  "procedures": ["ЭКГ в 12 отведениях", "Консультация кардиолога"],
  "source_file": "protocol.pdf",
  "source_page": 1
}
```

## Интеграция с RAG

### Pinecone

```python
from pinecone import Pinecone

pc = Pinecone(api_key="your-key")
index = pc.Index("clinical-protocols")

# Загрузка данных
import json
with open("pinecone_format.json") as f:
    vectors = json.load(f)

# Добавление векторов (предварительно получите эмбеддинги)
index.upsert(vectors)
```

### ChromaDB

```python
import chromadb

client = chromadb.Client()
collection = client.create_collection("clinical_protocols")

with open("chromadb_format.json") as f:
    data = json.load(f)

collection.add(
    ids=data["ids"],
    embeddings=data["embeddings"],
    metadatas=data["metadatas"],
    documents=data["documents"]
)
```

## API для RAG-системы

```python
from search_engine import ClinicalSearchEngine

# Инициализация
engine = ClinicalSearchEngine()
engine.load_from_json("chunks.json")

# Поиск рекомендаций
results = engine.search("Фибрилляция предсердий лечение", top_k=5)

for result in results:
    print(f"📋 {result.title}")
    print(f"💊 {result.medications}")
    print(f"⚠️ Противопоказания: {result.contraindications}")
```

## Разработка

### Запуск тестов

```bash
python demo.py
```

### Добавление нового экстрактора

1. Создайте класс, наследующий `BaseExtractor`
2. Реализуйте методы `extract()` и `extract_from_text()`
3. Добавьте в `extractors/__init__.py`

## Лицензия

MIT
