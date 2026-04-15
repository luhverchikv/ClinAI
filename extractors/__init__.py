# -*- coding: utf-8 -*-
"""
Экстракторы для клинических протоколов.
"""

from .base_extractor import BaseExtractor, ClinicalChunk
from .pdf_extractor import PDFExtractor
from .image_extractor import ImageExtractor

__all__ = ['BaseExtractor', 'ClinicalChunk', 'PDFExtractor', 'ImageExtractor']
