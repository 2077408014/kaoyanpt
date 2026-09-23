import base64
import uuid
import warnings
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

try:
    import cv2  # noqa: F401
    _HAS_CV2 = True
except Exception as e:
    warnings.warn(f"cv2 不可用 ({e})，学习监督功能将受限")
    _HAS_CV2 = False
    cv2 = None

try:
    from ultralytics import YOLO  # noqa: F401
    _HAS_YOLO = True
except Exception as e:
    warnings.warn(f"ultralytics 不可用 ({e})，学习监督功能将受限")
    _HAS_YOLO = False
    YOLO = None

from ..models.supervision import StudySupervisionRecord


SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

STATUS_COLORS = {
    "focused": (0, 255, 0),
    "distracted": (0, 0, 255),
    "absent": (0, 165, 255),
    "unknown": (128, 128, 128),
}

STATUS_LABELS = {
    "focused": "专注",
    "distracted": "走神",
    "absent": "离开",
    "unknown": "未知",
}


class SupervisionService:
    _pose_model = None

    @property
    def cv2(self):
        return cv2 if _HAS_CV2 else None

    @property
    def pose_model(self):
        if not _HAS_YOLO or YOLO is None:
            return None
        if self._pose_model is None:
            self._pose_model = YOLO("yolov8n-pose.pt", verbose=False)
        return self._pose_model

    def is_available(self) -> bool:
        return _HAS_CV2 and _HAS_YOLO

    def detect_status(self, image_data: bytes) -> dict:
        try:
            _cv2 = self.cv2
            if _cv2 is None:
                return {
                    "status": "unknown",
                    "confidence": 0.0,
                    "face_count": 0,
                    "overlay_base64": None,
                }

            np_arr = np.frombuffer(image_data, np.uint8)
            image = _cv2.imdecode(np_arr, _cv2.IMREAD_COLOR)
            if image is None:
                return {
                    "status": "unknown",
                    "confidence": 0.0,
                    "face_count": 0,
                    "overlay_base64": None,
                }

            h, w = image.shape[:2]

            if self.pose_model is None:
                return {
                    "status": "unknown",
                    "confidence": 0.0,
                    "face_count": 0,
                    "overlay_base64": None,
                }

            results = self.pose_model(image, verbose=False)

            persons = self._extract_persons(results, w, h)
            face_count = len(persons)

            if face_count == 0:
                overlay = self._draw_overlay(image, [], "absent")
                return {
                    "status": "absent",
                    "confidence": 1.0,
                    "face_count": 0,
                    "overlay_base64": overlay,
                }

            if face_count >= 2:
                overlay = self._draw_overlay(image, persons, "distracted")
                return {
                    "status": "distracted",
                    "confidence": 1.0,
                    "face_count": face_count,
                    "overlay_base64": overlay,
                }

            status, confidence = self._classify_pose(persons[0], w, h)
            overlay = self._draw_overlay(image, persons, status)
            return {
                "status": status,
                "confidence": confidence,
                "face_count": 1,
                "overlay_base64": overlay,
            }

        except Exception:
            return {
                "status": "unknown",
                "confidence": 0.0,
                "face_count": 0,
                "overlay_base64": None,
            }

    def _extract_persons(self, results, img_w: int, img_h: int) -> list:
        persons = []
        for result in results:
            if result.keypoints is None:
                continue
            keypoints = result.keypoints.xy.cpu().numpy()
            confs = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None
            for idx, person_kpts in enumerate(keypoints):
                pts = person_kpts[:17].astype(int).tolist()
                cvals = confs[idx][:17].tolist() if confs is not None else [1.0] * 17
                persons.append({"keypoints": pts, "confidences": cvals})
        return persons

    def _keypoint(self, person: dict, idx: int) -> Optional[Tuple[int, int]]:
        pt = person["keypoints"][idx]
        conf = person["confidences"][idx]
        if conf < 0.3:
            return None
        if pt[0] <= 0 and pt[1] <= 0:
            return None
        return tuple(pt)

    def _classify_pose(self, person: dict, img_w: int, img_h: int) -> Tuple[str, float]:
        nose = self._keypoint(person, 0)
        left_eye = self._keypoint(person, 1)
        right_eye = self._keypoint(person, 2)
        left_shoulder = self._keypoint(person, 5)
        right_shoulder = self._keypoint(person, 6)
        left_elbow = self._keypoint(person, 7)
        right_elbow = self._keypoint(person, 8)
        left_wrist = self._keypoint(person, 9)
        right_wrist = self._keypoint(person, 10)

        face_visible = nose is not None and (left_eye is not None or right_eye is not None)
        if not face_visible:
            return "distracted", 0.8

        face_y = nose[1] if nose else (left_eye[1] if left_eye else right_eye[1])
        shoulder_y = None
        if left_shoulder and right_shoulder:
            shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        elif left_shoulder:
            shoulder_y = left_shoulder[1]
        elif right_shoulder:
            shoulder_y = right_shoulder[1]

        if shoulder_y is not None and face_y > shoulder_y - img_h * 0.05:
            return "distracted", 0.75

        def near_face(pt) -> bool:
            if pt is None or nose is None:
                return False
            dx = abs(pt[0] - nose[0]) / img_w
            dy = abs(pt[1] - nose[1]) / img_h
            return dx < 0.45 and dy < 0.35

        def hand_raised(wrist, elbow) -> bool:
            if wrist is None or elbow is None:
                return False
            return wrist[1] < elbow[1] + img_h * 0.05

        phone_like = False
        for wrist, elbow in ((left_wrist, left_elbow), (right_wrist, right_elbow)):
            if wrist and near_face(wrist):
                if hand_raised(wrist, elbow):
                    phone_like = True
                    break
                if nose and wrist[1] < nose[1] + img_h * 0.25:
                    phone_like = True
                    break

        hands_down = False
        if left_wrist and right_wrist and left_elbow and right_elbow:
            avg_wrist_y = (left_wrist[1] + right_wrist[1]) / 2
            avg_elbow_y = (left_elbow[1] + right_elbow[1]) / 2
            if avg_wrist_y > avg_elbow_y + img_h * 0.02:
                hands_down = True

        if phone_like:
            return "distracted", 0.9
        if hands_down:
            return "focused", 0.85

        single_hand_up = False
        for wrist, elbow in ((left_wrist, left_elbow), (right_wrist, right_elbow)):
            if hand_raised(wrist, elbow):
                single_hand_up = True
                break
        if single_hand_up:
            return "distracted", 0.65

        return "focused", 0.6

    def _draw_overlay(self, image, persons: list, status: str) -> Optional[str]:
        _cv2 = self.cv2
        if _cv2 is None:
            return None

        overlay = image.copy()
        color = STATUS_COLORS.get(status, (128, 128, 128))
        label = STATUS_LABELS.get(status, "未知")

        for person in persons:
            kpts = person["keypoints"]
            for a, b in SKELETON:
                pa = kpts[a]
                pb = kpts[b]
                if (pa[0] > 0 or pa[1] > 0) and (pb[0] > 0 or pb[1] > 0):
                    _cv2.line(overlay, tuple(pa), tuple(pb), color, 2, _cv2.LINE_AA)
            for idx, pt in enumerate(kpts):
                if pt[0] > 0 or pt[1] > 0:
                    _cv2.circle(overlay, tuple(pt), 4, (255, 255, 255), -1)
                    _cv2.circle(overlay, tuple(pt), 3, color, -1)

        self._draw_chinese_label(overlay, f"状态: {label}", color)

        _, buf = _cv2.imencode(".jpg", overlay)
        return base64.b64encode(buf).decode("utf-8")

    def _find_chinese_font(self) -> Optional[str]:
        import os
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\simkai.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _draw_chinese_label(self, image, text: str, color_bgr: tuple) -> None:
        _cv2 = self.cv2
        if _cv2 is None:
            return

        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception:
            _cv2.putText(image, "Status", (10, 30), _cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_bgr, 2)
            return

        font_path = self._find_chinese_font()
        h, w = image.shape[:2]
        font_size = max(20, min(w, h) // 18)
        try:
            font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        pil_img = Image.fromarray(_cv2.cvtColor(image, _cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 10
        draw.rectangle((pad, pad, pad + tw + pad * 2, pad + th + pad * 2), fill=(0, 0, 0))
        draw.text((pad * 2, pad), text, font=font, fill=color_rgb)

        image[:, :] = _cv2.cvtColor(np.array(pil_img), _cv2.COLOR_RGB2BGR)

    def start_session(self, user_id: int) -> str:
        return str(uuid.uuid4())

    def record_check(self, db: Session, user_id: int, session_id: str, result: dict) -> StudySupervisionRecord:
        record = StudySupervisionRecord(
            user_id=user_id,
            session_id=session_id,
            status=result["status"],
            confidence=result["confidence"],
            face_count=result["face_count"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_session_stats(self, db: Session, user_id: int, session_id: str) -> dict:
        records = (
            db.query(StudySupervisionRecord)
            .filter(
                StudySupervisionRecord.user_id == user_id,
                StudySupervisionRecord.session_id == session_id,
            )
            .all()
        )

        total = len(records)
        focused = sum(1 for r in records if r.status == "focused")
        distracted = sum(1 for r in records if r.status == "distracted")
        absent = sum(1 for r in records if r.status == "absent")
        unknown = sum(1 for r in records if r.status == "unknown")

        duration = 0
        if records:
            first = min(r.created_at for r in records if r.created_at)
            last = max(r.created_at for r in records if r.created_at)
            if last and first:
                duration = int((last - first).total_seconds())

        focus_rate = focused / total * 100 if total > 0 else 0.0

        return {
            "session_id": session_id,
            "total_checks": total,
            "focused_count": focused,
            "distracted_count": distracted,
            "absent_count": absent,
            "unknown_count": unknown,
            "focus_rate": round(focus_rate, 1),
            "duration_seconds": duration,
        }

    def get_daily_stats(self, db: Session, user_id: int, target_date: date) -> dict:
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

        records = (
            db.query(StudySupervisionRecord)
            .filter(
                StudySupervisionRecord.user_id == user_id,
                StudySupervisionRecord.created_at >= start,
                StudySupervisionRecord.created_at < end,
            )
            .all()
        )

        total = len(records)
        focused = sum(1 for r in records if r.status == "focused")

        focused_seconds = focused * 15

        focus_rate = focused / total * 100 if total > 0 else 0.0

        return {
            "date": target_date.isoformat(),
            "total_focused_seconds": focused_seconds,
            "total_checks": total,
            "focus_rate": round(focus_rate, 1),
        }


supervision_service = SupervisionService()