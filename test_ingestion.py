#!/usr/bin/env python3
from src.ingestion.pipeline import run_ingestion_pipeline
from src.utils.logger import setup_logger

if __name__ == "__main__":
    setup_logger("ClinAI")
    try:
        result = run_ingestion_pipeline()
        print(f"✅ Готово! Успешно обработано: {result['parsed_count']} файлов")
        print(f"📊 Отчёт валидации: {result['validation_report']}")
    except Exception as e:
        print(f"❌ Ошибка пайплайна: {e}")
        raise
