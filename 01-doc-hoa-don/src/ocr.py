"""Đọc chữ trên ảnh hóa đơn bằng PaddleOCR và gom thành từng dòng."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent
# Mô hình (~30 MB) tải về models/ của dự án thay vì ~/.paddlex trong thư mục người dùng.
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PROJECT_DIR / "models" / "paddlex"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Bản small: ~3 giây/ảnh trên CPU, giữ dấu tiếng Việt ngang bản medium (~20 giây/ảnh)
# và tốt hơn hẳn mô hình latin_PP-OCRv5 (rơi mất cả chữ cái có dấu chồng như "ổ", "ộ").
DET_MODEL = "PP-OCRv6_small_det"
REC_MODEL = "PP-OCRv6_small_rec"


@dataclass
class OcrLine:
    text: str
    score: float  # độ tin cậy thấp nhất trong các đoạn chữ của dòng


@lru_cache(maxsize=1)
def get_engine():
    from paddleocr import PaddleOCR  # nhập muộn: nặng, và phần tách trường không cần tới

    return PaddleOCR(
        text_detection_model_name=DET_MODEL,
        text_recognition_model_name=REC_MODEL,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        # oneDNN của Paddle 3.3 báo "ConvertPirAttribute2RuntimeAttribute not support" trên CPU Windows.
        enable_mkldnn=False,
    )


def read_lines(image: str | Path | np.ndarray) -> list[OcrLine]:
    """Đọc ảnh (đường dẫn, hoặc mảng numpy theo thứ tự màu BGR như OpenCV)."""
    image = str(image) if isinstance(image, Path) else image
    result = get_engine().predict(image)[0]
    return group_lines(result["rec_texts"], result["rec_scores"], result["rec_polys"])


def group_lines(texts: list[str], scores: list[float], polys: list) -> list[OcrLine]:
    """Gom các đoạn chữ cùng hàng (nhãn bên trái, số tiền bên phải) thành một dòng.

    Ảnh chụp thường hơi nghiêng: đầu dòng và cuối dòng lệch nhau cả chục pixel,
    đủ để số tiền "nhảy" sang dòng bên cạnh. Vì vậy trước khi so độ cao, xoay
    tâm các đoạn chữ ngược lại theo góc nghiêng trung vị của chúng.
    """
    if not texts:
        return []
    polys = [np.asarray(p, dtype=float) for p in polys]  # 4 góc: trên-trái, trên-phải, dưới-phải, dưới-trái
    angle = float(np.median([np.arctan2(p[1, 1] - p[0, 1], p[1, 0] - p[0, 0]) for p in polys]))
    cos, sin = np.cos(angle), np.sin(angle)

    pieces = []
    for text, score, poly in zip(texts, scores, polys):
        cx, cy = poly.mean(axis=0)
        pieces.append({"y": cy * cos - cx * sin, "x": cx * cos + cy * sin, "height": np.linalg.norm(poly[3] - poly[0]),
                       "text": text, "score": float(score)})
    pieces.sort(key=lambda p: p["y"])
    tolerance = 0.5 * float(np.median([p["height"] for p in pieces]))

    rows: list[list[dict]] = [[pieces[0]]]
    for piece in pieces[1:]:
        row_y = np.mean([p["y"] for p in rows[-1]])
        if abs(piece["y"] - row_y) <= tolerance:
            rows[-1].append(piece)
        else:
            rows.append([piece])

    lines = []
    for row in rows:
        row.sort(key=lambda p: p["x"])
        lines.append(OcrLine(text="  ".join(p["text"] for p in row), score=min(p["score"] for p in row)))
    return lines
