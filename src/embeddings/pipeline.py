# src/embeddings/pipeline.py
import json
import gc
from tqdm import tqdm
from pathlib import Path
from src.embeddings.model_loader import load_embedding_model
from src.embeddings.vector_db import ChromaManager
import logging

logger = logging.getLogger(__name__)

class EmbeddingPipeline:
    def __init__(self, config_path: str = "config/embeddings.yaml", 
                 model_key: str = None, db_path: str = "data/chromadb"):
        self.model, self.cfg = load_embedding_model(config_path, model_key)
        self.db = ChromaManager(persist_dir=db_path)
        self.batch_size = self.cfg["batch_size"]
        self.normalize = self.cfg.get("settings", {}).get("normalize_embeddings", True)
        self.show_progress = self.cfg.get("settings", {}).get("show_progress", True)
    
    def run(self, chunks_path: str, recreate_db: bool = False):
        logger.info(f"📂 Загрузка чанков: {chunks_path}")
        with open(chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        chunks = data.get("chunks", [])
        if not chunks:
            logger.warning("Пустой список чанков. Завершаю.")
            return
        
        collection = self.db.get_collection(recreate=recreate_db)
        logger.info(f"🚀 Векторизация {len(chunks)} чанков (batch_size={self.batch_size})...")
        
        for i in tqdm(range(0, len(chunks), self.batch_size), 
                     desc="Векторизация", disable=not self.show_progress):
            batch = chunks[i:i + self.batch_size]
            texts = [c["text"] for c in batch]
            
            embeddings = self.model.encode(
                texts, 
                show_progress_bar=False, 
                normalize_embeddings=self.normalize,
                batch_size=self.batch_size
            ).tolist()
            
            for chunk, emb in zip(batch, embeddings):
                chunk["embedding"] = emb
            
            self.db.upsert_chunks(batch)
            gc.collect()  # Освобождаем память после каждого батча
        
        logger.info(f"🎉 Векторная база готова! {len(chunks)} документов → {self.db.persist_dir}")

