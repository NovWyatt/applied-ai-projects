"""Đánh giá: tìm bằng ảnh khách chụp, xem sản phẩm đúng có đứng đầu không.

Chạy sau `python -m src.build_index`:

    python -m src.evaluate
"""

import sys
import time
from collections.abc import Callable

import numpy as np
import pandas as pd

from src.data import load_queries, open_image
from src.embedders import MODELS, get_embedder
from src.index import CatalogIndex, Hit
from src.search import Candidate, ProductSearch, rerank

K = 5
Fusion = Callable[[list[Candidate]], list[tuple[Candidate, float]]]


def ranked(scored: list[tuple[Candidate, float]]) -> list[tuple[Candidate, float]]:
    return sorted(scored, key=lambda pair: pair[1], reverse=True)


def weighted_raw(w_dino: float) -> Fusion:
    return lambda cands: ranked([(c, w_dino * c.dino + (1 - w_dino) * c.clip) for c in cands])


def weighted_minmax(w_dino: float) -> Fusion:
    """Đưa điểm từng mô hình về 0..1 trong danh sách ứng viên rồi mới cộng."""
    def fuse(cands):
        scale = lambda xs: (np.array(xs) - min(xs)) / max(max(xs) - min(xs), 1e-9)
        dino, clip = scale([c.dino for c in cands]), scale([c.clip for c in cands])
        return ranked([(c, w_dino * d + (1 - w_dino) * k) for c, d, k in zip(cands, dino, clip)])
    return fuse


def reciprocal_rank(k: int = 60) -> Fusion:
    """RRF: chỉ dùng thứ hạng trong từng mô hình, bỏ qua độ lớn của điểm."""
    def fuse(cands):
        dino_rank = {c.sku: r for r, c in enumerate(sorted(cands, key=lambda c: -c.dino))}
        clip_rank = {c.sku: r for r, c in enumerate(sorted(cands, key=lambda c: -c.clip))}
        return ranked([(c, 1 / (k + dino_rank[c.sku]) + 1 / (k + clip_rank[c.sku])) for c in cands])
    return fuse


FUSIONS: list[tuple[str, Fusion]] = [
    ("Chỉ DINOv2 (không chấm lại)", lambda cands: [(c, c.dino) for c in cands]),
    ("Chỉ CLIP trong 10 ứng viên", lambda cands: ranked([(c, c.clip) for c in cands])),
    ("Cộng thẳng điểm, 50/50", weighted_raw(0.5)),
    ("Chuẩn hóa 0..1 rồi cộng, 50/50", weighted_minmax(0.5)),
    ("Chuẩn hóa 0..1, DINOv2 30% / CLIP 70%", weighted_minmax(0.3)),
    ("Theo thứ hạng (RRF)", reciprocal_rank()),
]


def score(results: list[list[Hit]], queries: pd.DataFrame) -> dict[str, str]:
    top1 = [hits[0].payload for hits in results]
    rate = lambda flags: f"{sum(flags) / len(flags):.0%}"
    return {
        "Đúng sản phẩm @1": rate([p["sku"] == sku for p, sku in zip(top1, queries["sku"])]),
        f"Đúng sản phẩm @{K}": rate([sku in [h.sku for h in hits[:K]] for hits, sku in zip(results, queries["sku"])]),
        "Đúng loại @1": rate([p["loai"] == loai for p, loai in zip(top1, queries["loai"])]),
        "Đúng màu @1": rate([p["mau"] == mau for p, mau in zip(top1, queries["mau"])]),
    }


def print_mistakes(results: list[list[Hit]], queries: pd.DataFrame, limit: int = 12) -> None:
    rows = [{"Ảnh khách chụp": q.ten, "Kết quả đầu": hits[0].payload["ten"], "Điểm": round(hits[0].score, 3),
             "Hạng của sản phẩm đúng": next((i + 1 for i, h in enumerate(hits) if h.sku == q.sku), f">{K}")}
            for q, hits in zip(queries.itertuples(), results) if hits[0].sku != q.sku]
    print(pd.DataFrame(rows).head(limit).to_string(index=False) if rows else "(không có)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    queries = load_queries()
    images = [open_image(path) for path in queries["file"]]
    index = CatalogIndex()

    table, all_results = [], {}
    for name in MODELS:
        embedder = get_embedder(name)
        start = time.perf_counter()
        vectors = embedder.embed(images)
        ms = (time.perf_counter() - start) / len(images) * 1000
        all_results[name] = [index.search(name, vector, k=K) for vector in vectors]
        table.append({"Cách biến ảnh thành vector": embedder.label, **score(all_results[name], queries),
                      "ms/ảnh": f"{ms:.0f}"})

    print(f"{len(queries)} ảnh khách chụp, tìm trong danh mục {len(queries)} sản phẩm.\n")
    print("== Từng mô hình riêng ==")
    print(pd.DataFrame(table).to_string(index=False))

    searcher = ProductSearch(index)
    candidates = [searcher.candidates(image) for image in images]
    index.close()
    spread = lambda attr: np.mean([max(getattr(c, attr) for c in cs) - min(getattr(c, attr) for c in cs)
                                   for cs in candidates])
    print(f"\n== Hai bước: DINOv2 lấy 10 ứng viên, rồi chấm lại ==")
    print(f"Độ trải điểm trong 10 ứng viên (cao nhất - thấp nhất, trung bình): "
          f"DINOv2 {spread('dino'):.3f}, CLIP {spread('clip'):.3f}\n")

    as_hits = lambda scored: [Hit(c.sku, s, c.payload) for c, s in scored]
    fused_table = []
    for name, fuse in [*FUSIONS, ("→ rerank đang dùng", rerank)]:
        results = [as_hits(fuse(cands)) for cands in candidates]
        fused_table.append({"Cách chấm lại": name, **score(results, queries)})
    print(pd.DataFrame(fused_table).to_string(index=False))

    # Biểu đồ màu sai gần hết nên không in danh sách của nó.
    for name in ["dinov2", "clip"]:
        print(f"\n== {get_embedder(name).label}: các ảnh tìm sai ==")
        print_mistakes(all_results[name], queries)
    print("\n== rerank đang dùng: các ảnh vẫn tìm sai ==")
    print_mistakes(results, queries)


if __name__ == "__main__":
    main()
