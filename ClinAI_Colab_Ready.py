"""
ClinAI Vector Database Creator для Google Colab
===============================================
Запустите этот код в Google Colab для создания векторной базы данных.

Инструкция:
1. Откройте Google Colab: https://colab.research.google.com
2. Создайте новый notebook
3. Скопируйте весь код из этого файла в ячейку
4. Запустите (Shift+Enter)
"""

# ============================================================
# БЛОК 1: Установка зависимостей и подключение Google Drive
# ============================================================
print("=" * 60)
print("ClinAI Vector Database Creator")
print("=" * 60)

# Подключаем Google Drive
from google.colab import drive
drive.mount('/content/drive')
print("✅ Google Drive подключен")

# Устанавливаем зависимости
!pip install sentence-transformers chromadb pyyaml -q
print("✅ Зависимости установлены")

# ============================================================
# БЛОК 2: Конфигурация (ИЗМЕНИТЕ ЭТИ ПУТИ!)
# ============================================================

# ИЗМЕНИТЕ ЭТИ ПУТИ СООТВЕТСТВЕННО ВАШЕЙ ФАЙЛОВОЙ СИСТЕМЕ:
CHUNKS_PATH = '/content/drive/MyDrive/ClinAI/data/all_chunks.json'
VECTOR_DB_PATH = '/content/drive/MyDrive/ClinAI/data/chromadb'

# Выбор модели (light, balanced, high_quality)
MODEL_NAME = 'light'  # ⚡ light - быстрая, balanced - качественная, high_quality - лучшая

# ============================================================
# БЛОК 3: Загрузка чанков
# ============================================================
import json
import os
from pathlib import Path

# Создаём директорию для БД
os.makedirs(VECTOR_DB_PATH, exist_ok=True)

# Загружаем чанки
print(f"\n📂 Загрузка чанков из: {CHUNKS_PATH}")

if not os.path.exists(CHUNKS_PATH):
    print("❌ ОШИБКА: Файл не найден!")
    print("   Проверьте путь CHUNKS_PATH")
else:
    with open(CHUNKS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = data.get('chunks', [])
    print(f"✅ Загружено чанков: {len(chunks)}")

# ============================================================
# БЛОК 4: Загрузка модели и создание эмбеддингов
# ============================================================
from sentence_transformers import SentenceTransformer
import chromadb
import gc
from tqdm import tqdm

# Конфигурация моделей
MODEL_CONFIGS = {
    'light': {
        'repo': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'batch_size': 4,
        'description': '⚡ Легкая модель (~120MB) - быстрая, для CPU'
    },
    'balanced': {
        'repo': 'intfloat/multilingual-e5-base',
        'batch_size': 8,
        'description': '⚖️ Средняя модель (~1.1GB) - хорошее качество'
    },
    'high_quality': {
        'repo': 'intfloat/multilingual-e5-large',
        'batch_size': 16,
        'description': '🏆 Лучшая модель (~2.2GB) - максимальное качество'
    }
}

# Проверка выбора модели
if MODEL_NAME not in MODEL_CONFIGS:
    print(f"❌ Неизвестная модель: {MODEL_NAME}")
    print(f"   Доступные: {list(MODEL_CONFIGS.keys())}")
    MODEL_NAME = 'light'

config = MODEL_CONFIGS[MODEL_NAME]
BATCH_SIZE = config['batch_size']

print(f"\n🤖 Загрузка модели: {config['repo']}")
print(f"   {config['description']}")

model = SentenceTransformer(config['repo'])
print("✅ Модель загружена!")

# ============================================================
# БЛОК 5: Создание ChromaDB коллекции
# ============================================================
print(f"\n🗄️ Инициализация ChromaDB...")
print(f"   Путь: {VECTOR_DB_PATH}")

chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
collection = chroma_client.get_or_create_collection(name="clinical_protocols")
print(f"✅ ChromaDB инициализирована!")

# ============================================================
# БЛОК 6: Векторизация чанков
# ============================================================
print(f"\n🚀 Начало векторизации {len(chunks)} чанков...")
print(f"   Размер батча: {BATCH_SIZE}")
print(f"   Всего батчей: {len(chunks) // BATCH_SIZE + 1}")

for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Векторизация"):
    batch = chunks[i:i + BATCH_SIZE]

    # Получаем тексты из чанков
    texts = [c['text'] for c in batch]

    # Создаём эмбеддинги
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
        batch_size=BATCH_SIZE
    )

    # Подготавливаем данные для ChromaDB
    ids = [f"chunk_{i + j}" for j in range(len(batch))]
    metadatas = [c.get('metadata', {}) for c in batch]

    # Добавляем в коллекцию
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        documents=texts
    )

    # Очищаем память
    gc.collect()

# ============================================================
# БЛОК 7: Финальная информация
# ============================================================
print("\n" + "=" * 60)
print("🎉 ВЕКТОРНАЯ БАЗА ДАННЫХ УСПЕШНО СОЗДАНА!")
print("=" * 60)
print(f"📍 Путь: {VECTOR_DB_PATH}")
print(f"📊 Всего документов: {collection.count()}")
print(f"🧠 Модель: {MODEL_CONFIGS[MODEL_NAME]['repo']}")

# ============================================================
# БЛОК 8: Тестовый поиск
# ============================================================
print("\n" + "-" * 60)
print("🔍 Тестирование поиска...")

test_query = "клинический протокол лечение"
query_embedding = model.encode([test_query], normalize_embeddings=True).tolist()

results = collection.query(
    query_embeddings=query_embedding,
    n_results=3
)

print(f"\nЗапрос: '{test_query}'")
print(f"Найдено результатов: {len(results['documents'][0])}")

for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
    print(f"\n--- Результат {i+1} ---")
    print(f"Текст: {doc[:150]}...")
    if meta:
        print(f"Метаданные: {meta}")

# ============================================================
# БЛОК 9: Инструкции по использованию
# ============================================================
print("\n" + "=" * 60)
print("📋 СЛЕДУЮЩИЕ ШАГИ:")
print("=" * 60)
print("""
1. ✅ Векторная база данных сохранена на Google Drive
2. 📥 Скачайте папку chromadb на свой сервер
3. 🚀 Используйте в своём проекте ClinAI:
   - Установите зависимости: pip install chromadb sentence-transformers
   - Укажите путь к скачанной БД в config

4. 💡 Для скачивания ChromaDB:
   - Откройте Google Drive
   - Найдите папку: ClinAI/data/chromadb
   - Скачайте всю папку
""")
