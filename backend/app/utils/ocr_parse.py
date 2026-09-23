import io
import os
import re
import warnings
from typing import Optional

_engine = None
_engine_inited = False


def _get_ocr_engine():
    """惰性加载 OCR 引擎：优先使用已安装的 rapidocr，其次尝试 paddleocr。"""
    global _engine, _engine_inited
    if _engine_inited:
        return _engine
    _engine_inited = True
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        _engine = RapidOCR()
        return _engine
    except Exception as e:
        warnings.warn(f"RapidOCR 不可用 ({e})")
    try:
        from paddleocr import PaddleOCR  # noqa: F401
        _engine = PaddleOCR(lang='ch', use_gpu=False)
        return _engine
    except Exception as e:
        warnings.warn(f"PaddleOCR 不可用 ({e})，OCR 识别功能将受限")
    _engine = None
    return None


class OCRParser:
    def __init__(self):
        self._engine = None

    @property
    def ocr_engine(self):
        if self._engine is None:
            self._engine = _get_ocr_engine()
        return self._engine

    def parse_file(self, file_path: str, progress_callback=None) -> str:
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            return self._parse_pdf(file_path, progress_callback)
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            return self._parse_image(file_path)
        elif file_ext in ['.doc', '.docx']:
            return self._parse_docx(file_path)
        elif file_ext == '.txt':
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")

    def _parse_pdf(self, file_path: str, progress_callback=None) -> str:
        try:
            text = self._parse_pdf_with_fitz(file_path, progress_callback)
            if text and len(text.strip()) > 100:
                chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                if chinese_count > len(text) * 0.1:
                    return self._clean_text(text)
            if text and text.strip():
                return self._clean_text(text)
        except Exception:
            pass

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            pypdf_text = ""
            has_text = False
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                except Exception:
                    page_text = ""
                if page_text and page_text.strip():
                    has_text = True
                    pypdf_text += page_text + "\n\n"
            if has_text and len(pypdf_text.strip()) > 10:
                return self._clean_text(pypdf_text)
        except Exception:
            pass

        if progress_callback:
            progress_callback(10, "检测为扫描版PDF，开始OCR识别...")
        return self._parse_scanned_pdf(file_path, progress_callback)

    def _parse_pdf_with_fitz(self, file_path: str, progress_callback=None) -> str:
        try:
            import fitz
        except Exception:
            return ""
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            text = ""
            for page_num, page in enumerate(doc):
                try:
                    page_text = page.get_text()
                except Exception:
                    page_text = ""
                if page_text and page_text.strip():
                    text += page_text + "\n\n"
                if progress_callback and total_pages > 0:
                    if (page_num + 1) % 5 == 0 or page_num == total_pages - 1:
                        progress_callback(int(5 + (page_num + 1) / total_pages * 15),
                                          f"正在解析第 {page_num + 1}/{total_pages} 页...")
            doc.close()
            return text
        except Exception:
            return ""

    def _parse_scanned_pdf(self, file_path: str, progress_callback=None) -> str:
        try:
            import fitz
        except Exception:
            return ""
        if not self.ocr_engine:
            return ""
        text = ""
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7))
                img_bytes = pix.tobytes("png")
                page_text = self._parse_image_bytes(img_bytes)
                if page_text and page_text.strip():
                    text += page_text + "\n\n"
                if progress_callback:
                    ocr_progress = int(10 + (page_num + 1) / total_pages * 10)
                    progress_callback(ocr_progress, f"OCR识别中... 第 {page_num + 1}/{total_pages} 页")
            return self._clean_text(text)
        except Exception:
            return ""

    def _parse_image(self, file_path: str) -> str:
        if not self.ocr_engine:
            return ""
        try:
            result, _ = self.ocr_engine(file_path)
            if not result:
                return ""
            return self._process_ocr_result(result)
        except TypeError:
            try:
                result = self.ocr_engine.ocr(file_path, cls=True)
                if not result or not result[0]:
                    return ""
                return self._process_ocr_result(result[0])
            except Exception:
                return ""
        except Exception:
            return ""

    def _parse_image_bytes(self, img_bytes: bytes) -> str:
        if not self.ocr_engine:
            return ""
        try:
            import numpy as np
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes))
            img_np = np.array(img)
            result, _ = self.ocr_engine(img_np)
            if not result:
                return ""
            return self._process_ocr_result(result)
        except TypeError:
            try:
                result = self.ocr_engine.ocr(img_np, cls=True)
                if not result or not result[0]:
                    return ""
                return self._process_ocr_result(result[0])
            except Exception:
                return ""
        except Exception:
            return ""

    def _process_ocr_result(self, result) -> str:
        if not result:
            return ""

        filtered_results = []
        for item in result:
            # rapidocr: [box, (text, score)] ; 兼容 [box, text, score]
            if len(item) >= 2:
                box = item[0]
                if isinstance(item[1], (list, tuple)):
                    text = item[1][0]
                    confidence = item[1][1] if len(item[1]) > 1 else 0.5
                else:
                    text = item[1]
                    confidence = item[2] if len(item) > 2 else 0.5
                if confidence > 0.45:
                    filtered_results.append({
                        'box': box,
                        'text': text,
                        'confidence': confidence
                    })

        filtered_results.sort(key=lambda x: (x['box'][0][1], x['box'][0][0]))

        texts = [item['text'] for item in filtered_results]
        raw_text = "\n".join(texts)
        return self._clean_text(raw_text)

    def _parse_docx(self, file_path: str) -> str:
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n\n"
            return self._clean_text(text)
        except Exception:
            return ""

    def _parse_txt(self, file_path: str) -> str:
        for encoding in ['utf-8', 'gbk']:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    text = f.read()
                if text.strip():
                    return self._clean_text(text)
            except Exception:
                continue
        return ""

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace('\r\n', '\n')
        text = text.replace('\u3000', ' ')

        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                if cleaned_lines and cleaned_lines[-1] != '':
                    cleaned_lines.append('')
                continue
            if self._is_invalid_line(line):
                continue
            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _is_invalid_line(self, line: str) -> bool:
        if len(line) <= 1:
            return True
        if re.match(r'^[\s\W]{3,}$', line):
            return True
        if re.match(r'^[\d]{8,}$', line):
            return True
        if re.match(r'^[a-zA-Z]{15,}$', line):
            return True

        invalid_keywords = ['undefined', 'null', 'NaN', 'error', 'failed']
        line_lower = line.lower()
        for kw in invalid_keywords:
            if kw in line_lower:
                return True

        char_count = sum(1 for c in line if '\u4e00' <= c <= '\u9fff')
        eng_count = sum(1 for c in line if c.isalpha())
        num_count = sum(1 for c in line if c.isdigit())
        math_symbols = sum(1 for c in line if c in '=+-*/()[]{}|<>^_∫∑∏√∞≈≠≤≥∈∉⊂⊃∪∩')
        total = len(line)

        if total > 0 and char_count == 0 and eng_count == 0 and math_symbols == 0:
            return True
        if total >= 8 and char_count == 0 and math_symbols == 0 and num_count >= total * 0.9:
            return True

        return False


ocr_parser = OCRParser()