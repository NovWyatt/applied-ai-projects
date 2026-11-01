"""Biến ảnh thành vector đã chuẩn hóa (độ dài 1), để tích vô hướng là độ tương đồng cosine."""

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

PROJECT_DIR = Path(__file__).resolve().parent.parent
# Mô hình Hugging Face tải về models/ của dự án thay vì ~/.cache trong thư mục người dùng.
os.environ.setdefault("HF_HOME", str(PROJECT_DIR / "models" / "huggingface"))
# Nhánh main của CLIP chỉ có pytorch_model.bin. Khi nạp file .bin, transformers chạy ngầm một luồng
# tải thêm bản safetensors (605 MB) từ PR chuyển đổi "cho lần sau", nhưng lần sau vẫn nạp .bin.
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")


def pad_to_square(image: Image.Image) -> Image.Image:
    """Thêm viền cho vuông thay vì cắt giữa.

    Bộ tiền xử lý của DINOv2/CLIP cắt lấy phần giữa ảnh. Ảnh khách chụp khổ 4:3
    với sản phẩm đặt lệch có thể bị cắt mất một phần sản phẩm.
    """
    image = image.convert("RGB")
    side = max(image.size)
    border_color = tuple(int(c) for c in np.asarray(image).reshape(-1, 3).mean(axis=0))
    return ImageOps.pad(image, (side, side), color=border_color)


def normalize(matrix: np.ndarray) -> np.ndarray:
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True).clip(min=1e-12)


class ColorHistogram:
    """Mốc so sánh không dùng học máy: phân bố màu HSV của cả ảnh."""

    name = "mau"
    label = "Biểu đồ màu HSV (không học máy)"
    bins = (12, 4, 4)

    def embed(self, images: list[Image.Image]) -> np.ndarray:
        rows = []
        for image in images:
            hsv = np.asarray(image.convert("RGB").resize((96, 96)).convert("HSV")).reshape(-1, 3)
            hist, _ = np.histogramdd(hsv, bins=self.bins, range=[(0, 256)] * 3)
            # Căn bậc hai trước khi chuẩn hóa: cosine khi đó là hệ số Bhattacharyya giữa hai phân bố.
            rows.append(np.sqrt(hist.ravel() / hist.sum()))
        return normalize(np.array(rows))


class HuggingFaceEmbedder:
    def __init__(self, name: str, label: str, model_id: str):
        import torch
        from transformers import AutoImageProcessor, AutoModel

        self.name, self.label, self.model_id = name, label, model_id
        self._torch = torch
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).eval()

    def embed(self, images: list[Image.Image], batch_size: int = 16) -> np.ndarray:
        chunks = []
        for start in range(0, len(images), batch_size):
            batch = [pad_to_square(image) for image in images[start:start + batch_size]]
            inputs = self.processor(images=batch, return_tensors="pt")
            with self._torch.inference_mode():
                if hasattr(self.model, "get_image_features"):  # CLIP: vector trong không gian chung ảnh-chữ
                    features = self.model.get_image_features(pixel_values=inputs["pixel_values"])
                    features = getattr(features, "pooler_output", features)
                else:  # DINOv2: token CLS sau lớp chuẩn hóa
                    features = self.model(**inputs).pooler_output
            chunks.append(features.numpy())
        return normalize(np.concatenate(chunks))


MODELS = {
    "mau": lambda: ColorHistogram(),
    "dinov2": lambda: HuggingFaceEmbedder("dinov2", "DINOv2-small (tự học từ ảnh)", "facebook/dinov2-small"),
    "clip": lambda: HuggingFaceEmbedder("clip", "CLIP ViT-B/32 (học từ ảnh và chú thích)",
                                        "openai/clip-vit-base-patch32"),
}


@lru_cache(maxsize=None)
def get_embedder(name: str):
    return MODELS[name]()
