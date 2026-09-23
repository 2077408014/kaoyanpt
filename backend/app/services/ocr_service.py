from typing import Dict
import threading
import os
import hashlib
import time

from ..utils.ocr_text import format_text, classify_subject, detect_knowledge_point


class OCRService:
    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._cache: Dict[str, dict] = {}
        self._cache_timeout = 300
        self._paddle_ocr = None
        self._use_paddle = True

    def _try_init_paddle(self):
        try:
            from .paddleocr_service import paddle_ocr_service
            if paddle_ocr_service.is_available():
                self._paddle_ocr = paddle_ocr_service
                self._use_paddle = True
                print("[OCR] 已启用 PaddleOCR 引擎")
                return True
            else:
                print(f"[OCR] PaddleOCR不可用: {paddle_ocr_service.get_init_error()}")
        except Exception as e:
            print(f"[OCR] 加载PaddleOCR失败: {e}")
        self._use_paddle = False
        return False

    @property
    def engine(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    if self._use_paddle and self._paddle_ocr is None:
                        self._try_init_paddle()

                    if self._paddle_ocr:
                        self._engine = self._paddle_ocr
                    else:
                        from rapidocr_onnxruntime import RapidOCR
                        self._engine = RapidOCR()
                        print("[OCR] 已启用 RapidOCR 引擎")
        return self._engine

    @property
    def current_engine_name(self) -> str:
        if self._use_paddle and self._paddle_ocr:
            return "paddleocr"
        return "rapidocr"

    def reset_engine(self):
        with self._lock:
            self._engine = None
            self._paddle_ocr = None

    def _clean_cache(self):
        now = time.time()
        to_remove = [key for key, value in self._cache.items()
                     if now - value['timestamp'] > self._cache_timeout]
        for key in to_remove:
            del self._cache[key]

    def _get_cache_key(self, image_path: str) -> str:
        file_stat = os.stat(image_path)
        return hashlib.md5(
            f"{image_path}_{file_stat.st_mtime}_{file_stat.st_size}".encode()
        ).hexdigest()

    def extract_text(self, image_path: str) -> str:
        try:
            file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
            print(f"[OCR] 开始识别图片: {image_path}, 文件大小: {file_size} bytes")

            start_time = time.time()

            if self._use_paddle and self._paddle_ocr:
                result = self._paddle_ocr.extract_text(image_path)
                elapsed = time.time() - start_time
                print(f"[OCR] PaddleOCR引擎耗时: {elapsed:.2f}s")
                return result

            result, _ = self.engine(image_path)
            elapsed = time.time() - start_time
            print(f"[OCR] RapidOCR引擎耗时: {elapsed:.2f}s")

            if not result:
                print("[OCR] 未识别到任何内容")
                return ""

            filtered_results = [
                item for item in result
                if len(item) >= 3 and item[2] > 0.55
            ]
            print(f"[OCR] 过滤后识别结果数量: {len(filtered_results)}")

            filtered_results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))

            texts = [item[1] for item in filtered_results]

            raw_text = "\n".join(texts)
            print(f"[OCR] 原始文本长度: {len(raw_text)}")

            formatted_text = format_text(raw_text)
            print(f"[OCR] 格式化后文本长度: {len(formatted_text)}, "
                  f"前150字符: {formatted_text[:150]}...")

            return formatted_text
        except Exception as e:
            print(f"[OCR] 识别失败: {e}")
            return ""

    def classify_subject(self, text: str):
        return classify_subject(text)

    def detect_knowledge_point(self, text: str, subject=None):
        return detect_knowledge_point(text, subject)

    def recognize(self, image_path: str) -> dict:
        full_path = str(image_path)

        self._clean_cache()
        cache_key = self._get_cache_key(full_path)

        if cache_key in self._cache:
            print(f"[OCR] 命中缓存: {cache_key}")
            return self._cache[cache_key]['data']

        raw_text = self.extract_text(full_path)

        if not raw_text:
            result = {
                "question_text": None,
                "subject": None,
                "knowledge_point": None,
                "confidence": 0.0,
                "raw_text": ""
            }
            self._cache[cache_key] = {"data": result, "timestamp": time.time()}
            return result

        subject, confidence = self.classify_subject(raw_text)
        knowledge_point = self.detect_knowledge_point(raw_text, subject)

        result = {
            "question_text": raw_text[:2000],
            "subject": subject,
            "knowledge_point": knowledge_point,
            "confidence": confidence,
            "raw_text": raw_text
        }

        self._cache[cache_key] = {"data": result, "timestamp": time.time()}
        return result

    def recognize_politics(self, image_path: str) -> dict:
        full_path = str(image_path)

        formatted_text = self.extract_text(full_path)

        if not formatted_text:
            return {"content": "", "confidence": 0.0}

        confidence = 0.85 if len(formatted_text) > 50 else 0.7
        if len(formatted_text) < 10:
            confidence = 0.3

        return {"content": formatted_text, "confidence": confidence}


ocr_service = OCRService()