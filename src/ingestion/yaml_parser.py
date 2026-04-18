# src/ingestion/yaml_parser.py
import re
import yaml
from typing import Tuple, Optional
import frontmatter  # pip install python-frontmatter
import logging

logger = logging.getLogger(__name__)

class YAMLParseError(Exception):
    """Исключение при ошибке парсинга YAML"""
    pass

class YAMLParser:
    """Парсит YAML frontmatter из Markdown файлов"""
    
    FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    
    @staticmethod
    def extract_frontmatter(content: str) -> Tuple[Optional[dict], str]:
        """
        Извлекает YAML frontmatter и возвращает (metadata_dict, body_content)
        """
        try:
            # Используем библиотеку python-frontmatter для надёжности
            post = frontmatter.loads(content)
            return dict(post.metadata), post.content
        except Exception as e:
            # Fallback: ручной парсинг
            match = YAMLParseError.FRONTMATTER_PATTERN.match(content)
            if match:
                try:
                    yaml_content = match.group(1)
                    metadata = yaml.safe_load(yaml_content)
                    body = content[match.end():]
                    return metadata, body
                except yaml.YAMLError as ye:
                    raise YAMLParseError(f"Ошибка YAML: {ye}")
            raise YAMLParseError("Frontmatter не найден или некорректен")
    
    @staticmethod
    def parse_sections(body: str) -> dict[str, str]:
        """
        Разбивает Markdown-тело на секции по заголовкам ##
        Возвращает: { "📋 Общая информация": "текст...", ... }
        """
        sections = {}
        # Паттерн: заголовок ## + название + контент до следующего ##
        pattern = re.compile(
            r'##\s+([^\n]+)\n(.*?)(?=\n##\s+|$)', 
            re.DOTALL
        )
        for match in pattern.finditer(body):
            section_name = match.group(1).strip()
            section_content = match.group(2).strip()
            sections[section_name] = section_content
        return sections

