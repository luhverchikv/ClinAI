# -*- coding: utf-8 -*-
"""
Экстрактор для изображений (OCR) клинических протоколов.
"""

import re
import uuid
from typing import List, Dict, Any
from pathlib import Path

from .base_extractor import BaseExtractor, ClinicalChunk


class ImageExtractor(BaseExtractor):
    """Экстрактор для изображений с OCR."""

    def __init__(self):
        self.available_ocr = self._check_ocr_availability()

    def _check_ocr_availability(self) -> str:
        """Проверка доступности OCR движков."""
        try:
            import pytesseract
            return "tesseract"
        except ImportError:
            pass

        try:
            import easyocr
            return "easyocr"
        except ImportError:
            pass

        return "none"

    def extract(self, file_path: str) -> List[ClinicalChunk]:
        """Извлечение из изображения через OCR."""
        if self.available_ocr == "none":
            raise RuntimeError(
                "Установите OCR библиотеку: pip install pytesseract (требует Tesseract OCR) "
                "или pip install easyocr"
            )

        text = self._perform_ocr(file_path)
        return self.extract_from_text(text, Path(file_path).name)

    def extract_from_text(self, text: str, source_file: str = "") -> List[ClinicalChunk]:
        """Извлечение структурированных фрагментов из OCR текста."""
        # Используем те же методы что и PDFExtractor
        from .pdf_extractor import PDFExtractor
        extractor = PDFExtractor()
        return extractor.extract_from_text(text, source_file)

    def _perform_ocr(self, file_path: str) -> str:
        """Выполнение OCR на изображении."""
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("Установите Pillow: pip install pillow")

        image = Image.open(file_path)

        if self.available_ocr == "tesseract":
            import pytesseract
            text = pytesseract.image_to_string(image, lang='rus+eng')
            return text

        elif self.available_ocr == "easyocr":
            import easyocr
            reader = easyocr.Reader(['ru', 'en'])
            results = reader.readtext(file_path)

            text_parts = []
            for detection in results:
                text_parts.append(detection[1])

            return '\n'.join(text_parts)

        return ""
