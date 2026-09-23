from typing import Optional, Dict
import threading
import os
import hashlib
import time

from ..utils.ocr_text import format_text, classify_subject, detect_knowledge_point


class PaddleOCRService:
    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._cache: Dict[str, dict] = {}
        self._cache_timeout = 300
        self._initialized = False
        self._init_error = None

    def _initialize_engine(self):
        try:
            from paddleocr import PaddleOCR
            self._engine = PaddleOCR(
                lang='ch',
                use_gpu=False
            )
            self._initialized = True
            self._init_error = None
            print("[PaddleOCR] 引擎初始化成功")
        except Exception as e:
            self._init_error = str(e)
            self._initialized = False
            print(f"[PaddleOCR] 引擎初始化失败: {e}")

    @property
    def engine(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._initialize_engine()
        return self._engine

    def is_available(self) -> bool:
        return self._initialized or (self._engine is not None)

    def get_init_error(self) -> Optional[str]:
        return self._init_error

    def reset_engine(self):
        with self._lock:
            self._engine = None
            self._initialized = False
            self._init_error = None

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
        if not self.is_available():
            print(f"[PaddleOCR] 引擎不可用: {self._init_error}")
            return ""

        try:
            file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
            print(f"[PaddleOCR] 开始识别图片: {image_path}, 文件大小: {file_size} bytes")

            start_time = time.time()
            result = self.engine.ocr(image_path, cls=True)
            elapsed = time.time() - start_time
            print(f"[PaddleOCR] OCR引擎耗时: {elapsed:.2f}s")

            if not result or not result[0]:
                print("[PaddleOCR] 未识别到任何内容")
                return ""

            filtered_results = []
            for page in result:
                for item in page:
                    if len(item) >= 2:
                        text = item[1][0]
                        confidence = item[1][1] if len(item[1]) > 1 else 0.5
                        if confidence > 0.55:
                            filtered_results.append((item[0], text, confidence))

            print(f"[PaddleOCR] 过滤后识别结果数量: {len(filtered_results)}")

            filtered_results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))

            texts = [item[1] for item in filtered_results]
            raw_text = "\n".join(texts)
            print(f"[PaddleOCR] 原始文本长度: {len(raw_text)}")

            formatted_text = format_text(raw_text)
            print(f"[PaddleOCR] 格式化后文本长度: {len(formatted_text)}, "
                  f"前150字符: {formatted_text[:150]}...")

            return formatted_text
        except Exception as e:
            print(f"[PaddleOCR] 识别失败: {e}")
            return ""

    def classify_subject(self, text: str):
        return classify_subject(text)

    def detect_knowledge_point(self, text: str, subject: Optional[str]):
        return detect_knowledge_point(text, subject)

    def recognize(self, image_path: str) -> dict:
        full_path = str(image_path)

        self._clean_cache()
        cache_key = self._get_cache_key(full_path)

        if cache_key in self._cache:
            print(f"[PaddleOCR] 命中缓存: {cache_key}")
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


paddle_ocr_service = PaddleOCRService()