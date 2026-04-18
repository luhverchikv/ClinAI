#!/usr/bin/env python3
from src.ingestion.pipeline import run_ingestion_pipeline
from src.chunking.pipeline import ChunkingPipeline
from src.utils.logger import setup_logger

if __name__ == "__main__":
    setup_logger("ClinAI")
    
    # Шаг 1: Ингестия и валидация
    print("🔄 Шаг 1: Загрузка и валидация...")
    ingestion_result = run_ingestion_pipeline()
    
    # Шаг 2: Чанкинг
    print("🔄 Шаг 2: Чанкинг...")
    chunker = ChunkingPipeline(
        output_dir="data/chunks",
        min_chunk_chars=150,
        max_chunk_chars=700,
        overlap_chars=60
    )
    chunking_result = chunker.process_protocols(ingestion_result["protocols_json"])
    
    # Итоги
    stats = chunking_result["stats"]
    print(f"\n✅ Готово!")
    print(f"📊 Протоколов: {stats['total_protocols']}")
    print(f"📦 Чанков: {stats['total_chunks']}")
    print(f"💊 Чанков с препаратами: {stats['chunks_with_medications']}")
    print(f"📁 Выход: {chunking_result['all_chunks']}")
    print(f"📈 По секциям: {stats['chunks_by_section']}")
