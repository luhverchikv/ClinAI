# -*- coding: utf-8 -*-
"""
Главный парсер для извлечения клинических протоколов.
Поддерживает PDF и изображения.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Union

from extractors import PDFExtractor, ImageExtractor, ClinicalChunk


class ClinicalProtocolParser:
    """Парсер клинических протоколов для RAG системы."""

    SUPPORTED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']

    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.image_extractor = ImageExtractor()

    def parse_file(self, file_path: str) -> List[ClinicalChunk]:
        """Парсинг одного файла."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == '.pdf':
            return self.pdf_extractor.extract(str(path.absolute()))
        elif extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return self.image_extractor.extract(str(path.absolute()))
        else:
            raise ValueError(f"Неподдерживаемый формат: {extension}")

    def parse_directory(self, directory: str, recursive: bool = True) -> List[ClinicalChunk]:
        """Парсинг всех файлов в директории."""
        path = Path(directory)
        all_chunks = []

        pattern = "**/*" if recursive else "*"
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    chunks = self.parse_file(str(file_path))
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"Ошибка при обработке {file_path}: {e}")

        return all_chunks

    def parse_from_text(self, text: str, source_name: str = "manual_input") -> List[ClinicalChunk]:
        """Парсинг из текста."""
        return self.pdf_extractor.extract_from_text(text, source_name)

    def to_json(self, chunks: List[ClinicalChunk], output_path: str = None) -> str:
        """Экспорт фрагментов в JSON."""
        data = [chunk.to_dict() for chunk in chunks]

        json_str = json.dumps(data, ensure_ascii=False, indent=2)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)

        return json_str

    def to_markdown(self, chunks: List[ClinicalChunk]) -> str:
        """Экспорт фрагментов в Markdown для просмотра."""
        lines = ["# Клинические протоколы\n"]

        current_diagnosis = None

        for chunk in chunks:
            # Группировка по диагнозам
            if chunk.diagnosis != current_diagnosis:
                current_diagnosis = chunk.diagnosis
                lines.append(f"\n## {chunk.diagnosis} ({chunk.icd_code})\n")

            # Заголовок фрагмента
            section_emoji = {
                "diagnosis": "🔬",
                "emergency": "🚨",
                "prophylaxis": "💊",
                "treatment": "💉"
            }.get(chunk.section_type, "📋")

            lines.append(f"### {section_emoji} {chunk.title}\n")

            # Контент
            lines.append(f"{chunk.content}\n")

            # Препараты
            if chunk.medications:
                lines.append("**Препараты:**\n")
                for med in chunk.medications:
                    med_str = f"- {med.get('name', '')}"
                    if med.get('dosage'):
                        med_str += f" — {med.get('dosage')}"
                    if med.get('route'):
                        med_str += f" ({med.get('route')})"
                    lines.append(med_str + "\n")

            # Противопоказания
            if chunk.contraindications:
                lines.append(f"**Противопоказания:** {', '.join(chunk.contraindications)}\n")

            lines.append("---\n")

        return ''.join(lines)


def main():
    """CLI интерфейс."""
    import argparse

    parser = argparse.ArgumentParser(description='Парсер клинических протоколов для RAG')
    parser.add_argument('input', help='Путь к файлу или директории')
    parser.add_argument('-o', '--output', help='Путь для сохранения JSON')
    parser.add_argument('-m', '--markdown', help='Путь для сохранения Markdown')
    parser.add_argument('-r', '--recursive', action='store_true', help='Рекурсивный обход директории')
    parser.add_argument('-t', '--text', help='Парсинг из текста (вместо файла)')

    args = parser.parse_args()

    parser_instance = ClinicalProtocolParser()

    # Парсинг
    if args.text:
        chunks = parser_instance.parse_from_text(args.text, "manual_input")
    else:
        path = Path(args.input)
        if path.is_dir():
            chunks = parser_instance.parse_directory(args.input, args.recursive)
        else:
            chunks = parser_instance.parse_file(args.input)

    print(f"Извлечено фрагментов: {len(chunks)}")

    # Экспорт
    if args.output:
        parser_instance.to_json(chunks, args.output)
        print(f"JSON сохранён: {args.output}")

    if args.markdown:
        md_content = parser_instance.to_markdown(chunks)
        with open(args.markdown, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown сохранён: {args.markdown}")

    # Вывод в консоль
    if not args.output and not args.markdown:
        print("\n" + parser_instance.to_markdown(chunks))


if __name__ == '__main__':
    main()
