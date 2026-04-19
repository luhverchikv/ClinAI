# src/embeddings/model_loader.py
import os
import torch
import logging
from sentence_transformers import SentenceTransformer
from .config import load_config, resolve_model_key, get_model_config

logger = logging.getLogger(__name__)

def load_embedding_model(config_path: str = "config/embeddings.yaml", 
                         model_key: str = None) -> tuple[SentenceTransformer, dict]:
    cfg = load_config(config_path)
    key = resolve_model_key(cfg, model_key)
    model_cfg = get_model_config(cfg, key)
    
    logger.info(f"📦 Загрузка модели: {key} → {model_cfg['repo']}")
    logger.info(f"💻 Device: {model_cfg['device']} | Batch: {model_cfg['batch_size']}")
    
    # Оптимизация для CPU
    if model_cfg["device"] == "cpu":
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        os.environ.update({
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "TRANSFORMERS_CACHE": model_cfg.get("settings", {}).get("cache_dir", ".cache/huggingface")
        })
    
    # Установка HF cache
    os.environ["HF_HOME"] = model_cfg.get("settings", {}).get("cache_dir", ".cache/huggingface")
    
    model = SentenceTransformer(model_cfg["repo"], device=model_cfg["device"])
    logger.info(f"✅ Модель загружена. Размерность: {model.get_sentence_embedding_dimension()}")
    
    return model, model_cfg

