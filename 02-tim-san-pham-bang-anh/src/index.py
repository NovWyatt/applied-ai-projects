"""Chỉ mục vector của danh mục, lưu bằng Qdrant chạy cục bộ (không cần server).

Mỗi sản phẩm là một điểm, mang nhiều vector có tên (mỗi mô hình một vector), để
so sánh các mô hình trên cùng một chỉ mục và kết hợp điểm của chúng.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models

PROJECT_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = PROJECT_DIR / "qdrant_storage"
COLLECTION = "san_pham"


@dataclass
class Hit:
    sku: str
    score: float
    payload: dict


class CatalogIndex:
    def __init__(self, path: Path | None = INDEX_DIR):
        # path=None: chỉ giữ trong bộ nhớ (dùng cho test).
        # Lưu ý: chế độ thư mục khóa thư mục lại, mỗi lúc chỉ một tiến trình mở được.
        self.client = QdrantClient(path=str(path)) if path else QdrantClient(location=":memory:")

    def build(self, vectors: dict[str, np.ndarray], payloads: list[dict]) -> None:
        """Tạo lại chỉ mục. vectors: tên mô hình -> ma trận (số sản phẩm x số chiều)."""
        if self.client.collection_exists(COLLECTION):
            self.client.delete_collection(COLLECTION)
        self.client.create_collection(COLLECTION, vectors_config={
            name: models.VectorParams(size=matrix.shape[1], distance=models.Distance.COSINE)
            for name, matrix in vectors.items()
        })
        self.client.upsert(COLLECTION, points=[
            models.PointStruct(id=i, payload=payload,
                               vector={name: matrix[i].tolist() for name, matrix in vectors.items()})
            for i, payload in enumerate(payloads)
        ])

    def search(self, using: str, vector: np.ndarray, k: int = 5, category: str | None = None) -> list[Hit]:
        """k sản phẩm gần nhất theo vector `using`; có thể lọc theo loại sản phẩm."""
        query_filter = None
        if category:
            query_filter = models.Filter(must=[
                models.FieldCondition(key="loai", match=models.MatchValue(value=category))])
        points = self.client.query_points(COLLECTION, query=vector.tolist(), using=using, limit=k,
                                          query_filter=query_filter, with_payload=True).points
        return [Hit(sku=p.payload["sku"], score=p.score, payload=p.payload) for p in points]

    def vectors_of(self, using: str, skus: list[str]) -> dict[str, np.ndarray]:
        """Lấy lại vector đã lưu của các sản phẩm (để chấm điểm thêm theo mô hình khác)."""
        points, _ = self.client.scroll(COLLECTION, limit=10_000, with_payload=True, with_vectors=[using],
                                       scroll_filter=models.Filter(must=[
                                           models.FieldCondition(key="sku", match=models.MatchAny(any=skus))]))
        return {p.payload["sku"]: np.asarray(p.vector[using]) for p in points}

    def close(self) -> None:
        self.client.close()
