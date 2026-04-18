# src/utils/config.py
import yaml
from pathlib import Path

def load_config(config_path: str) -> dict:
    """Загружает YAML-конфигурацию"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# src/utils/logger.py
import logging
import sys

def setup_logger(name: str, log_file: str = "logs/ingestion.log", 
                 level: str = "INFO") -> logging.Logger:
    """Настраивает логгер с выводом в консоль и файл"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консоль
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # Файл
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

