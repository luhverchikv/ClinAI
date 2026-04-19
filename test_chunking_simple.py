#!/usr/bin/env python3
from src.ingestion.pipeline import run_ingestion_pipeline
from src.chunking.pipeline import SimpleChunkingPipeline
from src.utils.logger import setup_logger

if __name__ == "__main__":
    setup_logger("ClinAI")
    
    print("🔄 Шаг 1: Загрузка и валидация...")
    ingestion = run_ingestion_pipeline()
    
    print("🔄 Шаг 2: Простой чанкинг...")
    pipeline = SimpleChunkingPipeline(output_dir="data/chunks_simple")
    result = pipeline.process_protocols(ingestion["protocols_json"])
    
    stats = result["stats"]
    print(f"\n✅ Готово!")
    print(f"📊 Протоколов: {stats['total_protocols']}")
    print(f"📦 Чанков: {stats['total_chunks']}")
    print(f"📈 По секциям: {stats['by_section']}")
    print(f"📁 Выход: {result['all_chunks']}")
