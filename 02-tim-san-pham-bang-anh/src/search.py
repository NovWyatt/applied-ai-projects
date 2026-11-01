"""Tìm sản phẩm bằng ảnh, hai bước:

1. DINOv2 lấy N_CANDIDATES sản phẩm gần nhất từ Qdrant. DINOv2 nhận dáng rất tốt
   (đúng loại 96%) nhưng hay nhầm màu.
2. Chấm lại các ứng viên, kết hợp thêm độ giống theo CLIP, mô hình giữ màu tốt hơn.

Chạy từ thư mục 02-tim-san-pham-bang-anh (sau `python -m src.build_index`):

    python -m src.search data/queries/SP29_khach.jpg
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from src.embedders import get_embedder
from src.index import CatalogIndex

N_CANDIDATES = 10
# Cộng thẳng cosine, không chuẩn hóa: độ trải điểm trong 10 ứng viên của hai mô hình
# tương đương (DINOv2 0.17, CLIP 0.15) nên 50/50 đã cân. Đo trên 48 ảnh khách chụp:
# đúng @1 85%, so với 79% khi chuẩn hóa min-max và 73% khi dùng thứ hạng (RRF).
DINO_WEIGHT = 0.5


@dataclass
class Candidate:
    sku: str
    payload: dict  # ten, loai, mau, hoa_van, file
    dino: float    # cosine theo DINOv2, giỏi nhận dáng và hoa văn
    clip: float    # cosine theo CLIP, giữ màu tốt hơn


def rerank(candidates: list[Candidate]) -> list[tuple[Candidate, float]]:
    """Sắp xếp lại ứng viên theo điểm kết hợp, cao nhất trước.

    candidates đến theo thứ tự điểm DINOv2 giảm dần. Trả về [(ứng viên, điểm kết hợp), ...].
    """
    # Giữ nguyên độ lớn của điểm: khi DINOv2 chắc chắn (cách biệt lớn), CLIP hơi nghiêng
    # ngược lại không lật được; khi DINOv2 gần như hòa, CLIP quyết định màu.
    # Min-max sẽ kéo cách biệt 0.01 thành 0..1, còn RRF bỏ hẳn độ lớn.
    scored = [(c, DINO_WEIGHT * c.dino + (1 - DINO_WEIGHT) * c.clip) for c in candidates]
    return sorted(scored, key=lambda pair: pair[1], reverse=True)


class ProductSearch:
    def __init__(self, index: CatalogIndex):
        self.index = index
        self.dino = get_embedder("dinov2")
        self.clip = get_embedder("clip")

    def candidates(self, image: Image.Image, n: int = N_CANDIDATES, category: str | None = None) -> list[Candidate]:
        dino_vector = self.dino.embed([image])[0]
        clip_vector = self.clip.embed([image])[0]
        hits = self.index.search("dinov2", dino_vector, k=n, category=category)
        clip_vectors = self.index.vectors_of("clip", [hit.sku for hit in hits])
        return [Candidate(hit.sku, hit.payload, hit.score, float(clip_vectors[hit.sku] @ clip_vector))
                for hit in hits]

    def search(self, image: Image.Image, k: int = 5, category: str | None = None) -> list[tuple[Candidate, float]]:
        """category: chỉ tìm trong một loại sản phẩm (bộ lọc payload của Qdrant)."""
        return rerank(self.candidates(image, category=category))[:k]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Tìm sản phẩm giống ảnh.")
    parser.add_argument("image", type=Path)
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    index = CatalogIndex()
    with Image.open(args.image) as image:
        results = ProductSearch(index).search(image.convert("RGB"), k=args.k)
    index.close()
    for rank, (candidate, score) in enumerate(results, 1):
        print(f"{rank}. {candidate.payload['ten']:32} điểm {score:.3f}   "
              f"(DINOv2 {candidate.dino:.3f}, CLIP {candidate.clip:.3f})   {candidate.sku}")


if __name__ == "__main__":
    main()
