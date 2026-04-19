# src/embeddings/config.py
import os
import yaml
import torch
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: str = "config/embeddings.yaml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Embedding config not found: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def resolve_model_key(config: Dict[str, Any], requested_key: str = None) -> str:
    """Определяет ключ модели: CLI/ENV > config.default"""
    env_key = os.environ.get("EMBEDDING_MODEL")
    return requested_key or env_key or config["embeddings"]["default"]

def get_model_config(config: Dict[str, Any], model_key: str) -> Dict[str, Any]:
    """Возвращает конфиг выбранной модели с разрешением device"""
    models = config["embeddings"]["models"]
    if model_key not in models:
        raise ValueError(f"Model '{model_key}' not found. Available: {list(models.keys())}")
    
    cfg = models[model_key].copy()
    
    # Авто-определение устройства
    if cfg.get("device") == "auto":
        cfg["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Валидация железа (предупреждение, не блок)
    import psutil
    ram_mb = psutil.virtual_memory().available / (1024 * 1024)
    if ram_mb < cfg.get("min_ram_mb", 0) * 0.7:
        print(f"⚠️  [Hardware] Возможно недостаточно ОЗУ для '{model_key}'. "
              f"Доступно: {ram_mb:.0f} МБ, рекомендуется: {cfg['min_ram_mb']} МБ. "
              f"Используйте '--model light' если возникнет OOM.")
    
    return cfg

