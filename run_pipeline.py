#!/usr/bin/env python3
"""
ClinAI: Полный пайплайн Ingestion → Chunking → Embeddings → VectorDB
Использование: python run_pipeline.py --model balanced --recreate-db
"""
import argparse
import logging
from src.utils.logger import setup_logger
from src.ingestion.pipeline import run_ingestion_pipeline
from src.chunking.pipeline import SimpleChunkingPipeline
from src.embeddings.pipeline import EmbeddingPipeline

def main():
    parser = argparse.ArgumentParser(description="ClinAI RAG Pipeline")
    parser.add_argument("--config", default="config/embeddings.yaml", help="Path to embeddings config")
    parser.add_argument("--model", default=None, help="Model key: light, balanced, high_quality")
    parser.add_argument("--chunk-dir", default="data/chunks_simple", help="Output dir for chunks")
    parser.add_argument("--db-path", default="data/chromadb", help="Vector DB path")
    parser.add_argument("--recreate-db", action="store_true", help="Clear existing vector DB")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    
    setup_logger("ClinAI", level=args.log_level)
    logging.info("🚀 Запуск ClinAI Pipeline...")
    
    # 1. Ingestion
    ingestion = run_ingestion_pipeline()
    
    # 2. Chunking
    chunker = SimpleChunkingPipeline(output_dir=args.chunk_dir)
    chunk_result = chunker.process_protocols(ingestion["protocols_json"])
    
    # 3. Embeddings & DB
    emb = EmbeddingPipeline(
        config_path=args.config,
        model_key=args.model,
        db_path=args.db_path
    )
    emb.run(chunk_result["all_chunks"], recreate_db=args.recreate_db)
    
    logging.info("✅ Пайплайн завершён успешно.")

if __name__ == "__main__":
    main()

