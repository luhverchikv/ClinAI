# src/preprocessing/section_parser.py
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class SectionBlock:
    """Представляет секцию или подраздел с иерархией"""
    title: str
    level: int  # 2 для ##, 3 для ###
    content: str
    parent_title: Optional[str] = None
    hierarchy_path: str = ""
    
    def get_section_type(self) -> str:
        t = self.title.lower()
        mapping = {
            "общая информация": "general", "описание": "general", "введение": "general",
            "диагност": "diagnostics", "обследован": "diagnostics", "критерии": "diagnostics",
            "лечение": "treatment", "терап": "treatment", "медикаментоз": "treatment",
            "купир": "treatment_acute", "неотлож": "treatment_acute", "остр": "treatment_acute",
            "наблюд": "monitoring", "монитор": "monitoring", "диспансер": "monitoring",
            "противопоказ": "contraindications", "огранич": "contraindications",
            "осложн": "side_effects", "побочн": "side_effects", "реабилит": "rehabilitation"
        }
        for k, v in mapping.items():
            if k in t:
                return v
        return "other"

class SectionParser:
    """Парсит Markdown на иерархические блоки секций"""
    
    # Паттерн для заголовков: ## Заголовок или ### Подзаголовок
    HEADER_PATTERN = re.compile(r'^(#{2,3})\s+(.+?)\s*$', re.MULTILINE)
    
    @classmethod
    def parse(cls, markdown: str, source_file: str = "") -> List[SectionBlock]:
        """
        Разбивает Markdown на иерархические блоки.
        Возвращает список SectionBlock с сохранением родительских связей.
        """
        if not markdown:
            return []
        
        blocks = []
        lines = markdown.split('\n')
        
        current_block: Optional[SectionBlock] = None
        parent_stack: List[Tuple[str, int]] = []  # (title, level)
        
        for line in lines:
            header_match = cls.HEADER_PATTERN.match(line.strip())
            
            if header_match:
                # Сохраняем предыдущий блок
                if current_block and current_block.content.strip():
                    blocks.append(current_block)
                
                # Определяем уровень и название нового заголовка
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Обновляем стек родителей
                while parent_stack and parent_stack[-1][1] >= level:
                    parent_stack.pop()
                
                parent_title = parent_stack[-1][0] if parent_stack else None
                hierarchy = " > ".join([p[0] for p in parent_stack] + [title])
                
                # Создаём новый блок
                current_block = SectionBlock(
                    title=title,
                    level=level,
                    content="",
                    parent_title=parent_title,
                    hierarchy_path=hierarchy
                )
                
                if level == 2:  # ## — новый родитель
                    parent_stack = [p for p in parent_stack if p[1] < 2]
                    parent_stack.append((title, level))
                elif level == 3:  # ### — подраздел
                    parent_stack.append((title, level))
                    
            elif current_block:
                # Добавляем строку к контенту текущего блока
                current_block.content += line + "\n"
        
        # Не забываем последний блок
        if current_block and current_block.content.strip():
            blocks.append(current_block)
        
        return blocks
    
    @classmethod
    def group_by_type(cls, blocks: List[SectionBlock]) -> Dict[str, List[SectionBlock]]:
        """Группирует блоки по типу секции"""
        grouped = {}
        for block in blocks:
            sec_type = block.get_section_type()
            if sec_type not in grouped:
                grouped[sec_type] = []
            grouped[sec_type].append(block)
        return grouped

