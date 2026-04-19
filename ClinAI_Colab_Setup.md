# ClinAI Vector Database Setup на Google Colab

Этот notebook поможет вам создать векторную базу данных ChromaDB из ваших чанков на Google Colab.

## Шаг 1: Подключение Google Drive и установка зависимостей

```python
# Подключаем Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Устанавливаем необходимые пакеты
!pip install sentence-transformers chromadb pyyaml python-frontmatter pydantic tqdm
```

## Шаг 2: Клонируем репозиторий (для структуры)

```python
!git clone https://github.com/luhverchikv/ClinAI.git
%cd ClinAI
```

## Шаг 3: Настройка путей

```python
import os
import json
from pathlib import Path

# Путь к вашему файлу с чанками на Google Drive
CHUNKS_PATH = '/content/drive/MyDrive/ClinAI/data/all_chunks.json'  # Измените путь!

# Путь для сохранения векторной БД
VECTOR_DB_PATH = '/content/drive/MyDrive/ClinAI/data/chromadb'

# Создаём директории
os.makedirs(VECTOR_DB_PATH, exist_ok=True)
os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
```

## Шаг 4: Загрузка и проверка чанков

```python
# Загружаем чанки
with open(CHUNKS_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

chunks = data.get('chunks', [])
print(f"✅ Загружено чанков: {len(chunks)}")

# Проверяем структуру первого чанка
if chunks:
    print(f"📋 Пример чанка: {chunks[0]}")
```

## Шаг 5: Создание векторной базы данных

```python
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import gc

# ====== НАСТРОЙКИ ======
# Выберите модель в зависимости от ваших потребностей:
# 'light' - быстрая, для CPU, ~120MB
# 'balanced' - средняя, мультиязычная, ~1.1GB
# 'high_quality' - лучшее качество, ~2.2GB

MODEL_NAME = 'light'  # Измените на 'balanced' или 'high_quality' если нужно

MODEL_CONFIGS = {
    'light': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    'balanced': 'intfloat/multilingual-e5-base',
    'high_quality': 'intfloat/multilingual-e5-large'
}

BATCH_SIZE = 4 if MODEL_NAME == 'light' else 8

print(f"🤖 Загрузка модели: {MODEL_CONFIGS[MODEL_NAME]}")
model = SentenceTransformer(MODEL_CONFIGS[MODEL_NAME])
print("✅ Модель загружена!")

# Инициализируем ChromaDB
chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
collection = chroma_client.get_or_create_collection(name="clinical_protocols")

print(f"🚀 Начало векторизации {len(chunks)} чанков...")
```

## Шаг 6: Обработка чанков батчами

```python
from tqdm import tqdm

# Обработка батчами для экономии памяти
for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Векторизация"):
    batch = chunks[i:i + BATCH_SIZE]

    # Получаем тексты
    texts = [c['text'] for c in batch]

    # Создаём эмбеддинги
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    # Подготавливаем данные для ChromaDB
    ids = [f"chunk_{i+j}" for j in range(len(batch))]
    metadatas = [c.get('metadata', {}) for c in batch]
    documents = texts

    # Добавляем в коллекцию
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        documents=documents
    )

    # Очищаем память
    gc.collect()

print(f"🎉 Готово! Векторная база сохранена в: {VECTOR_DB_PATH}")
print(f"📊 Всего документов: {collection.count()}")
```

## Шаг 7: Проверка работоспособности

```python
# Тестовый запрос
test_query = "Что такое клинический протокол?"

# Получаем эмбеддинг запроса
query_embedding = model.encode([test_query], normalize_embeddings=True).tolist()

# Ищем похожие документы
results = collection.query(
    query_embeddings=query_embedding,
    n_results=3
)

print(f"🔍 Результаты поиска по запросу: '{test_query}'")
for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
    print(f"\n--- Результат {i+1} ---")
    print(f"Текст: {doc[:200]}...")
    print(f"Метаданные: {meta}")
```

## Шаг 8: Экспорт (опционально)

```python
# Для скачивания ChromaDB на локальный компьютер
import shutil

# Создаём архив
shutil.make_archive('/content/chromadb_backup', 'zip', VECTOR_DB_PATH)
print("📦 Архив создан: /content/chromadb_backup.zip")
print("💾 Скачайте архив через Files → ChromeOS → Downloads")
```

---

## Важные моменты:

1. **Runtime**: Для GPU выберите Runtime → Change runtime type → GPU (рекомендуется для моделей balanced/high_quality)

2. **Размер чанков**: Если у вас очень много чанков (>10000), рекомендуется использовать модель 'light' с batch_size=4

3. **Google Drive лимит**: Бесплатный Google Drive имеет ограничение на размер файлов. Если ваша БД >15GB, разделите на части

4. **Стоимость**: Google Colab бесплатен, но имеет ограничения по времени сессии. Для больших датасетов используйте Colab Pro
